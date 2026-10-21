from __future__ import annotations

import ctypes
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Callable

from .codex_locator import CODEX_PROCESS_NAMES, _get_process_name


def is_codex_window_running() -> bool:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    User32EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    found = [False]

    @User32EnumProc
    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindowTextLengthW(hwnd) <= 0:
            return True
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        process_name = _get_process_name(int(process_id.value)).casefold()
        if process_name in CODEX_PROCESS_NAMES:
            found[0] = True
            return False
        return True

    user32.EnumWindows(callback, 0)
    return found[0]


def start_helper_process() -> subprocess.Popen:
    if getattr(sys, "frozen", False):
        command = [sys.executable]
        working_directory = str(Path(sys.executable).resolve().parent)
    else:
        plugin_root = Path(__file__).resolve().parents[2]
        command = [sys.executable, str(plugin_root / "app_entry.py")]
        working_directory = str(plugin_root)
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        command,
        cwd=working_directory,
        creationflags=creation_flags,
        close_fds=True,
    )


class CodexWatcher:
    def __init__(
        self,
        is_codex_running: Callable[[], bool] = is_codex_window_running,
        start_helper: Callable[[], object] = start_helper_process,
        interval: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._is_codex_running = is_codex_running
        self._start_helper = start_helper
        self._interval = max(0.2, float(interval))
        self._sleep = sleep
        self._child = None
        self._lock = threading.RLock()

    def _stop_child(self) -> None:
        child = self._child
        self._child = None
        if child is None:
            return
        try:
            child.terminate()
            child.wait(timeout=3)
        except Exception:
            try:
                child.kill()
            except Exception:
                pass

    def tick(self) -> None:
        with self._lock:
            if self._child is not None and self._child.poll() is not None:
                self._child = None
            if self._is_codex_running():
                if self._child is None:
                    try:
                        self._child = self._start_helper()
                    except Exception:
                        self._child = None
            else:
                self._stop_child()

    def run(self, stop_event: threading.Event | None = None) -> None:
        stop_event = stop_event or threading.Event()
        try:
            while not stop_event.is_set():
                self.tick()
                stop_event.wait(self._interval)
        finally:
            with self._lock:
                self._stop_child()
