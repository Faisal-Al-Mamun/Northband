from app.services.stt import cloud_whisper_model_name, local_whisper_model_name
from app.config import settings


def test_local_model_defaults_to_base_when_cloud_name_is_set(monkeypatch):
    monkeypatch.setattr(settings, "whisper_model", "whisper-1")
    assert local_whisper_model_name() == "base"
    assert cloud_whisper_model_name() == "whisper-1"


def test_cloud_fallback_uses_whisper_1_when_local_size_is_set(monkeypatch):
    monkeypatch.setattr(settings, "whisper_model", "base")
    assert local_whisper_model_name() == "base"
    assert cloud_whisper_model_name() == "whisper-1"


def test_explicit_local_size_is_kept(monkeypatch):
    monkeypatch.setattr(settings, "whisper_model", "small")
    assert local_whisper_model_name() == "small"
