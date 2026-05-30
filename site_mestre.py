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
# 3. FUNÇÕES DO BANCO DE DADOS SUPABASE
# =====================================================================
def salvar_no_banco(nome, pergunta, resposta):
    try:
        conn = psycopg2.connect(URL_BANCO)
        cursor = conn.cursor()
        query = "INSERT INTO historico_conversas (usuario, mensagem_usuario, resposta_ia) VALUES (%s, %s, %s);"
        cursor.execute(query, (nome, pergunta, resposta))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"⚠️ Erro ao salvar histórico no banco: {e}")

def buscar_mensagens_recentes(nome):
    try:
        conn = psycopg2.connect(URL_BANCO)
        cursor = conn.cursor()
        query = "SELECT mensagem_usuario, resposta_ia FROM historico_conversas WHERE usuario = %s ORDER BY id DESC LIMIT 10;"
        cursor.execute(query, (nome,))
        registros = cursor.fetchall()
        cursor.close()
        conn.close()
        return registros
    except Exception as e:
        return []

def salvar_sessao_banco(email, nome, foto):
    try:
        conn = psycopg2.connect(URL_BANCO)
        cursor = conn.cursor()
        query = """
            INSERT INTO sessoes_ativas (email_usuario, usuario_nome, usuario_foto, atualizado_em)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (email_usuario) 
            DO UPDATE SET usuario_nome = EXCLUDED.usuario_nome, usuario_foto = EXCLUDED.usuario_foto, atualizado_em = CURRENT_TIMESTAMP;
        """
        cursor.execute(query, (email, nome, foto))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        pass

def buscar_ultima_sessao():
    try:
        conn = psycopg2.connect(URL_BANCO)
        cursor = conn.cursor()
        query = "SELECT usuario_nome, usuario_foto FROM sessoes_ativas ORDER BY atualizado_em DESC LIMIT 1;"
        cursor.execute(query)
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        return resultado
    except Exception as e:
        return None

def limpar_todas_sessoes():
    try:
        conn = psycopg2.connect(URL_BANCO)
        cursor = conn.cursor()
        query = "DELETE FROM sessoes_ativas;"
        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        pass

# =====================================================================
# 4. BARRA LATERAL (LOGIN DO GOOGLE COM PERSISTÊNCIA)
# =====================================================================
# Tenta recuperar o último login do banco de dados caso tenha dado F5
if "user_info" not in st.session_state:
    sessao_recuperada = buscar_ultima_sessao()
    if sessao_recuperada:
        st.session_state.user_info = {
            "name": sessao_recuperada[0],
            "picture": sessao_recuperada[1]
        }

with st.sidebar:
    st.header("👤 Acesso ao Sistema")
    
    if "user_info" not in st.session_state:
        st.write("Faça login com o Google para acessar.")
        
        result = oauth2.authorize_button(
            name="Entrar com o Google",
            icon="https://www.google.com.br/favicon.ico",
            redirect_uri=REDIRECT_URI,
            scope="openid email profile",
            key="google_login_main",
            extras_params={"prompt": "select_account", "access_type": "offline"},
            use_container_width=True
        )
        
        if result and "token" in result:
            id_token = result["token"]["id_token"]
            payload = id_token.split(".")[1]
            payload += "=" * ((4 - len(payload) % 4) % 4)
            user_data = json.loads(base64.b64decode(payload).decode("utf-8"))
            
            st.session_state.user_info = user_data
            
            # Salva o login no Supabase para lembrar no F5
            salvar_sessao_banco(
                user_data.get("email", "indisponivel"), 
                user_data.get("name", "Cervejeiro"), 
                user_data.get("picture", "")
            )
            st.rerun() 
    else:
        nome_usuario = st.session_state.user_info.get("name", "Cervejeiro")
        foto_usuario = st.session_state.user_info.get("picture", "")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if foto_usuario:
                st.image(foto_usuario, width=50)
        with col2:
            st.write(f"Olá, **{nome_usuario}**!")
            
        if st.button("Sair da Conta"):
            limpar_todas_sessoes()
            del st.session_state.user_info
            if "chat" in st.session_state:
                del st.session_state.chat
            st.rerun()
            
        st.write("---")
        st.header("⚙️ Painel do Mestre")
        if st.button("🗑️ Limpar Tela do Chat"):
            if "chat" in st.session_state:
                del st.session_state.chat
            st.rerun()
            
        st.write("---")
        st.header("📜 Mensagens Recentes")
        historico_banco = buscar_mensagens_recentes(nome_usuario)
        if historico_banco:
            for i, (pergunta_antiga, resposta_antiga) in enumerate(historico_banco):
                titulo_aba = f"💬 {pergunta_antiga[:25]}..." if len(pergunta_antiga) > 25 else f"💬 {pergunta_antiga}"
                with st.expander(titulo_aba):
                    st.markdown(f"**Você:** {pergunta_antiga}")
                    st.markdown(f"**Mia:** {resposta_antiga}")
        else:
            st.caption("Nenhuma conversa antiga encontrada.")

