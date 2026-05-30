import streamlit as st
import google.generativeai as genai

# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA AND DESIGN (LETRAS MAIORES)
# =====================================================================
st.set_page_config(page_title="Mestre Cervejeiro", page_icon="🍺")

# Injeção de CSS para manter as letras grandes e fáceis de ler
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
st.write("Fale no microfone, use os botões rápidos ou digite sua dúvida!")

# =====================================================================
# 2. CONFIGURAÇÃO DA CHAVE DE API E PERSONALIDADE
# =====================================================================
CHAVE_API = st.secrets["CHAVE_API"]
genai.configure(api_key=CHAVE_API)

instrucoes_mestre = """
Você é um especialista em processos de produção de bebidas, focado em ajudar com dúvidas sobre insumos, tempos e boas práticas de fabricação de forma clara e técnica.
"""

# =====================================================================
# 3. GERENCIAMENTO DA MEMÓRIA E NOVA BARRA LATERAL
# =====================================================================
# Inicializa o modelo e o chat se não existirem
if "chat" not in st.session_state:
    modelo = genai.GenerativeModel(
        model_name='gemini-2.5-flash', 
        system_instruction=instrucoes_mestre
    )
    st.session_state.chat = modelo.start_chat(history=[])

# MELHORIA 2: Barra lateral profissional com botão de Reset
with st.sidebar:
    st.header("⚙️ Painel do Mestre")
    st.write("Use o botão abaixo para reiniciar o chat do zero se a conversa ficar muito longa.")
    if st.button("🗑️ Limpar Histórico"):
        modelo = genai.GenerativeModel(
            model_name='gemini-2.5-flash', 
            system_instruction=instrucoes_mestre
        )
        st.session_state.chat = modelo.start_chat(history=[])
        st.rerun() # Recarrega a página com o chat limpo

# Exibe o histórico de mensagens na tela
for mensagem in st.session_state.chat.history:
    papel = "user" if mensagem.role == "user" else "assistant"
    with st.chat_message(papel):
        st.markdown(mensagem.parts[0].text)

# =====================================================================
# 4. CONTROLES DE ENTRADA E BOTÕES RÁPIDOS
# =====================================================================
pergunta_final = None

# Componente de Áudio Fixo
st.write("---")
audio_gravado = st.audio_input("🎙️ Clique para falar e aguarde o envio automático")

# MELHORIA 1: Botões de sugestão para cliques rápidos
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

# Caixa de texto padrão no rodapé
texto_digitado = st.chat_input("Ou digite sua dúvida aqui...")

# Definição de qual entrada foi acionada
if texto_digitado:
    pergunta_final = texto_digitado

elif audio_gravado and not pergunta_final:
    with st.spinner("Entendendo o áudio..."):
        dados_audio = {
            "mime_type": "audio/wav",
            "data": audio_gravado.getvalue()
        }
        
        instruco_tradutor = """
        Você é um especialista em transcrição de áudio focado em terminologias técnicas de processos de fabricação e insumos.
        Sua única tarefa é ouvir o áudio e escrever exatamente o que a pessoa disse, corrigindo a grafia de termos técnicos comuns caso o áudio esteja abafado.
        Não adicione comentários, não responda à pergunta, apenas transcreva o texto limpo de forma exata.
        """
        
        modelo_tradutor = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=instruco_tradutor
        )
        
        resposta_traducao = modelo_tradutor.generate_content([
            "Escute o áudio e faça a transcrição exata aplicando as corrections de termos técnicos necessárias.", 
            dados_audio
        ])
        pergunta_final = resposta_traducao.text

# =====================================================================
# 5. PROCESSAMENTO E EXIBIÇÃO DA RESPOSTA (STREAMING)
# =====================================================================
if pergunta_final:
    with st.chat_message("user"):
        st.markdown(pergunta_final)
    
    with st.chat_message("assistant"):
        resposta_streaming = st.session_state.chat.send_message(pergunta_final, stream=True)
        
        def extrair_texto(resposta_em_pedacos):
            for pedaco in resposta_em_pedacos:
                yield pedaco.text
                
        st.write_stream(extrair_texto(resposta_streaming))