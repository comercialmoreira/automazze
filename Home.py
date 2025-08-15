import tempfile
import streamlit as st
from langchain.memory import ConversationBufferMemory
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from loaders import carrega_site, carrega_youtube, carrega_pdf, carrega_docx, carrega_txt, carrega_csv, carrega_imagem

import os
import re




st.set_page_config(
    layout="wide",
    page_title="autoMazze Assistant",
    page_icon="🤖"
)

openai = st.secrets["OPENAI_API_KEY"]
groq = st.secrets["GROQ_API_KEY"]

CONFIG_MODELOS = {
    'OpenAI': {
        'modelos': [
            'gpt-4o-mini',  
            'gpt-4.1-mini',
            'gpt-4.1-nano',
            'gpt-o4-mini-high',
            'gpt-4o',
            'gpt-4.1',
            'gpt-4.5',
        ],
        'chat': ChatOpenAI,
        'api_key': openai
    },
    'Groq': {
        'modelos': [
            'deepseek-r1-distill-llama-70b',
            'llama-3.3-70b-versatile',  
            'qwen-qwq-32b'
        ],
        'chat': ChatGroq,
        'api_key': groq
    }
}

MEMORIA = ConversationBufferMemory()

def identificar_tipo_entrada(input_usuario, arquivo):
    """Identifica o tipo de documento e extrai URLs da mensagem."""
    # Padrão para identificar URLs
    url_pattern = r'(https?://[^\s]+)'
    url_match = None
    if input_usuario:
        url_match = re.search(url_pattern, input_usuario)

    if arquivo:
        # Detectar tipo com base na extensão do arquivo
        extensao = os.path.splitext(arquivo.name)[1].lower()
        if extensao == '.pdf':
            return 'Analisador de Pdf', arquivo, input_usuario
        elif extensao == '.docx':
            return 'Analisador de DOCX', arquivo, input_usuario
        elif extensao == '.csv':
            return 'Analisador de CSV', arquivo, input_usuario
        elif extensao == '.txt':
            return 'Analisador de Texto', arquivo, input_usuario
        elif extensao in ['.png', '.jpg', '.jpeg']:
            return 'Analisador de Imagem', arquivo, input_usuario
        else:
            st.error(f"Tipo de arquivo não suportado: {extensao}")
            return None, None, None
    elif url_match:
        # Extrair a URL da mensagem
        url = url_match.group(0)
        # Determinar se é YouTube ou site
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'Analisador de Youtube', url, input_usuario
        else:
            return 'Analisador de Site', url, input_usuario
    elif input_usuario:
        return 'Chat', None, input_usuario
    return None, None, None

def carrega_arquivos(tipo_arquivo, arquivo):
    if tipo_arquivo == 'Chat':
        return "Modo Chat ativado. Nenhum documento carregado."
    if tipo_arquivo == 'Analisador de Site':
        return carrega_site(arquivo)
    if tipo_arquivo == 'Analisador de Youtube':
        return carrega_youtube(arquivo)
    if tipo_arquivo == 'Analisador de Pdf':
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp:
            temp.write(arquivo.read())
            nome_temp = temp.name
        return carrega_pdf(nome_temp)
    if tipo_arquivo == 'Analisador de DOCX':
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp:
            temp.write(arquivo.read())
            nome_temp = temp.name
        return carrega_docx(nome_temp)
    if tipo_arquivo == 'Analisador de CSV':
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp:
            temp.write(arquivo.read())
            nome_temp = temp.name
        return carrega_csv(nome_temp)
    if tipo_arquivo == 'Analisador de Texto':
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp:
            temp.write(arquivo.read())
            nome_temp = temp.name
        return carrega_txt(nome_temp)
    if tipo_arquivo == 'Analisador de Imagem':
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(arquivo.read())
            nome_temp = temp.name
        return carrega_imagem(nome_temp)

