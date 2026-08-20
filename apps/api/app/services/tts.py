"""Listening audio synthesis.

Primary engine is Kyutai Pocket TTS (CPU). Falls back to macOS `say` so
recordings are always real speech — never a 3-second sine tone.
"""

from __future__ import annotations

import hashlib
import logging
import re
import struct
import subprocess
import tempfile
import threading
import wave
from pathlib import Path

from app.config import settings
from app.services.stt import audio_duration_seconds

logger = logging.getLogger("northband.tts")

TURN_RE = re.compile(r"^([A-Za-z][A-Za-z0-9' _/-]{0,40}):\s*(.*)$")

POCKET_VOICES = {
    "narrator": "charles",
    "advisor": "alba",
    "officer": "alba",
    "receptionist": "anna",
    "reception": "anna",
    "student": "jean",
    "mina": "jane",
    "guide": "stuart_bell",
    "tutor": "mary",
    "sara": "mary",
    "tom": "paul",
    "lecturer": "michael",
    "professor": "michael",
    "agent": "stuart_bell",
    "owen": "paul",
    "speaker": "alba",
    "nadia": "jane",
    "mei": "mary",
    "callum": "jean",
}

SAY_VOICES = {
    "en-GB": {
        "narrator": "Daniel",
        "advisor": "Flo",
        "officer": "Flo",
        "receptionist": "Shelley",
        "reception": "Shelley",
        "student": "Reed",
        "mina": "Sandy",
        "guide": "Daniel",
        "tutor": "Moira",
        "sara": "Moira",
        "tom": "Eddy",
        "lecturer": "Daniel",
        "professor": "Daniel",
    },
    "en-AU": {
        "narrator": "Karen",
        "receptionist": "Karen",
        "reception": "Karen",
        "student": "Daniel",
        "mina": "Karen",
    },
    "en-US": {
        "narrator": "Samantha",
        "tutor": "Samantha",
        "sara": "Samantha",
        "student": "Albert",
        "tom": "Fred",
        "lecturer": "Fred",
        "professor": "Albert",
        "guide": "Fred",
    },
}

_pocket_lock = threading.Lock()
_pocket_model = None
_pocket_states: dict[str, object] = {}
_file_locks: dict[str, threading.Lock] = {}
_file_locks_guard = threading.Lock()


