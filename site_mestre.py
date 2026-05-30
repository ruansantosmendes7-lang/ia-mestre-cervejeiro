import streamlit as st
import google.generativeai as genai

# 1. Configuração da página e AUMENTO DAS LETRAS
st.set_page_config(page_title="Mestre Cervejeiro", page_icon="🍺")

# Esse bloco de "style" é o que deixa as letras maiores e mais fáceis de ler
st.markdown("""
<style>
    div[data-testid="stChatMessageContent"] {
        font-size: 18px !important;
    }
    div[data-testid="stChatInput"] textarea {
        font-size: 18px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🍺 IA Mestre Cervejeiro")
st.write("Bem-vindo à sua consultoria cervejeira online!")

# 2. Configurando a Chave
CHAVE_API = st.secrets["CHAVE_API"]
genai.configure(api_key=CHAVE_API)

instrucoes_mestre = """
Você é um mestre cervejeiro artesanal experiente.
Ajude a criar receitas, entender lúpulos, maltes e leveduras.
"""

# 3. A Memória da Sessão (Já está ativada!)
if "chat" not in st.session_state:
    modelo = genai.GenerativeModel(
        model_name='gemini-2.5-flash', 
        system_instruction=instrucoes_mestre
    )
    st.session_state.chat = modelo.start_chat(history=[])

for mensagem in st.session_state.chat.history:
    papel = "user" if mensagem.role == "user" else "assistant"
    with st.chat_message(papel):
        st.markdown(mensagem.parts[0].text)

# 4. A Caixa de Pergunta e o Efeito "Máquina de Escrever" (Mais rápido!)
pergunta = st.chat_input("Qual a sua dúvida cervejeira hoje?")

if pergunta:
    # Mostra a sua pergunta na tela
    with st.chat_message("user"):
        st.markdown(pergunta)
    
    with st.chat_message("assistant"):
        # Pede a resposta em modo streaming (pacotinhos)
        resposta = st.session_state.chat.send_message(pergunta, stream=True)
        
        # O SEGREDO ESTÁ AQUI: Uma função para "abrir os envelopes"
        def extrair_texto(resposta_em_pedacos):
            for pedaco in resposta_em_pedacos:
                yield pedaco.text
                
        # O Streamlit digita na tela apenas o texto limpo, com o efeito rápido!
        st.write_stream(extrair_texto(resposta))