def carrega_modelo(provedor, modelo, api_key):
    try:
        # System prompt inicial sem tipo_arquivo
        system_message = f'''# Instruções para o autoMazze Assistant

## IDENTIDADE E PROPÓSITO
Você é o autoMazze, um assistente de IA avançado e extremamente inteligente projetado para análise profunda de documentos e conteúdo.
Você foi programado para ser preciso, detalhista e fornecer insights valiosos sobre o conteúdo analisado.

## REGRAS DE COMPORTAMENTO

### Processamento e Análise
1. **Priorize informações relevantes** do documento fornecido
2. **Identifique padrões e conexões** entre diferentes partes do documento
3. **Extraia insights principais** que talvez não estejam explícitos
4. **Interprete dados complexos** de forma acessível e compreensível
5. **Forneça contexto adicional** quando necessário para melhorar a compreensão

### Quando Responder
1. **Seja detalhado** nas respostas, não apenas superficial
2. **Estruture informações** de maneira lógica e facilmente compreensível
3. **Adapte o nível de complexidade** de acordo com o contexto da pergunta
4. **Quando apropriado, sugira ações** baseadas nos insights do documento
5. **Corrija equívocos** respeitosamente quando o usuário interpretar incorretamente o conteúdo

### Formato e Estilo de Respostas
1. Use **negrito** para destacar conceitos-chave importantes
2. Utilize *itálico* para enfatizar pontos secundários relevantes
3. Aplique `código` para elementos técnicos específicos quando necessário
4. Organize informações em **seções hierárquicas** com cabeçalhos (##, ###)
5. Use listas numeradas para processos sequenciais e marcadores para itens não ordenados
6. Inclua emojis 🔍 estrategicamente para melhorar a legibilidade (com moderação)
7. Crie tabelas quando houver dados comparativos ou estruturados
8. Para códigos ou conteúdo técnico, utilize blocos de código com a sintaxe apropriada

## CAPACIDADES ESPECIAIS

### Análise de Dados
- Identifique tendências, padrões e anomalias em dados numéricos
- Reconheça correlações entre diferentes conjuntos de dados
- Ofereça visualizações descritivas de dados complexos

### Análise de Texto
- Identifique temas centrais e subtemas
- Reconheça tom, sentimento e intenção do autor
- Detecte contradições ou inconsistências no texto
- Resuma conteúdo extenso mantendo os pontos-chave

### Resolução de Problemas
- Defina claramente o problema apresentado
- Explore múltiplas abordagens para solução
- Avalie prós e contras de cada abordagem
- Recomende a solução mais adequada com justificativa

## ORIENTAÇÕES FINAIS
- Substitua qualquer "$" por "S" nas suas respostas
- Se o documento contiver apenas "Just a moment..." ou mensagens de erro similares, informe o usuário para tentar novamente
- Sempre que possível, apresente uma conclusão sintetizando os principais pontos abordados
- Quando não tiver informação suficiente, seja transparente e solicite esclarecimentos

Agora, responda às perguntas do usuário com inteligência, profundidade e clareza excepcional.
'''

        print(system_message)

        template = ChatPromptTemplate.from_messages([
            ('system', system_message),
            ('placeholder', '{chat_history}'),
            ('user', '{input}')
        ])
        
        if provedor == 'OpenAI':
            chat = CONFIG_MODELOS[provedor]['chat'](
                model=modelo, 
                api_key=api_key,
                temperature=1
            )
        else:
            chat = CONFIG_MODELOS[provedor]['chat'](
                model=modelo, 
                api_key=api_key
            )
            
        chain = template | chat
        st.session_state['chain'] = chain
        st.session_state['modelo_carregado'] = True
        st.success(f"{modelo} carregado")

    except Exception as e:
        st.error(f"Erro ao carregar o modelo: {str(e)}")