def parse_script(script: str) -> list[tuple[str, str]]:
    """Split an IELTS-style script into (role, text) turns."""
    turns: list[tuple[str, str]] = []
    role = "Narrator"
    buf: list[str] = []

    def flush() -> None:
        text = " ".join(part.strip() for part in buf if part.strip())
        if text:
            turns.append((role, text))
        buf.clear()

    for raw in (script or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        match = TURN_RE.match(line)
        if match:
            flush()
            role = match.group(1).strip()
            rest = match.group(2).strip()
            if rest:
                buf.append(rest)
        else:
            buf.append(line)
    flush()
    if not turns and (script or "").strip():
        turns.append(("Narrator", " ".join((script or "").split())))
    return turns


def script_fingerprint(script: str, accent: str) -> str:
    payload = f"{accent}\n{script.strip()}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:12]


def audio_path_for(stem: str, script: str, accent: str) -> Path:
    name = f"{stem}_{script_fingerprint(script, accent)}.wav"
    return settings.upload_path / "content" / "audio" / name


def wav_is_playable(path: Path, min_seconds: float = 6.0) -> bool:
    if not path.exists() or path.stat().st_size < 4000:
        return False
    duration = audio_duration_seconds(path) or 0.0
    return duration >= min_seconds


def _file_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _file_locks_guard:
        lock = _file_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _file_locks[key] = lock
        return lock


def _pcm16_silence(sample_rate: int, seconds: float) -> bytes:
    n = max(0, int(sample_rate * seconds))
    return b"\x00\x00" * n


def _floats_to_pcm16(samples: list[float] | object) -> bytes:
    if hasattr(samples, "detach"):
        samples = samples.detach().cpu().float().numpy().reshape(-1)
    elif hasattr(samples, "numpy"):
        samples = samples.numpy().reshape(-1)
    else:
        samples = list(samples)
    try:
        import numpy as np

        arr = np.asarray(samples, dtype=np.float64).reshape(-1)
        peak = float(np.max(np.abs(arr))) if arr.size else 0.0
        if peak > 1.5:
            arr = arr / 32767.0
            peak = float(np.max(np.abs(arr))) if arr.size else 0.0
        if peak > 0:
            arr = arr / peak * 0.92
        pcm = np.clip(arr * 32767.0, -32767, 32767).astype("<i2")
        return pcm.tobytes()
    except Exception:
        values = [float(v) for v in samples]
        peak = max((abs(v) for v in values), default=0.0)
        if peak > 1.5:
            values = [v / 32767.0 for v in values]
            peak = max((abs(v) for v in values), default=0.0)
        scale = (0.92 / peak) if peak else 0.0
        frames = bytearray()
        for value in values:
            frames += struct.pack("<h", int(max(-1.0, min(1.0, value * scale)) * 32767))
        return bytes(frames)


def _write_wav(path: Path, pcm: bytes, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.wav")
    with wave.open(str(tmp), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm)
    tmp.replace(path)


def _read_wav_pcm(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as handle:
        rate = handle.getframerate()
        width = handle.getsampwidth()
        channels = handle.getnchannels()
        frames = handle.readframes(handle.getnframes())
    if width != 2:
        raise ValueError(f"Unsupported sample width {width}")
    if channels == 2:
        # Downmix stereo by taking the left channel.
        left = bytearray()
        for i in range(0, len(frames), 4):
            left += frames[i : i + 2]
        frames = bytes(left)
    return frames, rate


def _concat_pcm(chunks: list[tuple[bytes, int]], pause_sec: float = 0.45) -> tuple[bytes, int]:
    if not chunks:
        return b"", 22050
    rate = chunks[0][1]
    pause = _pcm16_silence(rate, pause_sec)
    out = bytearray()
    for index, (pcm, chunk_rate) in enumerate(chunks):
        if chunk_rate != rate:
            raise ValueError("Mixed sample rates in listening render")
        if index:
            out += pause
        out += pcm
    return bytes(out), rate


def _role_key(role: str) -> str:
    return re.sub(r"[^a-z]+", "", role.lower())


def pocket_voice_for(role: str) -> str:
    return POCKET_VOICES.get(_role_key(role), "alba")


def say_voice_for(role: str, accent: str) -> str:
    table = SAY_VOICES.get(accent) or SAY_VOICES["en-GB"]
    default = "Daniel" if accent == "en-GB" else "Karen" if accent == "en-AU" else "Samantha"
    return table.get(_role_key(role), default)


def _load_pocket():
    global _pocket_model
    if _pocket_model is not None:
        return _pocket_model
    from pocket_tts import TTSModel

    logger.info("Loading Pocket TTS model (CPU)")
    _pocket_model = TTSModel.load_model()
    return _pocket_model


def _pocket_state(voice: str):
    if voice in _pocket_states:
        return _pocket_states[voice]
    model = _load_pocket()
    state = model.get_state_for_audio_prompt(voice)
    _pocket_states[voice] = state
    return state


def _render_pocket(turns: list[tuple[str, str]]) -> tuple[bytes, int] | None:
    try:
        import pocket_tts  # noqa: F401
    except Exception:
        return None
    with _pocket_lock:
        try:
            model = _load_pocket()
            chunks: list[tuple[bytes, int]] = []
            for role, text in turns:
                voice = pocket_voice_for(role)
                state = _pocket_state(voice)
                audio = model.generate_audio(state, text)
                pcm = _floats_to_pcm16(audio)
                chunks.append((pcm, int(model.sample_rate)))
            return _concat_pcm(chunks, pause_sec=0.55)
        except Exception:
            logger.exception("Pocket TTS in-process render failed")
            return None


def _pocket_cli_available() -> bool:
    from shutil import which

    return which("pocket-tts") is not None or which("uvx") is not None


def _render_pocket_cli(turns: list[tuple[str, str]]) -> tuple[bytes, int] | None:
    if not _pocket_cli_available():
        return None
    from shutil import which

    chunks: list[tuple[bytes, int]] = []
    with tempfile.TemporaryDirectory(prefix="nb-tts-") as tmp:
        tmp_path = Path(tmp)
        for index, (role, text) in enumerate(turns):
            dest = tmp_path / f"turn-{index}.wav"
            voice = pocket_voice_for(role)
            if which("pocket-tts"):
                cmd = ["pocket-tts", "generate", "--text", text, "--voice", voice, "--output-path", str(dest)]
            else:
                cmd = [
                    "uvx",
                    "pocket-tts",
                    "generate",
                    "--text",
                    text,
                    "--voice",
                    voice,
                    "--output-path",
                    str(dest),
                ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180)
            except Exception:
                logger.exception("pocket-tts CLI failed for turn %s", index)
                return None
            if not dest.exists():
                fallback = Path("tts_output.wav")
                if fallback.exists():
                    fallback.replace(dest)
                else:
                    return None
            pcm, rate = _read_wav_pcm(dest)
            chunks.append((pcm, rate))
    try:
        return _concat_pcm(chunks, pause_sec=0.55)
    except Exception:
        logger.exception("Failed to concatenate Pocket TTS CLI turns")
        return None


def _say_one(text: str, voice: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    aiff = dest.with_suffix(".aiff")
    subprocess.run(
        ["say", "-v", voice, "-r", "165", "-o", str(aiff), text],
        check=True,
        capture_output=True,
        timeout=120,
    )
    convert = subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@22050", str(aiff), str(dest)],
        capture_output=True,
        timeout=60,
    )
    if convert.returncode != 0 or not dest.exists():
        # Newer macOS can write wav directly.
        subprocess.run(
            ["say", "-v", voice, "-r", "165", "-o", str(dest), "--data-format=LEI16@22050", text],
            check=True,
            capture_output=True,
            timeout=120,
        )
    if aiff.exists():
        aiff.unlink(missing_ok=True)


def _render_say(turns: list[tuple[str, str]], accent: str) -> tuple[bytes, int] | None:
    from shutil import which

    if which("say") is None:
        return None
    chunks: list[tuple[bytes, int]] = []
    with tempfile.TemporaryDirectory(prefix="nb-say-") as tmp:
        tmp_path = Path(tmp)
        for index, (role, text) in enumerate(turns):
            dest = tmp_path / f"turn-{index}.wav"
            try:
                _say_one(text, say_voice_for(role, accent), dest)
                pcm, rate = _read_wav_pcm(dest)
            except Exception:
                logger.exception("macOS say failed for turn %s", index)
                return None
            chunks.append((pcm, rate))
    try:
        return _concat_pcm(chunks, pause_sec=0.5)
    except Exception:
        logger.exception("Failed to concatenate say turns")
        return None


def render_script_wav(script: str, dest: Path, accent: str = "en-GB") -> float:
    """Render a multi-speaker script to WAV. Returns duration in seconds."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with _file_lock(dest):
        if wav_is_playable(dest):
            return float(audio_duration_seconds(dest) or 0.0)
        turns = parse_script(script)
        if not turns:
            raise ValueError("Empty listening script")

        engine = (settings.tts_engine or "auto").lower()
        rendered: tuple[bytes, int] | None = None
        if engine in {"auto", "pocket"}:
            rendered = _render_pocket(turns)
            if rendered is None and engine in {"auto", "pocket"}:
                rendered = _render_pocket_cli(turns)
        if rendered is None and engine in {"auto", "say"}:
            rendered = _render_say(turns, accent)
        if rendered is None:
            raise RuntimeError(
                "Could not synthesize listening audio. Install pocket-tts "
                "(pip install pocket-tts) or use macOS say."
            )
        pcm, rate = rendered
        _write_wav(dest, pcm, rate)
        duration = float(audio_duration_seconds(dest) or (len(pcm) / 2 / rate))
        logger.info("Wrote listening audio %s (%.1fs, %s Hz)", dest.name, duration, rate)
        return duration


def ensure_script_wav(script: str, dest: Path, accent: str = "en-GB") -> float:
    dest = Path(dest)
    if wav_is_playable(dest):
        return float(audio_duration_seconds(dest) or 0.0)
    return render_script_wav(script, dest, accent)
