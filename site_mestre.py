import streamlit as st
import google.generativeai as genai

# 1. Configuração do visual da página
st.set_page_config(page_title="Mestre Cervejeiro", page_icon="🍺")
st.title("🍺 IA Mestre Cervejeiro")
st.write("Bem-vindo à sua consultoria cervejeira online!")

# 2. Configurando a Inteligência
CHAVE_API = st.secrets["CHAVE_API"]
genai.configure(api_key=CHAVE_API)

instrucoes_mestre = """
Você é um mestre cervejeiro artesanal muito experiente e simpático. 
Seu objetivo é ajudar cervejeiros caseiros a criar receitas, entender sobre 
lúpulos, maltes, leveduras e corrigir problemas na fermentação.
Responda de forma clara e com um tom de quem adora fazer cerveja.
"""

# 3. Criando a "memória" do bot para o site não esquecer a conversa
if "chat" not in st.session_state:
    modelo = genai.GenerativeModel(
        model_name='gemini-2.5-flash', 
        system_instruction=instrucoes_mestre
    )
    # Aqui a IA inicia um chat com memória vazia
    st.session_state.chat = modelo.start_chat(history=[])

# 4. Desenhando as mensagens antigas na tela
for mensagem in st.session_state.chat.history:
    papel = "user" if mensagem.role == "user" else "assistant"
    with st.chat_message(papel):
        st.markdown(mensagem.parts[0].text)

# 5. A caixa de texto para você digitar
pergunta = st.chat_input("Qual a sua dúvida cervejeira hoje?")

if pergunta:
    # Mostra a pergunta que você digitou na tela
    with st.chat_message("user"):
        st.markdown(pergunta)
    
    # Envia para a IA e mostra a resposta com um efeitinho de carregamento
    with st.chat_message("assistant"):
        resposta = st.session_state.chat.send_message(pergunta)
        st.markdown(resposta.text)