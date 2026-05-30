import streamlit as st
import google.generativeai as genai
import psycopg2

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

genai.configure(api_key=CHAVE_API)

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
        st.error(f"⚠️ Erro ao salvar no banco de dados: {e}")

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

# =====================================================================
# 4. PAINEL DE ACESSO (BARRA LATERAL ESTÁVEL)
# =====================================================================
with st.sidebar:
    st.header("👤 Identificação")
    
    # Lista de usuários autorizados (adicione os nomes dos seus amigos aqui)
    usuarios_permitidos = ["Selecione...", "Juan", "Visitante"]
    
    # O Streamlit guarda a seleção do combo mesmo com atualizações leves
    nome_usuario = st.selectbox(
        "Quem está acessando o sistema?",
        options=usuarios_permitidos,
        key="usuario_ativo"
    )
    
    if nome_usuario != "Selecione...":
        st.success(f"Conectado como: **{nome_usuario}**")
        
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
            st.caption("Nenhuma conversa antiga encontrada para este usuário.")

# =====================================================================
# 5. LÓGICA DO CHAT (SÓ EXECUTA APÓS SELECIONAR UM USUÁRIO)
# =====================================================================
if nome_usuario != "Selecione...":
    
    instrucoes_mestre = f"Você é uma especialista em produção de bebidas chamada Mia. Ajude de forma clara e amigável. O nome do usuário conectado é {nome_usuario}."

    if "chat" not in st.session_state:
        modelo = genai.GenerativeModel(model_name='gemini-2.5-flash', system_instruction=instrucoes_mestre)
        st.session_state.chat = modelo.start_chat(history=[])

    # Renderiza o histórico da sessão atual
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
            modelo_tradutor = genai.GenerativeModel(model_name='gemini-2.5-flash', system_instruction="Transcreva o áudio de forma limpa.")
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
                
                # Salva no banco de dados vinculando ao nome selecionado
                salvar_no_banco(nome_usuario, pergunta_final, texto_completo_resposta)
                st.rerun()
            except Exception as e:
                st.error("O limite gratuito de perguntas por minuto do Google Gemini foi atingido. Por favor, aguarde de 1 a 2 minutos e envie sua mensagem novamente!")

else:
    st.info("👈 Por favor, selecione quem está acessando na barra lateral para liberar o chat com a Mia!")
