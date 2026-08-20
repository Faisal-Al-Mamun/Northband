from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import threading
import wave
from pathlib import Path

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger("northband.stt")

CLOUD_WHISPER_MODELS = {"whisper-1", "gpt-4o-mini-transcribe", "gpt-4o-transcribe"}
LOCAL_WHISPER_MODELS = {"tiny", "base", "small", "medium", "large-v2", "large-v3", "turbo", "distil-large-v3"}

_model_lock = threading.Lock()
_whisper_model = None


def audio_duration_seconds(path: str | Path | None) -> float | None:
    if not path:
        return None
    audio_path = Path(path)
    if not audio_path.exists():
        return None
    try:
        with wave.open(str(audio_path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
            if rate:
                return frames / float(rate)
    except Exception:
        pass
    try:
        from mutagen import File as MutagenFile

        audio = MutagenFile(str(audio_path))
        length = getattr(getattr(audio, "info", None), "length", None)
        if length:
            return float(length)
    except Exception:
        return None
    return None


def local_whisper_model_name() -> str:
    name = (settings.whisper_model or "").strip()
    if not name or name in CLOUD_WHISPER_MODELS:
        return "base"
    return name


def cloud_whisper_model_name() -> str:
    name = (settings.whisper_model or "").strip()
    if not name or name in LOCAL_WHISPER_MODELS:
        return "whisper-1"
    return name


def _get_faster_whisper_model():
    global _whisper_model
    with _model_lock:
        if _whisper_model is None:
            from faster_whisper import WhisperModel

            model_name = local_whisper_model_name()
            logger.info("Loading faster-whisper model %s (cpu/int8)", model_name)
            _whisper_model = WhisperModel(
                model_name,
                device=settings.stt_device,
                compute_type=settings.stt_compute_type,
            )
        return _whisper_model


def warmup_stt() -> None:
    if settings.stt_provider not in {"auto", "faster_whisper", "local"}:
        return
    try:
        _get_faster_whisper_model()
    except Exception:
        logger.exception("faster-whisper warmup skipped")


def _pcm_wav_for_whisper(path: Path) -> Path:
    """Resample to 16 kHz mono WAV so Whisper does less work on browser WebM."""
    if path.suffix.lower() == ".wav":
        return path
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return path
    dest = path.with_name(f"{path.stem}.whisper.wav")
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    result = subprocess.run(
        [ffmpeg, "-y", "-i", str(path), "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", str(dest)],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not dest.exists():
        logger.warning("ffmpeg could not convert %s; transcribing original", path.name)
        return path
    return dest


def _transcribe_faster_whisper_sync(path: Path) -> str:
    model = _get_faster_whisper_model()
    audio = _pcm_wav_for_whisper(path)
    segments, _info = model.transcribe(
        str(audio),
        language="en",
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    text = " ".join(segment.text.strip() for segment in segments if segment.text).strip()
    if audio != path:
        audio.unlink(missing_ok=True)
    return text


async def _transcribe_faster_whisper(path: Path) -> str:
    return await asyncio.to_thread(_transcribe_faster_whisper_sync, path)


async def _transcribe_openai_compat(path: Path, *, base_url: str, api_key: str, label: str) -> str:
    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    with path.open("rb") as handle:
        result = await client.audio.transcriptions.create(
            model=cloud_whisper_model_name(),
            file=handle,
        )
    text = (result.text or "").strip()
    if not text:
        raise RuntimeError(f"{label} returned an empty transcript")
    return text


async def _transcribe_gemini(path: Path) -> str:
    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    uploaded = await client.aio.files.upload(file=str(path))
    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=[
            "Transcribe this spoken English audio verbatim. Return plain text only.",
            uploaded,
        ],
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty transcript")
    return text


def _prefer_local(provider: str) -> bool:
    return provider in {"auto", "faster_whisper", "local"}


def _allow_cloud_fallback(provider: str) -> bool:
    return provider in {"auto", "openai_compat", "openai", "openrouter", "gemini"}


async def transcribe_audio(path: str | Path) -> tuple[str, str]:
    """Return (transcript, provider_used). Local faster-whisper is preferred."""
    audio_path = Path(path)
    if not audio_path.exists():
        raise FileNotFoundError(str(audio_path))

    provider = (settings.stt_provider or "auto").strip().lower()
    errors: list[str] = []

    if _prefer_local(provider):
        try:
            text = await _transcribe_faster_whisper(audio_path)
            if text:
                return text, "faster_whisper"
            errors.append("faster-whisper returned empty text")
        except Exception as exc:
            logger.warning("faster-whisper failed: %s", exc)
            errors.append(str(exc))
            if provider in {"faster_whisper", "local"}:
                raise RuntimeError(
                    "Local speech-to-text failed. Install ffmpeg and faster-whisper, "
                    "or paste a transcript instead."
                ) from exc

    if _allow_cloud_fallback(provider) and settings.openai_compat_api_key:
        try:
            text = await _transcribe_openai_compat(
                audio_path,
                base_url=settings.openai_compat_base_url,
                api_key=settings.openai_compat_api_key,
                label="openai_compat",
            )
            return text, "openai_compat"
        except Exception as exc:
            logger.warning("openai_compat STT failed: %s", exc)
            errors.append(str(exc))

    if provider == "openrouter" and settings.openrouter_api_key:
        try:
            text = await _transcribe_openai_compat(
                audio_path,
                base_url=settings.openrouter_base_url,
                api_key=settings.openrouter_api_key,
                label="openrouter",
            )
            return text, "openrouter"
        except Exception as exc:
            logger.warning("openrouter STT failed: %s", exc)
            errors.append(str(exc))

    if _allow_cloud_fallback(provider) and settings.gemini_api_key:
        try:
            text = await _transcribe_gemini(audio_path)
            return text, "gemini"
        except Exception as exc:
            logger.warning("gemini STT failed: %s", exc)
            errors.append(str(exc))

    detail = errors[-1] if errors else "no speech-to-text provider available"
    raise RuntimeError(
        "Speech-to-text is unavailable. Local faster-whisper is the default "
        f"({detail}). Configure OPENAI_COMPAT_API_KEY only as a fallback, "
        "or submit a transcript instead."
    )
