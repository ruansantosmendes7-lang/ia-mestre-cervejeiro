import streamlit as st
import google.generativeai as genai

# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E DESIGN (LETRAS MAIORES)
# =====================================================================
st.set_page_config(page_title="Mestre Cervejeiro", page_icon="🍺")

# Injeção de CSS para aumentar o tamanho da fonte das mensagens e da caixa de entrada
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
st.write("Fale no microfone ou digite sua dúvida sobre processos, insumos e técnicas!")

# =====================================================================
# 2. CONFIGURAÇÃO DA CHAVE DE API E PERSONALIDADE
# =====================================================================
# Puxa a chave de forma segura do cofre (Secrets) do Streamlit
CHAVE_API = st.secrets["CHAVE_API"]
genai.configure(api_key=CHAVE_API)

# Prompt do sistema que define como o assistente deve se comportar
instrucoes_mestre = """
Você é um especialista em processos de produção de bebidas, focado em ajudar com dúvidas sobre insumos, tempos e boas práticas de fabricação de forma clara e técnica.
"""

# =====================================================================
# 3. GERENCIAMENTO DA MEMÓRIA DA CONVERSA
# =====================================================================
# Inicializa o chat histórico na sessão se ele ainda não existir
if "chat" not in st.session_state:
    modelo = genai.GenerativeModel(
        model_name='gemini-2.5-flash', 
        system_instruction=instrucoes_mestre
    )
    st.session_state.chat = modelo.start_chat(history=[])

# Exibe na tela todas as mensagens trocadas anteriormente nesta sessão
for mensagem in st.session_state.chat.history:
    papel = "user"