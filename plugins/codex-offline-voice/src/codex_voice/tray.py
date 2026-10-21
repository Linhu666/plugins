from __future__ import annotations

import os
import threading
from pathlib import Path

from PIL import Image, ImageDraw
import pystray

from .config import default_data_dir
from .overlay import OverlayPresenter, OverlayWindow
from .service import VoiceService


COLORS = {
    "ready": "#2F80ED",
    "recording": "#EB5757",
    "transcribing": "#F2C94C",
    "pasted": "#27AE60",
    "copied": "#27AE60",
    "empty": "#828282",
    "error": "#C0392B",
}


def make_icon(color: str) -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((4, 4, 60, 60), radius=18, fill=color)
    draw.rounded_rectangle((25, 13, 39, 38), radius=7, fill="white")
    draw.arc((17, 23, 47, 51), start=0, end=180, fill="white", width=5)
    draw.line((32, 47, 32, 54), fill="white", width=4)
    draw.line((23, 54, 41, 54), fill="white", width=4)
    return image


class TrayApp:
    def __init__(self, service: VoiceService, overlay=None) -> None:
        self.service = service
        self._status = "正在启动"
        self._lock = threading.RLock()
        self.overlay = overlay or OverlayWindow()
        self._overlay_presenter = OverlayPresenter(self.overlay)
        self.icon = pystray.Icon(
            "CodexOfflineVoice",
            make_icon(COLORS["ready"]),
            "Codex 离线语音",
            menu=pystray.Menu(
                pystray.MenuItem(lambda _: f"状态：{self._status}", None, enabled=False),
                pystray.MenuItem(
                    lambda _: "恢复监听" if self.service.paused else "暂停监听",
                    self._toggle_pause,
                ),
                pystray.MenuItem("打开数据目录", self._open_data_dir),
                pystray.MenuItem("退出", self._exit),
            ),
        )

    def notify(self, status: str, message: str) -> None:
        with self._lock:
            self._status = message
            self.icon.title = f"Codex 离线语音 · {message}"
            self.icon.icon = make_icon(COLORS.get(status, COLORS["ready"]))
        self._overlay_presenter.notify(status, message)

    def _toggle_pause(self, _icon=None, _item=None) -> None:
        if self.service.paused:
            self.service.resume()
            self.notify("ready", "监听已恢复")
        else:
            self.service.pause()
            self.notify("ready", "监听已暂停")

    def _open_data_dir(self, _icon=None, _item=None) -> None:
        path = default_data_dir()
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))

    def _exit(self, _icon=None, _item=None) -> None:
        self.service.stop()
        self.overlay.stop()
        self.icon.stop()

    def run(self) -> None:
        self.overlay.start()
        self.service.start()
        self.icon.run()
