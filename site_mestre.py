import streamlit as st
import google.generativeai as genai

# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E DESIGN (LETRAS MAIORES)
# =====================================================================
st.set_page_config(page_title="Mestre Cervejeiro", page_icon="🍺")

# CSS para garantir que tudo fique grande e visível
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
CHAVE_API = st.secrets["CHAVE_API"]
genai.configure(api_key=CHAVE_API)

instrucoes_mestre = """
Você é um especialista em processos de produção de bebidas, focado em ajudar com dúvidas sobre insumos, tempos e boas práticas de fabricação de forma clara e técnica.
"""

# =====================================================================
# 3. GERENCIAMENTO DA MEMÓRIA DA CONVERSA
# =====================================================================
if "chat" not in st.session_state:
    modelo = genai.GenerativeModel(
        model_name='gemini-2.5-flash', 
        system_instruction=instrucoes_mestre
    )
    st.session_state.chat = modelo.start_chat(history=[])

# Exibe o histórico de mensagens na tela
for mensagem in st.session_state.chat.history:
    papel = "user" if mensagem.role == "user" else "assistant"
    with st.chat_message(papel):
        st.markdown(mensagem.parts[0].text)

# =====================================================================
# 4. CONTROLES DE ENTRADA (SEM COLUNAS - UM EMBAIXO DO OUTRO)
# =====================================================================
pergunta_final = None

# Removido as colunas. Agora o gravador fica fixo e visível no corpo do site
st.write("---")
audio_gravado = st.audio_input("🎙️ Clique para falar e aguarde o envio automático")

# A caixa de texto padrão do Streamlit (fica fixa no rodapé da página)
texto_digitado = st.chat_input("Ou digite sua dúvida aqui...")

# Verificação das entradas do usuário
if texto_digitado:
    pergunta_final = texto_digitado

elif audio_gravado:
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
            "Escute o áudio e faça a transcrição exata aplicando as correções de termos técnicos necessárias.", 
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