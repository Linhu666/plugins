from __future__ import annotations

import argparse
import ctypes
import json
import sys
import threading
from pathlib import Path

from .asr import SherpaRecognizer
from .codex_locator import CodexLocator
from .config import AppConfig, default_config_path
from .service import VoiceService
from .windows import enable_dpi_awareness


def _parse_point(value: str) -> tuple[int, int]:
    try:
        x_text, y_text = value.split(",", 1)
        return int(x_text.strip()), int(y_text.strip())
    except Exception as exc:
        raise argparse.ArgumentTypeError("coordinates must be X,Y") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex offline voice input")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--diagnose-point", type=_parse_point)
    parser.add_argument("--transcribe-file", type=Path)
    parser.add_argument("--no-tray", action="store_true")
    parser.add_argument("--watch-codex", action="store_true")
    parser.add_argument("--version", action="version", version="0.1.0")
    return parser


def resolve_model_dir() -> Path:
    override = __import__("os").environ.get("CODEX_VOICE_MODEL_DIR")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "models"
    return Path(__file__).resolve().parents[2] / "runtime" / "models"


class SingleInstance:
    def __init__(self, name: str) -> None:
        self._handle = None
        self._name = name

    def acquire(self) -> bool:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._handle = kernel32.CreateMutexW(None, False, self._name)
        return bool(self._handle) and ctypes.get_last_error() != 183


def _show_error(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, message, "Codex 离线语音", 0x10)


def main(argv: list[str] | None = None) -> int:
    enable_dpi_awareness()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = build_parser().parse_args(argv)
    locator = CodexLocator()

    if args.diagnose_point is not None:
        print(json.dumps(locator.diagnose_point(*args.diagnose_point), ensure_ascii=False, indent=2))
        return 0

    if args.watch_codex:
        watcher_instance = SingleInstance("Local\\CodexOfflineVoiceWatcher")
        if not watcher_instance.acquire():
            return 0
        from .watcher import CodexWatcher

        try:
            CodexWatcher().run()
        except KeyboardInterrupt:
            pass
        return 0

    model_dir = resolve_model_dir()
    if args.transcribe_file is not None:
        try:
            text = SherpaRecognizer(model_dir).transcribe_wav(args.transcribe_file)
        except Exception as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps({"ok": True, "text": text}, ensure_ascii=False))
        return 0

    instance = SingleInstance("Local\\CodexOfflineVoice")
    if not instance.acquire():
        _show_error("Codex 离线语音已经在运行。")
        return 0

    try:
        SherpaRecognizer._find_model_files(model_dir)
    except Exception as exc:
        _show_error(f"离线模型不可用：\n{exc}")
        return 2

    config = AppConfig.load(args.config or default_config_path())
    service = VoiceService(config, model_dir, locator=locator)
    if args.no_tray:
        service.start()
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            service.stop()
        return 0

    from .tray import TrayApp

    tray = TrayApp(service)
    service._notify = tray.notify
    tray.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
