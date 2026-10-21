from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path


def default_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "CodexOfflineVoice"
    return Path.home() / "AppData" / "Local" / "CodexOfflineVoice"


def default_config_path() -> Path:
    return default_data_dir() / "config.json"


@dataclass
class AppConfig:
    hold_ms: int = 200
    max_record_seconds: int = 60
    sample_rate: int = 16000
    threads: int = 2
    auto_paste: bool = True
    restore_clipboard: bool = True
    audio_cues: bool = True
    noise_filter: bool = True
    vad_threshold: float = 0.45
    min_voice_rms_dbfs: float = -50.0
    input_device: str | None = None

    def validate(self) -> None:
        self.hold_ms = min(2000, max(150, int(self.hold_ms)))
        self.max_record_seconds = min(300, max(5, int(self.max_record_seconds)))
        self.sample_rate = 16000
        self.threads = min(8, max(1, int(self.threads)))
        self.auto_paste = bool(self.auto_paste)
        self.restore_clipboard = bool(self.restore_clipboard)
        self.audio_cues = bool(self.audio_cues)
        self.noise_filter = bool(self.noise_filter)
        self.vad_threshold = min(0.95, max(0.05, float(self.vad_threshold)))
        self.min_voice_rms_dbfs = min(-20.0, max(-80.0, float(self.min_voice_rms_dbfs)))
        if self.input_device is not None:
            self.input_device = str(self.input_device).strip() or None

    @classmethod
    def from_mapping(cls, data: dict) -> "AppConfig":
        allowed = {field.name for field in fields(cls)}
        config = cls(**{key: value for key, value in data.items() if key in allowed})
        config.validate()
        return config

    @classmethod
    def load(cls, path: Path | str | None = None) -> "AppConfig":
        path = Path(path or default_config_path())
        if not path.exists():
            return cls().with_validation()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("config root must be an object")
            return cls.from_mapping(data)
        except Exception:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            backup = path.with_name(f"config.corrupt-{stamp}.json")
            try:
                backup.write_bytes(path.read_bytes())
            except OSError:
                pass
            return cls().with_validation()

    def with_validation(self) -> "AppConfig":
        self.validate()
        return self

    def save(self, path: Path | str | None = None) -> None:
        path = Path(path or default_config_path())
        self.validate()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n"
        handle, temp_name = tempfile.mkstemp(prefix="config.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, path)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