def pagina_chat():
    col1, col2, col3 = st.columns([5, 1, 5])
    
    # Initialize the session state for file if it doesn't exist
    if 'uploaded_file' not in st.session_state:
        st.session_state['uploaded_file'] = None

        
    with col3:
        # Store the file in session state instead of a local variable
        uploaded_file = st.file_uploader("Envie um arquivo (PDF, CSV, TXT, Imagem, DOCX)", 
                                         type=['pdf', 'csv', 'txt', 'png', 'jpg', 'jpeg', 'docx'], 
                                         key="chat_file_uploader")
        
        # Update session state when a new file is uploaded
        if uploaded_file is not None:
            st.session_state['uploaded_file'] = uploaded_file
    
    with col1:
        
        st.image("./assets/image/autoMazze.png", width=400)
    if 'modelo_carregado' not in st.session_state or not st.session_state['modelo_carregado']:
        st.info('👈 Por favor, selecione um provedor e modelo na barra lateral para começar.')
        st.stop()
    
    st.divider()
    chain = st.session_state.get('chain')
    if chain is None:
        st.info('👈 Por favor, selecione um provedor e modelo na barra lateral para começar.')
        st.stop()

    memoria = st.session_state.get('memoria', MEMORIA)
    for mensagem in memoria.buffer_as_messages:
        chat = st.chat_message(mensagem.type)
        chat.markdown(mensagem.content)

    # Get user input
    input_usuario = st.chat_input('Fale com o autoMazze assistant ou envie um arquivo/URL...')

    # Only process when there's user input
    if input_usuario:
        # Get the file from session state
        arquivo = st.session_state['uploaded_file']
        
        # Identificar o tipo de entrada e extrair o prompt
        tipo_arquivo, entrada, prompt = identificar_tipo_entrada(input_usuario, arquivo)

        if tipo_arquivo is None:
            st.stop()

        # Exibir a mensagem do usuário no chat
        chat = st.chat_message('human')
        chat.markdown(input_usuario)
        if arquivo:
            chat.markdown(f"Utilizando arquivo: **{arquivo.name}**")

        with st.spinner('autoMazze está processando...'):
            # Carregar o documento com base no tipo identificado
            documento = carrega_arquivos(tipo_arquivo, entrada) if tipo_arquivo != 'Chat' else ""

            # Atualizar o system prompt com o tipo de documento e conteúdo
            system_message = f'''# Instruções para o autoMazze Assistant

## IDENTIDADE E PROPÓSITO
Você é o autoMazze, um assistente de IA avançado e extremamente inteligente projetado para análise profunda de documentos e conteúdo.
Você foi programado para ser preciso, detalhista e fornecer insights valiosos sobre o conteúdo analisado.

## FONTE DE DADOS ATUAL
Você está analisando um documento do tipo: **{tipo_arquivo}**

O conteúdo do documento é:

{documento}

## REGRAS DE COMPORTAMENTO

### Processamento e Análise
1. **Priorize informações relevantes** do documento fornecido
2. **Identifique padrões e conexões** entre diferentes partes do documento
3. **Extraia insights principais** que talvez não estejam explícitos
4. **Interprete dados complexos** de forma acessível e compreensível
5. **Forneça contexto adicional** quando necessário para melhorar a compreensão
6. **Se o tipo do documento foi exatamente = Analisador de Imagem, então você estará analisando uma imagem.

### Quando Responder
1. **Seja detalhado** nas respostas, não apenas superficial
2. **Estruture informações** de maneira lógica e facilmente compreensível
3. **Adapte o nível de complexidade** de acordo com o contexto da pergunta
4. **Quando apropriado, sugira ações** baseadas nos insights do documento
5. **Corrija equívocos** respeitosamente quando o usuário interpretar incorretamente o conteúdo

### Formato e Estilo de Respostas
1. Use **negrito** para destacar conceitos-chave importantes
2. Utilize *itálico* para enfatizar pontos secundários relevantes
3. Aplique `código` para elementos técnicos específicos quando necessário
4. Organize informações em **seções hierárquicas** com cabeçalhos (##, ###)
5. Use listas numeradas para processos sequenciais e marcadores para itens não ordenados
6. Inclua emojis 🔍 estrategicamente para melhorar a legibilidade (com moderação)
7. Crie tabelas quando houver dados comparativos ou estruturados
8. Para códigos ou conteúdo técnico, utilize blocos de código com a sintaxe apropriada

## CAPACIDADES ESPECIAIS

### Análise de Dados
- Identifique tendências, padrões e anomalias em dados numéricos
- Reconheça correlações entre diferentes conjuntos de dados
- Ofereça visualizações descritivas de dados complexos

### Análise de Texto
- Identifique temas centrais e subtemas
- Reconheça tom, sentimento e intenção do autor
- Detecte contradições ou inconsistências no texto
- Resuma conteúdo extenso mantendo os pontos-chave

### Resolução de Problemas
- Defina claramente o problema apresentado
- Explore múltiplas abordagens para solução
- Avalie prós e contras de cada abordagem
- Recomende a solução mais adequada com justificativa

## ORIENTAÇÕES FINAIS
- Substitua qualquer "$" por "S" nas suas respostas
- Se o documento contiver apenas "Just a moment..." ou mensagens de erro similares, informe o usuário para tentar novamente
- Sempre que possível, apresente uma conclusão sintetizando os principais pontos abordados
- Quando não tiver informação suficiente, seja transparente e solicite esclarecimentos

Agora, responda às perguntas do usuário com inteligência, profundidade e clareza excepcional.
'''

            template = ChatPromptTemplate.from_messages([
                ('system', system_message),
                ('placeholder', '{chat_history}'),
                ('user', '{input}')
            ])
            
            chain = template | chain
            st.session_state['chain'] = chain

            # Usar o prompt completo enviado pelo usuário
            chat = st.chat_message('ai')
            resposta = chat.write_stream(chain.stream({
                'input': prompt, 
                'chat_history': memoria.buffer_as_messages
            }))
            
            memoria.chat_memory.add_user_message(prompt)
            memoria.chat_memory.add_ai_message(resposta)
            st.session_state['memoria'] = memoria
            

