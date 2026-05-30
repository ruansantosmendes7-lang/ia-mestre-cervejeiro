import streamlit as st
import google.generativeai as genai

# 1. Configuração da página e Letras Maiores
st.set_page_config(page_title="Mestre Cervejeiro", page_icon="🍺")
st.markdown("""
<style>
    div[data-testid="stChatMessageContent"] { font-size: 18px !important; }
    div[data-testid="stChatInput"] textarea { font-size: 18px !important; }
</style>
""", unsafe_allow_html=True)

st.title("🍺 IA Mestre Cervejeiro")
st.write("Fale no microfone ou digite sua dúvida cervejeira!")

# 2. Configurando a Chave
CHAVE_API = st.secrets["CHAVE_API"]
genai.configure(api_key=CHAVE_API)

instrucoes_mestre = """
Você é um mestre cervejeiro artesanal muito experiente.
Ajude a criar receitas, entender lúpulos, maltes e leveduras.
"""

# 3. Iniciando a Memória e a Inteligência
if "chat" not in st.session_state:
    modelo = genai.GenerativeModel(
        model_name='gemini-2.5-flash', 
        system_instruction=instrucoes_mestre
    )
    st.session_state.chat = modelo.start_chat(history=[])

# 4. Desenhando as mensagens antigas na tela
for mensagem in st.session_state.chat.history:
    papel = "user" if mensagem.role == "user" else "assistant"
    with st.chat_message(papel):
        st.markdown(mensagem.parts[0].text)

# 5. OS CONTROLES (Áudio ou Texto)
pergunta_final = None

# Cria duas colunas para organizar: uma para o microfone, outra para o chat normal
col1, col2 = st.columns([1, 4])
with col1:
    audio_gravado = st.audio_input("🎙️ Falar")
with col2:
    texto_digitado = st.chat_input("Ou digite aqui...")

# Lógica: Se você digitou algo, ele usa o texto. 
if texto_digitado:
    pergunta_final = texto_digitado

# Se você gravou áudio, ele pede pro Gemini transcrever primeiro!
elif audio_gravado:
    with st.spinner("Traduzindo sua voz para o Mestre..."):
        # Transforma o áudio em um formato que o Gemini entende
        dados_audio = {
            "mime_type": "audio/wav",
            "data": audio_gravado.getvalue()
        }
        # Pede para a IA apenas transcrever
        modelo_tradutor = genai.GenerativeModel('gemini-2.5-flash')
        resposta_traducao = modelo_tradutor.generate_content([
            "Transcreva exatamente o que foi dito neste áudio, sem adicionar mais nada.", 
            dados_audio
        ])
        pergunta_final = resposta_traducao.text

# 6. ENVIANDO PARA O MESTRE (Seja por voz ou texto)
if pergunta_final:
    # Mostra o que você falou/digitou na tela
    with st.chat_message("user"):
        st.markdown(pergunta_final)
    
    # Mestre Cervejeiro responde rápido (efeito máquina de escrever consertado!)
    with st.chat_message("assistant"):
        resposta = st.session_state.chat.send_message(pergunta_final, stream=True)
        
        def extrair_texto(resposta_em_pedacos):
            for pedaco in resposta_em_pedacos:
                yield pedaco.text
                
        st.write_stream(extrair_texto(resposta))