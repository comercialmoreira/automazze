# loaders.py
# Versão robusta e compatível com Python 3.9+

import os
import re
import io
import time
import tempfile
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import streamlit as st

# Site
import requests
from fake_useragent import UserAgent

# Arquivos
from docling.document_converter import DocumentConverter

# YouTube
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    TooManyRequests,
    CouldNotRetrieveTranscript,
)

# Fallback áudio -> Whisper
from openai import OpenAI
import yt_dlp


# ---------------------------------------------------------------------
# Helpers comuns
# ---------------------------------------------------------------------

def _ensure_path_exists(caminho: str) -> None:
    if not os.path.exists(caminho):
        st.error(f"Arquivo não encontrado: {caminho}")
        st.stop()


def _docling_to_text(source: str) -> str:
    """
    Usa Docling para converter qualquer fonte suportada (caminho local ou URL)
    e exporta para texto (plain text). Se desejar Markdown, troque para:
        result.document.export_to_markdown()
    """
    converter = DocumentConverter()
    result = converter.convert(source)
    return result.document.export_to_text()


# ---------------------------------------------------------------------
# Loader de SITES (URL)
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60)
def carrega_site(url: str) -> str:
    """
    Tenta converter diretamente com Docling (HTML suportado).
    Se falhar, faz fallback: baixa HTML com requests e faz limpeza simples.
    """
    if not url or not isinstance(url, str):
        st.error("URL inválida.")
        st.stop()

    # Tenta diretamente com Docling (suporta URL remota)
    try:
        return _docling_to_text(url)
    except Exception:
        # Fallback: requests + limpeza básica de HTML
        pass

    try:
        ua = UserAgent()
        headers = {"User-Agent": ua.random}
    except Exception:
        headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, headers=headers, timeout=25)
        resp.raise_for_status()
        html = resp.text

        # limpeza bem simples de HTML -> texto
        # (se quiser algo melhor, podemos incluir trafilatura/readability)
        text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+\n", "\n", text)
        text = re.sub(r"\n\s+", "\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = text.strip()

        if not text:
            st.error("Não foi possível extrair texto da página.")
            st.stop()
        return text
    except Exception:
        st.error("Não foi possível carregar o site. Verifique a URL e tente novamente.")
        st.stop()


# ---------------------------------------------------------------------
# Loader de CSV
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60)
def carrega_csv(caminho: str) -> str:
    """
    Parser de CSV sem pandas (para evitar dependência extra).
    Retorna um 'preview' tabular em Markdown + CSV bruto.
    """
    _ensure_path_exists(caminho)

    try:
        import csv
        out_lines = []
        with open(caminho, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return "(CSV vazio)"

        # header
        header = rows[0]
        rows_body = rows[1:]

        # Markdown
        md = io.StringIO()
        md.write("| " + " | ".join(header) + " |\n")
        md.write("| " + " | ".join(["---"] * len(header)) + " |\n")
        preview_rows = rows_body[:100]  # limita preview
        for r in preview_rows:
            md.write("| " + " | ".join(r) + " |\n")

        extra = ""
        if len(rows_body) > 100:
            extra = f"\n\n_(+{len(rows_body) - 100} linhas ocultas no preview)_\n"

        return f"### Tabela (preview)\n{md.getvalue()}{extra}\n\n### CSV bruto\n```\n" + \
               open(caminho, 'r', encoding='utf-8', errors='replace').read() + "\n```"
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV: {e}")
        st.stop()


# ---------------------------------------------------------------------
# Loader de PDF
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60)
def carrega_pdf(caminho: str) -> str:
    _ensure_path_exists(caminho)
    try:
        return _docling_to_text(caminho)
    except Exception as e:
        st.error(f"Erro ao carregar o PDF: {e}")
        st.stop()


# ---------------------------------------------------------------------
# Loader de DOCX
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60)
def carrega_docx(caminho: str) -> str:
    _ensure_path_exists(caminho)
    try:
        return _docling_to_text(caminho)
    except Exception as e:
        st.error(f"Erro ao carregar o DOCX: {e}")
        st.stop()


