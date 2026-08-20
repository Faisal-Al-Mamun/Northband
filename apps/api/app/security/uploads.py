from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import HTTPException, UploadFile, status

from app.config import settings

MAX_AUDIO_BYTES = 15 * 1024 * 1024
ALLOWED_SUFFIXES = {".webm", ".wav", ".mp3", ".m4a", ".ogg"}


async def save_audio_upload(audio: UploadFile) -> Path:
    filename = Path(audio.filename or "recording.webm").name
    suffix = Path(filename).suffix.lower() or ".webm"
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported audio type. Use WebM, WAV, MP3, M4A, or OGG.",
        )

    dest = settings.upload_path / f"{uuid4()}{suffix}"
    total = 0
    try:
        async with aiofiles.open(dest, "wb") as handle:
            while chunk := await audio.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_AUDIO_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Audio must be 15 MB or smaller.",
                    )
                await handle.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except OSError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not store audio") from exc

    if total == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio file")
    return dest
