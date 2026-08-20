"""Prepare listening WAVs from scripts and keep DB durations in sync."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.db.models import AudioAsset
from app.db.session import SessionLocal
from app.services.stt import audio_duration_seconds
from app.services.tts import audio_path_for, ensure_script_wav, wav_is_playable

logger = logging.getLogger("northband.tts")


def asset_file(uri: str) -> Path:
    return settings.upload_path / "content" / "audio" / Path(uri).name


async def ensure_asset_audio(asset: AudioAsset) -> float:
    dest = asset_file(asset.uri)
    # If the URI is stale (old sine-tone name), rewrite to a hashed speech file.
    hashed = audio_path_for(
        f"listening_{asset.section_label}",
        asset.transcript or "",
        asset.accent or "en-GB",
    )
    if dest.name.startswith("listening_demo") or dest.name.startswith("listening_section") or not dest.name.endswith(".wav"):
        dest = hashed
        asset.uri = f"content/audio/{hashed.name}"
    duration = await asyncio.to_thread(
        ensure_script_wav,
        asset.transcript or "",
        dest,
        asset.accent or "en-GB",
    )
    asset.uri = f"content/audio/{dest.name}"
    asset.duration_sec = duration
    return duration


async def warmup_listening_audio() -> None:
    if not settings.tts_warmup_on_start:
        return
    try:
        async with SessionLocal() as db:
            assets = (await db.scalars(select(AudioAsset))).all()
            for asset in assets:
                if not (asset.transcript or "").strip():
                    continue
                path = asset_file(asset.uri)
                if wav_is_playable(path):
                    duration = audio_duration_seconds(path) or asset.duration_sec
                    if duration and abs(float(asset.duration_sec or 0) - duration) > 0.5:
                        asset.duration_sec = duration
                    continue
                try:
                    await ensure_asset_audio(asset)
                    logger.info("Prepared listening audio for %s", asset.section_label)
                except Exception:
                    logger.exception("Listening audio warmup failed for %s", asset.uri)
            await db.commit()
    except Exception:
        logger.exception("Listening audio warmup skipped")


async def prepare_set_audio(set_id) -> dict:
    async with SessionLocal() as db:
        assets = (
            await db.scalars(select(AudioAsset).where(AudioAsset.content_set_id == set_id))
        ).all()
        ready = []
        for asset in assets:
            path = asset_file(asset.uri)
            if not wav_is_playable(path):
                await ensure_asset_audio(asset)
            else:
                duration = audio_duration_seconds(path)
                if duration:
                    asset.duration_sec = duration
            ready.append(
                {
                    "id": str(asset.id),
                    "filename": Path(asset.uri).name,
                    "duration_sec": asset.duration_sec,
                    "ready": wav_is_playable(asset_file(asset.uri)),
                }
            )
        await db.commit()
        return {"assets": ready}


async def ensure_filename_audio(filename: str) -> Path:
    safe = Path(filename).name
    path = settings.upload_path / "content" / "audio" / safe
    if wav_is_playable(path):
        return path
    async with SessionLocal() as db:
        assets = (await db.scalars(select(AudioAsset))).all()
        match = next((a for a in assets if Path(a.uri).name == safe), None)
        if match is None:
            # Hashed name might not be stored yet; match by stem prefix.
            match = next((a for a in assets if safe.startswith(Path(a.uri).stem[:18])), None)
        if match is None:
            raise FileNotFoundError(safe)
        await ensure_asset_audio(match)
        await db.commit()
        return asset_file(match.uri)