# =====================================================================
# 5. LÓGICA DO CHAT (SÓ EXECUTA LOGADO)
# =====================================================================
if "user_info" in st.session_state:
    nome_usuario = st.session_state.user_info.get("name", "Cervejeiro")
    
    instrucoes_mestre = f"Você é uma especialista em produção de bebidas chamada Mia. Ajude de forma clara. O nome do usuário é {nome_usuario}."

    if "chat" not in st.session_state:
        modelo = genai.GenerativeModel(model_name='gemini-2.5-flash', system_instruction=instrucoes_mestre)
        st.session_state.chat = modelo.start_chat(history=[])

    for message in st.session_state.chat.history:
        papel = "user" if message.role == "user" else "assistant"
        with st.chat_message(papel):
            st.markdown(message.parts[0].text)

    pergunta_final = None

    st.write("---")
    audio_gravado = st.audio_input("🎙️ Clique para falar e aguarde o envio automático")

    st.write("👉 Ideias prontas para testar o robô:")
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        if st.button("🌾 O que é Dry Hopping?"): pergunta_final = "O que é Dry Hopping e para que serve?"
    with col_b2:
        if st.button("🌡️ Guia de Fermentação"): pergunta_final = "Me dê dicas rápidas sobre controle de temperatura na fermentação."
    with col_b3:
        if st.button("💧 Água para Brassagem"): pergunta_final = "Qual a importância do controle do PH da água?"

    texto_digitado = st.chat_input("Ou digite sua dúvida aqui...")
    if texto_digitado:
        pergunta_final = texto_digitado
    elif audio_gravado and not pergunta_final:
        with st.spinner("Entendendo o áudio..."):
            dados_audio = {"mime_type": "audio/wav", "data": audio_gravado.getvalue()}
            modelo_tradutor = genai.GenerativeModel(model_name='gemini-2.5-flash', system_instruction="Transcreva o áudio.")
            resposta_traducao = modelo_tradutor.generate_content(["Transcreva exatamente:", dados_audio])
            pergunta_final = resposta_traducao.text

    if pergunta_final:
        with st.chat_message("user"):
            st.markdown(pergunta_final)
        with st.chat_message("assistant"):
            try:
                resposta_streaming = st.session_state.chat.send_message(pergunta_final, stream=True)
                def extrair_texto(resposta_em_pedacos):
                    for pedaco in resposta_em_pedacos: yield pedaco.text
                texto_completo_resposta = st.write_stream(extrair_texto(resposta_streaming))
                
                # Salva a mensagem no Supabase
                salvar_no_banco(nome_usuario, pergunta_final, texto_completo_resposta)
                st.rerun()
            except Exception as e:
                st.error("O limite gratuito de perguntas por minuto do Google Gemini foi atingido. Por favor, aguarde de 1 a 2 minutos e envie sua mensagem novamente!")

else:
    st.info("👈 Faça login com o Google na barra lateral para começar a conversar com a Mia!")
