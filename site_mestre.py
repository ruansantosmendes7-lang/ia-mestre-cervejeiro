import streamlit as st
import google.generativeai as genai
import psycopg2  # Biblioteca para conectar ao banco de dados Supabase

# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E DESIGN (LETRAS MAIORES)
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

# =====================================================================
# 2. CONFIGURAÇÃO DAS CHAVES (API E BANCO DE DADOS)
# =====================================================================
CHAVE_API = st.secrets["CHAVE_API"]
URL_BANCO = st.secrets["URL_BANCO"]

genai.configure(api_key=CHAVE_API)

# =====================================================================
# 3. IDENTIFICAÇÃO DO USUÁRIO NA BARRA LATERAL
# =====================================================================
with st.sidebar:
    st.header("👤 Quem está aí?")
    
    # Caixa para o usuário digitar o nome (padrão é "Visitante")
    nome_usuario = st.text_input("Digite seu nome para a IA te reconhecer:", value="Visitante")
    
    st.write(f"Olá, **{nome_usuario}**! Seja bem-vindo.")
    st.write("---")
    
    st.header("⚙️ Painel do Mestre")
    st.write("Use o botão abaixo para reiniciar o chat do zero se a conversa ficar muito longa.")
    if st.button("🗑️ Limpar Histórico"):
        # Se limpar o histórico, força a reinicialização do chat
        if "chat" in st.session_state:
            del st.session_state.chat
        st.rerun()

# Criamos a instrução personalizada incluindo o nome da pessoa que está usando o site
instrucoes_mestre = f"""
Você é um especialista em processos de produção de bebidas, focado em ajudar com dúvidas sobre insumos, tempos e boas práticas de fabricação de forma clara e técnica.
O nome da pessoa com quem você está conversando é {nome_usuario}. Sempre que puder ou for natural, chame-a por esse nome ({nome_usuario}) para manter um atendimento personalizado e amigável.
"""

# =====================================================================
# 4. GERENCIAMENTO DA MEMÓRIA DO CHAT
# =====================================================================
# Inicializa ou reinicializa o chat se o modelo não existir ou se o nome mudar
if "chat" not in st.session_state or st.session_state.get("nome_atual") != nome_usuario:
    modelo = genai.GenerativeModel(
        model_name='gemini-2.5-flash', 
        system_instruction=instrucoes_mestre
    )
    st.session_state.chat = modelo.start_chat(history=[])
    st.session_state.nome_atual = nome_usuario # Guarda o nome atual para checar depois

# Função para salvar a conversa no Supabase carregando o nome correto
def salvar_no_banco(nome, pergunta, resposta):
    try:
        conn = psycopg2.connect(URL_BANCO)
        cursor = conn.cursor()
        query = """
            INSERT INTO historico_conversas (usuario, mensagem_usuario, resposta_ia)
            VALUES (%s, %s, %s);
        """
        cursor.execute(query, (nome, pergunta, response_text))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar no banco de dados: {e}")

st.write(f"Fale no microfone, use os botões rápidos ou digite sua dúvida, **{nome_usuario}**!")

# Exibe o histórico de mensagens na tela
for mensagem in st.session_state.chat.history:
    papel = "user" if mensagem.role == "user" else "assistant"
    with st.chat_message(papel):
        st.markdown(mensagem.parts[0].text)

# =====================================================================
# 5. CONTROLES DE ENTRADA E BOTÕES RÁPIDOS
# =====================================================================
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
        pergunta_final = "Me dê dicas rápidos sobre controle de temperatura na fermentação."
with col_b3:
    if st.button("💧 Água para Brassagem"):
        pergunta_final = "Qual a importância do controle do PH da água?"

texto_digitado = st.chat_input("Ou digite sua dúvida aqui...")

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
# 6. PROCESSAMENTO, EXIBIÇÃO E SALVAMENTO NO BANCO
# =====================================================================
if pergunta_final:
    with st.chat_message("user"):
        st.markdown(pergunta_final)
    
    with st.chat_message("assistant"):
        resposta_streaming = st.session_state.chat.send_message(pergunta_final, stream=True)
        
        def extrair_texto(resposta_em_pedacos):
            for pedaco in resposta_em_pedacos:
                yield pedaco.text
                
        texto_completo_resposta = st.write_stream(extrair_texto(resposta_streaming))
    
    # SALVA NO BANCO DE DADOS PASSANDO O NOME DIGITADO
    salvar_no_banco(nome_usuario, pergunta_final, texto_completo_resposta)