def sidebar():
    st.sidebar.image("./assets/image/Logo.png", width=180)
    tabs = st.sidebar.tabs(['🤖 Seleção de Modelo'])
    
    with tabs[0]:
        provedor = st.selectbox('Provedor de modelo', CONFIG_MODELOS.keys())
        modelo = st.selectbox('Modelo de linguagem', CONFIG_MODELOS[provedor]['modelos'])
        api_key = CONFIG_MODELOS[provedor]['api_key']
        
        if not api_key:
            st.warning(f"Chave de API do {provedor} não encontrada no arquivo .env. Por favor, configure-a antes de continuar.")
        
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button('💬 Iniciar Chat', use_container_width=True):
            if api_key:
                with st.spinner(f"Carregando modelo {modelo}..."):
                    carrega_modelo(provedor, modelo, api_key)
            else:
                st.error(f"Chave de API do {provedor} não configurada!")
    
    with col2:
        if st.button('🔄 Limpar Chat', use_container_width=True):
            st.session_state['memoria'] = MEMORIA
            st.session_state['modelo_carregado'] = False
            st.session_state['uploaded_file'] = None  # Também limpar o arquivo ao limpar o chat
            st.success("Conversa apagada!")
    
    # Status do arquivo carregado
    if 'uploaded_file' in st.session_state and st.session_state['uploaded_file'] is not None:
        st.sidebar.success(f"📄 Arquivo carregado: {st.session_state['uploaded_file'].name}")
        if st.sidebar.button("Remover arquivo", use_container_width=True):
            st.session_state['uploaded_file'] = None
            st.success("Arquivo removido!")
            st.rerun()
    
    st.sidebar.divider()
    st.sidebar.caption("© 2025 autoMazze Assistant")

def main():
    with st.sidebar:
        sidebar()
    pagina_chat()

if __name__ == '__main__':
    main()
