
import os
from time import sleep
import streamlit as st
from fake_useragent import UserAgent
from docling.document_converter import DocumentConverter

from youtube_transcript_api import YouTubeTranscriptApi

def carrega_site(url):
    documento = ''
    for i in range(5):
        try:
            # Verificar se docling está instalado
            try:
                from docling.document_converter import DocumentConverter
            except ImportError:
                st.error("Pacote 'docling' não instalado. Instale com 'pip install docling'")
                st.stop()

            # Configurar o Docling com user-agent aleatório
            user_agent = UserAgent().random
            converter = DocumentConverter()
            
            # Converter a URL para documento
            result = converter.convert(url)
            
            # Extrair o conteúdo como texto
            documento = result.document.export_to_text()
            
            # Verificar se o documento foi carregado com sucesso
            if not documento.strip():
                raise ValueError("Nenhum conteúdo extraído da URL")
                
            break
        except Exception as e:
            print(f'Erro ao carregar o site {i+1}: {str(e)}')
            sleep(3)
    if documento == '':
        st.error('Não foi possível carregar o site. Por favor, verifique a URL e tente novamente.')
        st.stop()
    return documento

def carrega_youtube(video_id):
    try:
        # Verificar se youtube_transcript_api está instalado
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            st.error("Pacote 'youtube-transcript-api' não instalado. Instale com 'pip install youtube-transcript-api'")
            st.stop()

        # Extrair ID do vídeo se for uma URL completa
        if "youtube.com" in video_id or "youtu.be" in video_id:
            video_id = video_id.split("v=")[-1].split("&")[0] if "v=" in video_id else video_id.split("/")[-1]

        # Carregar transcrição
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'pt-BR', 'en'])
        documento = '\n\n'.join([entry['text'] for entry in transcript])
        return documento
    except Exception as e:
        st.error(f"Erro ao carregar o vídeo do YouTube: {e}")
        st.stop()

def carrega_csv(caminho):
    try:
        # Verifica se o arquivo existe
        if not os.path.exists(caminho):
            st.error(f"Arquivo CSV não encontrado: {caminho}")
            st.stop()

        # Verificar se docling está instalado
        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            st.error("Pacote 'docling' não instalado. Instale com 'pip install docling'")
            st.stop()

        # Carregar com Docling
        converter = DocumentConverter()
        result = converter.convert(caminho)
        documento = result.document.export_to_text()
        return documento
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV: {e}")
        st.stop()

def carrega_pdf(caminho):
    try:
        # Verifica se o arquivo existe
        if not os.path.exists(caminho):
            st.error(f"Arquivo PDF não encontrado: {caminho}")
            st.stop()

        # Verificar se docling está instalado
        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            st.error("Pacote 'docling' não instalado. Instale com 'pip install docling'")
            st.stop()

        # Carregar com Docling
        converter = DocumentConverter()
        result = converter.convert(caminho)
        documento = result.document.export_to_text()
        return documento
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo PDF: {e}")
        st.stop()

def carrega_txt(caminho):
    try:
        # Verifica se o arquivo existe
        if not os.path.exists(caminho):
            st.error(f"Arquivo de texto não encontrado: {caminho}")
            st.stop()

        # Verificar se docling está instalado
        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            st.error("Pacote 'docling' não instalado. Instale com 'pip install docling'")
            st.stop()

        # Carregar com Docling
        converter = DocumentConverter()
        result = converter.convert(caminho)
        documento = result.document.export_to_text()
        return documento
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo de texto: {e}")
        st.stop()

def carrega_imagem(caminho):
    try:
        # Verifica se o arquivo existe
        if not os.path.exists(caminho):
            st.error(f"Arquivo de imagem não encontrado: {caminho}")
            st.stop()

        # Verificar se docling está instalado
        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            st.error("Pacote 'docling' não instalado. Instale com 'pip install docling'")
            st.stop()

        # Carregar com Docling
        converter = DocumentConverter()
        result = converter.convert(caminho)
        documento = result.document.export_to_text()
        return documento
    except Exception as e:
        st.error(f"Erro ao carregar a imagem: {e}")
        st.stop()

def carrega_docx(caminho):
    try:
        # Verifica se o arquivo existe
        if not os.path.exists(caminho):
            st.error(f"Arquivo DOCX não encontrado: {caminho}")
            st.stop()

        # Verificar se docling está instalado
        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            st.error("Pacote 'docling' não instalado. Instale com 'pip install docling'")
            st.stop()

        # Carregar com Docling
        converter = DocumentConverter()
        result = converter.convert(caminho)
        documento = result.document.export_to_text()
        return documento
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo DOCX: {e}")
        st.stop()