# ---------------------------------------------------------------------
# Loader de TXT
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60)
def carrega_txt(caminho: str) -> str:
    _ensure_path_exists(caminho)
    try:
        with open(caminho, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo de texto: {e}")
        st.stop()


# ---------------------------------------------------------------------
# Loader de IMAGEM (OCR via Docling)
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60)
def carrega_imagem(caminho: str) -> str:
    _ensure_path_exists(caminho)
    try:
        return _docling_to_text(caminho)
    except Exception as e:
        st.error(f"Erro ao carregar a imagem: {e}")
        st.stop()


# ---------------------------------------------------------------------
# YouTube: transcript robusto + fallback Whisper
# ---------------------------------------------------------------------

def _extract_youtube_id(url_or_id: str) -> str:
    """
    Extrai de forma robusta o ID (11 chars) a partir de URL ou ID.
    Suporta: watch?v=, youtu.be, /embed/, /shorts/ e ID cru.
    """
    s = (url_or_id or "").strip()

    # já é ID?
    m = re.match(r"^[a-zA-Z0-9_-]{11}$", s)
    if m:
        return s

    try:
        u = urlparse(s)
    except Exception:
        return s

    host = (u.hostname or "").lower()
    path = (u.path or "").strip("/")

    if host == "youtu.be":
        return path.split("/")[0][:11]

    if "youtube" in host:
        qs = parse_qs(u.query or "")
        if "v" in qs and qs["v"]:
            return qs["v"][0][:11]
        parts = path.split("/")
        for i, p in enumerate(parts):
            if p in ("embed", "shorts", "v"):
                if i + 1 < len(parts):
                    return parts[i + 1][:11]
        if parts and len(parts[0]) >= 11:
            return parts[0][:11]

    return s


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def _try_transcript_text(video_id: str) -> Optional[str]:
    """
    Tenta obter transcript via API do YouTube (prioriza manual > auto).
    """
    preferred = ("pt-BR", "pt", "en")
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)

        # 1) manuais
        for lang in preferred:
            try:
                t = transcripts.find_manually_created_transcript([lang])
                return "\n".join([i["text"] for i in t.fetch()])
            except Exception:
                pass

        # 2) automáticas
        for lang in preferred:
            try:
                t = transcripts.find_generated_transcript([lang])
                return "\n".join([i["text"] for i in t.fetch()])
            except Exception:
                pass

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable,
            TooManyRequests, CouldNotRetrieveTranscript):
        return None
    except Exception:
        # Última tentativa: API "clássica"
        pass

    try:
        data = YouTubeTranscriptApi.get_transcript(video_id, languages=list(preferred))
        return "\n".join([i["text"] for i in data])
    except Exception:
        return None


def _transcribe_with_whisper(video_id: str) -> str:
    """
    Fallback: baixa áudio com yt-dlp e transcreve com Whisper (OpenAI).
    Requer: OPENAI_API_KEY e ffmpeg disponível no ambiente.
    """
    url = "https://www.youtube.com/watch?v={}".format(video_id)

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
            audio_path = Path("{}{}".format(info["id"], ".mp3"))
            if not audio_path.exists():
                for ext in (".m4a", ".webm", ".opus"):
                    p = Path("{}{}".format(info["id"], ext))
                    if p.exists():
                        audio_path = p
                        break

        if not audio_path or not audio_path.exists():
            raise RuntimeError("Falha ao obter arquivo de áudio via yt-dlp.")

        client = OpenAI()  # usa OPENAI_API_KEY
        with audio_path.open("rb") as f:
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
    """
    Fluxo final: transcript público > transcript auto > fallback Whisper.
    """
    vid = _extract_youtube_id(url_ou_id)
    if not vid or len(vid) < 10:
        st.error("Não foi possível identificar o ID do vídeo do YouTube.")
        st.stop()

    # 1) tenta transcript público/auto
    text = _try_transcript_text(vid)
    if text:
        return text

    # 2) fallback: Whisper
    st.info("Sem legenda pública disponível. Usando fallback via Whisper…")
    try:
        return _transcribe_with_whisper(vid)
    except Exception as e:
        st.error("Falha no fallback por Whisper: {}".format(e))
        st.stop()