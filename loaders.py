# loaders.py
# Versão robusta (compatível Python 3.9+), com lazy imports para evitar ImportError
# e com pipeline YouTube -> Transcript (manual/auto) -> Fallback Whisper (yt-dlp + OpenAI)

import os
import re
import io
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import streamlit as st


# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------

def _ensure_path_exists(path: str) -> None:
    if not os.path.exists(path):
        st.error(f"Arquivo não encontrado: {path}")
        st.stop()


def _docling_to_text(source: str) -> str:
    """Converte fonte (arquivo local ou URL) para texto via Docling."""
    try:
        from docling.document_converter import DocumentConverter  # lazy import
    except Exception as e:
        raise RuntimeError(
            "Pacote 'docling' não instalado ou com erro. Adicione 'docling' ao requirements.txt"
        ) from e

    converter = DocumentConverter()
    result = converter.convert(source)
    return result.document.export_to_text()


# ---------------------------------------------------------------------
# Loader de SITES (URL)
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60)
def carrega_site(url: str) -> str:
    """
    Tenta Docling direto; se falhar, faz fallback com requests + limpeza simples de HTML.
    """
    if not url or not isinstance(url, str):
        st.error("URL inválida.")
        st.stop()

    # 1) Tenta Docling (suporta URL remota)
    try:
        return _docling_to_text(url)
    except Exception:
        pass

    # 2) Fallback requests -> texto simples
    try:
        try:
            from fake_useragent import UserAgent  # lazy import
            headers = {"User-Agent": UserAgent().random}
        except Exception:
            headers = {"User-Agent": "Mozilla/5.0"}

        import requests  # lazy import
        resp = requests.get(url, headers=headers, timeout=25)
        resp.raise_for_status()
        html = resp.text

        # Limpeza muito simples de HTML -> texto
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
# Loaders de Arquivos (PDF, DOCX, TXT, CSV, IMAGEM)
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=60 * 60)
def carrega_pdf(path: str) -> str:
    _ensure_path_exists(path)
    try:
        return _docling_to_text(path)
    except Exception as e:
        st.error(f"Erro ao carregar o PDF: {e}")
        st.stop()


@st.cache_data(show_spinner=False, ttl=60 * 60)
def carrega_docx(path: str) -> str:
    _ensure_path_exists(path)
    try:
        return _docling_to_text(path)
    except Exception as e:
        st.error(f"Erro ao carregar o DOCX: {e}")
        st.stop()


@st.cache_data(show_spinner=False, ttl=60 * 60)
def carrega_txt(path: str) -> str:
    _ensure_path_exists(path)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo de texto: {e}")
        st.stop()


@st.cache_data(show_spinner=False, ttl=60 * 60)
def carrega_csv(path: str) -> str:
    _ensure_path_exists(path)
    try:
        import csv  # lazy import
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            rows = list(csv.reader(f))
        if not rows:
            return "(CSV vazio)"
        header, body = rows[0], rows[1:]
        preview = body[:100]
        buf = io.StringIO()
        buf.write("| " + " | ".join(header) + " |\n")
        buf.write("| " + " | ".join(["---"] * len(header)) + " |\n")
        for r in preview:
            buf.write("| " + " | ".join(r) + " |\n")
        extra = "\n\n_(+{} linhas ocultas no preview)_\n".format(max(0, len(body) - 100)) if len(body) > 100 else ""
        raw = open(path, 'r', encoding='utf-8', errors='replace').read()
        return f"### Tabela (preview)\n{buf.getvalue()}{extra}\n\n### CSV bruto\n```\n{raw}\n```"
    except Exception as e:
        st.error(f"Erro ao carregar o CSV: {e}")
        st.stop()


@st.cache_data(show_spinner=False, ttl=60 * 60)
def carrega_imagem(path: str) -> str:
    _ensure_path_exists(path)
    try:
        return _docling_to_text(path)  # Docling usa OCR quando aplicável
    except Exception as e:
        st.error(f"Erro ao carregar a imagem: {e}")
        st.stop()


# ---------------------------------------------------------------------
# YouTube: transcript robusto + fallback Whisper
# ---------------------------------------------------------------------

def _extract_youtube_id(url_or_id: str) -> str:
    """Extrai o ID (11 chars) a partir de URL ou ID cru."""
    s = (url_or_id or "").strip()
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
            if p in ("embed", "shorts", "v") and i + 1 < len(parts):
                return parts[i + 1][:11]
        if parts and len(parts[0]) >= 11:
            return parts[0][:11]
    return s


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def _try_transcript_text(video_id: str) -> Optional[str]:
    """Tenta obter transcript via API do YouTube (manual > auto)."""
    try:
        # lazy import para evitar ImportError na importação do módulo loaders
        from youtube_transcript_api import (
            YouTubeTranscriptApi,
            TranscriptsDisabled,
            NoTranscriptFound,
            VideoUnavailable,
            TooManyRequests,
            CouldNotRetrieveTranscript,
        )
    except Exception:
        # Biblioteca ausente -> sem transcript; retornamos None para cair no fallback Whisper
        return None

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
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, TooManyRequests, CouldNotRetrieveTranscript):
        return None
    except Exception:
        pass

    try:
        data = YouTubeTranscriptApi.get_transcript(video_id, languages=list(preferred))
        return "\n".join([i["text"] for i in data])
    except Exception:
        return None


def _transcribe_with_whisper(video_id: str) -> str:
    """
    Fallback: baixa áudio com yt-dlp e transcreve com Whisper (OpenAI).
    Requer: OPENAI_API_KEY e ffmpeg no ambiente.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        import yt_dlp  # lazy import
    except Exception as e:
        raise RuntimeError(
            "Pacote 'yt-dlp' não encontrado. Adicione 'yt-dlp>=2024.10.22' ao requirements.txt"
        ) from e

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "outtmpl": "%(id)s.%(ext)s",
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ],
    }

    audio_path: Optional[Path] = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = Path(f"{info['id']}.mp3")
            if not audio_path.exists():
                for ext in (".m4a", ".webm", ".opus"):
                    p = Path(f"{info['id']}{ext}")
                    if p.exists():
                        audio_path = p
                        break
        if not audio_path or not audio_path.exists():
            raise RuntimeError("Falha ao obter arquivo de áudio via yt-dlp.")

        try:
            from openai import OpenAI  # lazy import
        except Exception as e:
            raise RuntimeError(
                "Pacote 'openai' não encontrado. Adicione 'openai>=1.3.0' ao requirements.txt"
            ) from e

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
        try:
            if audio_path and audio_path.exists():
                audio_path.unlink()
        except Exception:
            pass


def carrega_youtube(url_ou_id: str) -> str:
    """Fluxo: transcript público > auto > fallback Whisper."""
    vid = _extract_youtube_id(url_ou_id)
    if not vid or len(vid) < 10:
        st.error("Não foi possível identificar o ID do vídeo do YouTube.")
        st.stop()

    text = _try_transcript_text(vid)
    if text:
        return text

    st.info("Sem legenda pública disponível. Usando fallback via Whisper…")
    try:
        return _transcribe_with_whisper(vid)
    except Exception as e:
        st.error(f"Falha no fallback por Whisper: {e}")
        st.stop()
