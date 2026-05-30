import streamlit as st
import google.generativeai as genai
import psycopg2
import base64
import json
from streamlit_oauth import OAuth2Component

# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E DESIGN
# =====================================================================
st.set_page_config(page_title="Mestre Cervejeiro", page_icon="🍺")

st.markdown("""
<style>
    div[data-testid="stChatMessageContent"] { font-size: 18px !important; }
    div[data-testid="stChatInput"] textarea { font-size: 18px !important; }
</style>
""", unsafe_allow_html=True)

st.title("🍺 IA Mestre Cervejeiro")

# =====================================================================
# 2. CHAVES E CONFIGURAÇÕES
# =====================================================================
CHAVE_API = st.secrets["CHAVE_API"]
URL_BANCO = st.secrets["URL_BANCO"]
CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]

genai.configure(api_key=CHAVE_API)

# Configuração do componente de Login do Google
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

# =====================================================================
# 3. BARRA LATERAL (LOGIN DO GOOGLE E CONTROLES)
# =====================================================================
with st.sidebar:
    st.header("👤 Acesso ao Sistema")
    
    # Verifica se o usuário JÁ está logado
    if "user_info" not in st.session_state:
        st.write("Faça login com o Google para conversar com o Mestre Cervejeiro.")
        
        # Botão de Login
        result = oauth2.authorize_button(
            name="Entrar com o Google",
            icon="https://www.google.com.br/favicon.ico",
            redirect_uri=REDIRECT_URI,
            scope="openid email profile",
            key="google_login",
            extras_params={"prompt": "consent", "access_type": "offline"},
            use_container_width=True
        )
        
        # Se o login der certo, extrai os dados do Google
        if result and "token" in result:
            id_token = result["token"]["id_token"]
            payload = id_token.split(".")[1]
            payload += "=" * ((4 - len(payload) % 4) % 4)
            user_data = json.loads(base64.b64decode(payload).decode("utf-8"))
            
            st.session_state.user_info = user_data
            st.rerun() 
    else:
        # Se já estiver logado, mostra a foto e o nome
        nome_usuario = st.session_state.user_info.get("name", "Cervejeiro")
        foto_usuario = st.session_state.user_info.get("picture", "")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if foto_usuario:
                st.image(foto_usuario, width=50)
        with col2:
            st.write(f"Olá, **{nome_usuario}**!")
            
        if st.button("Sair da Conta"):
            del st.session_state.user_info
            if "chat" in st.session_state:
                del st.session_state.chat
            st.rerun()
            
        st.write("---")
        st.header("⚙️ Painel do Mestre")
        if st.button("🗑️ Limpar Histórico do Chat"):
            if "chat" in st.session_state:
                del st.session_state.chat
            st.rerun()

# =====================================================================
# 4. LÓGICA PRINCIPAL (SÓ APARECE SE ESTIVER LOGADO)
# =====================================================================
if "user_info" in st.session_state:
    nome_usuario = st.session_state.user_info.get("name", "Cervejeiro")
    
    instrucoes_mestre = f"""
    Você é um especialista em processos de produção de bebidas, focado em ajudar com dúvidas sobre insumos, tempos e boas práticas de fabricação.
    O nome do usuário conectado é {nome_usuario}. Chame-o pelo nome ({nome_usuario}) para manter a conversa amigável.
    """

    if "chat" not in st.session_state:
        modelo = genai.GenerativeModel(
            model_name='gemini-2.5-flash', 
            system_instruction=instrucoes_mestre
        )
        st.session_state.chat = modelo.start_chat(history=[])

    def salvar_no_banco(nome, pergunta, resposta):
        try:
            conn = psycopg2.connect(URL_BANCO)
            cursor = conn.cursor()
            query = """
                INSERT INTO historico_conversas (usuario, mensagem_usuario, resposta_ia)
                VALUES (%s, %s, %s);
            """
            cursor.execute(query, (nome, pergunta, resposta))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Erro ao salvar no banco de dados: {e}")

    for mensagem in st.session_state.chat.history:
        papel = "user" if mensagem.role == "user" else "assistant"
        with st.chat_message(papel):
            st.markdown(mensagem.parts[0].text)

    pergunta_final = None

    st.write("---")
    audio_gravado = st.audio_input("🎙️ Clique para falar e aguarde o envio automático")

    st.write("👉 Ideias prontas para testar o robô:")
    col_b1, col_b2, col_b3 = st.columns(3)

    with col_b1:
        if st.button("🌾 O que é Dry Hopping?"):
            pergunta_final = "O que é Dry Hopping e para que serve?"
    with col_b2:
        if st.button("🌡️ Guia de Fermentação"):
            pergunta_final = "Me dê dicas rápidas sobre controle de temperatura na fermentação."
    with col_b3:
        if st.button("💧 Água para Brassagem"):
            pergunta_final = "Qual a importância do controle do PH da água?"

    texto_digitado = st.chat_input("Ou digite sua dúvida aqui...")

    if texto_digitado:
        pergunta_final = texto_digitado
    elif audio_gravado and not pergunta_final:
        with st.spinner("Entendendo o áudio..."):
            dados_audio = {"mime_type": "audio/wav", "data": audio_gravado.getvalue()}
            instruco_tradutor = """Sua tarefa é ouvir o áudio e transcrever o que a pessoa disse, corrigindo jargões cervejeiros."""
            modelo_tradutor = genai.GenerativeModel(model_name='gemini-2.5-flash', system_instruction=instruco_tradutor)
            resposta_traducao = modelo_tradutor.generate_content(["Transcreva exatamente:", dados_audio])
            pergunta_final = resposta_traducao.text

    if pergunta_final:
        with st.chat_message("user"):
            st.markdown(pergunta_final)
        
        with st.chat_message("assistant"):
            resposta_streaming = st.session_state.chat.send_message(pergunta_final, stream=True)
            
            def extrair_texto(resposta_em_pedacos):
                for pedaco in resposta_em_pedacos:
                    yield pedaco.text
                    
            texto_completo_resposta = st.write_stream(extrair_texto(resposta_streaming))
        
        salvar_no_banco(nome_usuario, pergunta_final, texto_completo_resposta)

else:
    st.info("👈 Faça login na barra lateral para começar a conversar com o Mestre Cervejeiro e liberar as funcionalidades!")
