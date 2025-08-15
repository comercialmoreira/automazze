
import os
from time import sleep
import streamlit as st
from fake_useragent import UserAgent
from docling.document_converter import DocumentConverter
# Imports necessários
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    TooManyRequests,
    CouldNotRetrieveTranscript,
)
from openai import OpenAI

# yt-dlp para baixar apenas o áudio no fallback
import yt_dlp



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

        # --- loaders.py (YouTube robusto) ---
from __future__ import annotations
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import streamlit as st


def _extract_youtube_id(url_or_id: str) -> str:
    """Extrai de forma robusta o ID (11 chars) a partir de URL ou ID."""
    s = (url_or_id or "").strip()

    # caso já seja um ID
    m = re.match(r"^[a-zA-Z0-9_-]{11}$", s)
    if m:
        return s

    try:
        u = urlparse(s)
    except Exception:
        # devolve como veio; Whisper tratará se for inválido
        return s

    host = (u.hostname or "").lower()
    path = (u.path or "").strip("/")

    if host == "youtu.be":
        # https://youtu.be/<id>
        return path.split("/")[0][:11]

    if "youtube" in host:
        # watch?v=ID
        qs = parse_qs(u.query or "")
        if "v" in qs and qs["v"]:
            return qs["v"][0][:11]
        # /embed/ID  ou  /shorts/ID
        parts = path.split("/")
        for i, p in enumerate(parts):
            if p in ("embed", "shorts", "v"):
                if i + 1 < len(parts):
                    return parts[i + 1][:11]
        # last resort: primeiro segmento
        if parts and len(parts[0]) >= 11:
            return parts[0][:11]

    # se nada bateu, retorna s (pode ser ID ou inválido)
    return s


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)  # cache 24h
def _try_transcript_text(video_id: str) -> str | None:
    """Tenta obter transcript por API do YouTube (manual > auto)."""
    preferred = ("pt-BR", "pt", "en")

    # Abordagem mais robusta: usar list_transcripts e tentar manual/auto
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)

        # 1) legendas manuais (prioridade)
        for lang in preferred:
            try:
                t = transcripts.find_manually_created_transcript([lang])
                return "\n".join([i["text"] for i in t.fetch()])
            except Exception:
                pass

        # 2) legendas automáticas
        for lang in preferred:
            try:
                t = transcripts.find_generated_transcript([lang])
                return "\n".join([i["text"] for i in t.fetch()])
            except Exception:
                pass

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, TooManyRequests, CouldNotRetrieveTranscript):
        return None
    except Exception:
        # quedas gerais: tenta API clássica como último suspiro
        pass

    # Última tentativa via API clássica (menos flexível)
    try:
        data = YouTubeTranscriptApi.get_transcript(video_id, languages=list(preferred))
        return "\n".join([i["text"] for i in data])
    except Exception:
        return None


def _transcribe_with_whisper(video_id: str) -> str:
    """Fallback: baixa áudio com yt-dlp e transcreve com OpenAI Whisper."""
    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "outtmpl": "%(id)s.%(ext)s",
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ],
    }

    audio_path = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # yt-dlp pode salvar como .m4a e depois converter p/ .mp3
            # prepare_filename dá o arquivo original; vamos assumir .mp3 no final
            audio_path = Path(f"{info['id']}.mp3")
            if not audio_path.exists():  # fallback se não virou mp3
                for ext in (".m4a", ".webm", ".opus"):
                    p = Path(f"{info['id']}{ext}")
                    if p.exists():
                        audio_path = p
                        break

        if not audio_path or not audio_path.exists():
            raise RuntimeError("Falha ao obter arquivo de áudio via yt-dlp.")

        client = OpenAI()  # usa OPENAI_API_KEY do ambiente/secrets
        with audio_path.open("rb") as f:
            # Whisper-1 em PT (pode trocar language=None para auto)
            result = client.audio.transcriptions.create(
                model="whisper-1",
                language="pt",
                response_format="text",
                file=f,
            )
        return str(result)
    finally:
        # limpeza best-effort
        try:
            if audio_path and audio_path.exists():
                audio_path.unlink()
        except Exception:
            pass


def carrega_youtube(url_ou_id: str) -> str:
    """Carrega texto de um vídeo YouTube.
       Ordem: transcript público > auto > fallback (Whisper)."""
    vid = _extract_youtube_id(url_ou_id)
    if not vid or len(vid) < 10:
        st.error("Não foi possível identificar o ID do vídeo do YouTube.")
        st.stop()

    # 1) tenta transcript público
    text = _try_transcript_text(vid)
    if text:
        return text

    # 2) fallback: Whisper (baixa áudio e transcreve)
    st.info("Sem legenda pública disponível. Usando fallback via Whisper…")
    try:
        return _transcribe_with_whisper(vid)
    except Exception as e:
        st.error(f"Falha no fallback por Whisper: {e}")
        st.stop()