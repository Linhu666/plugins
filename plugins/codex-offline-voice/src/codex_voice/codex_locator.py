from __future__ import annotations

import ctypes
import queue
import threading
import time
from concurrent.futures import Future
from ctypes import wintypes
from dataclasses import dataclass, replace
from pathlib import PureWindowsPath
from typing import Any


CODEX_PROCESS_NAMES = frozenset({"chatgpt.exe", "codex.exe"})
EDITABLE_TYPES = frozenset({"edit"})
DOCUMENT_HINTS = ("message", "composer", "prompt", "输入")


@dataclass(frozen=True)
class ControlInfo:
    control_type: str
    name: str
    process_id: int
    process_name: str
    top_level_name: str
    rect: tuple[int, int, int, int] | None = None
    top_level_rect: tuple[int, int, int, int] | None = None


def normalize_control_type(value: str) -> str:
    normalized = value.rsplit(".", 1)[-1].strip().lower()
    if normalized.endswith("control"):
        normalized = normalized[: -len("control")]
    return normalized


def is_codex_process(process_name: str) -> bool:
    return PureWindowsPath(process_name).name.lower() in CODEX_PROCESS_NAMES


def is_codex_editable(info: ControlInfo) -> bool:
    if not is_codex_process(info.process_name):
        return False
    control_type = normalize_control_type(info.control_type)
    if control_type in EDITABLE_TYPES:
        return True
    if control_type == "document":
        name = info.name.casefold()
        return any(hint in name for hint in DOCUMENT_HINTS)
    if control_type == "text" and info.rect is not None and info.top_level_rect is not None:
        left, top, right, bottom = info.top_level_rect
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            return False
        control_left, control_top, control_right, control_bottom = info.rect
        center_x = (control_left + control_right) / 2
        center_y = (control_top + control_bottom) / 2
        x_ratio = (center_x - left) / width
        y_ratio = (center_y - top) / height
        return 0.15 <= x_ratio <= 0.95 and y_ratio >= 0.85
    return False


def _get_process_name(process_id: int) -> str:
    if process_id <= 0:
        return ""
    process_query_limited_information = 0x1000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(process_query_limited_information, False, process_id)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        ok = kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size))
        return PureWindowsPath(buffer.value).name if ok else ""
    finally:
        kernel32.CloseHandle(handle)


def _rect_of(control: Any) -> tuple[int, int, int, int] | None:
    try:
        rect = control.BoundingRectangle
        values = (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))
        if values[2] > values[0] and values[3] > values[1]:
            return values
    except Exception:
        pass
    return None




def _window_info_from_point(x: int, y: int) -> tuple[str, tuple[int, int, int, int]] | None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    hwnd = user32.WindowFromPoint(wintypes.POINT(x, y))
    root = user32.GetAncestor(hwnd, 2) if hwnd else None
    if not root:
        return None
    rect = wintypes.RECT()
    if not user32.GetWindowRect(root, ctypes.byref(rect)):
        return None
    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(root, ctypes.byref(process_id))
    process_name = _get_process_name(int(process_id.value))
    values = (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))
    return process_name, values


def _window_rect_from_point(x: int, y: int) -> tuple[int, int, int, int] | None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    hwnd = user32.WindowFromPoint(wintypes.POINT(x, y))
    if not hwnd:
        return None
    root = user32.GetAncestor(hwnd, 2)
    if not root:
        return None
    rect = wintypes.RECT()
    if not user32.GetWindowRect(root, ctypes.byref(rect)):
        return None
    values = (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))
    return values if values[2] > values[0] and values[3] > values[1] else None


def _read_control(
    control: Any,
    process_name_resolver: Callable[[int], str] = _get_process_name,
) -> ControlInfo:
    process_id = int(getattr(control, "ProcessId", 0) or 0)
    process_name = process_name_resolver(process_id)
    hit_type = str(getattr(control, "ControlTypeName", "") or "")
    hit_name = str(getattr(control, "Name", "") or "")
    hit_rect = _rect_of(control)
    top_level_rect = hit_rect
    editable_type = ""
    editable_name = hit_name
    current = control
    top_level_name = ""
    seen: set[int] = set()
    for _ in range(64):
        current_name = str(getattr(current, "Name", "") or "")
        current_type = str(getattr(current, "ControlTypeName", "") or "")
        top_level_name = current_name or top_level_name
        top_level_rect = _rect_of(current) or top_level_rect
        if not editable_type and normalize_control_type(current_type) in {"edit", "document"}:
            editable_type = current_type
            editable_name = current_name or hit_name
        parent = current.GetParentControl()
        if parent is None or id(parent) in seen:
            break
        seen.add(id(parent))
        current = parent
    return ControlInfo(
        control_type=editable_type or hit_type,
        name=editable_name or hit_name,
        process_id=process_id,
        process_name=process_name,
        top_level_name=top_level_name,
        rect=hit_rect,
        top_level_rect=top_level_rect,
    )


class CodexLocator:
    def __init__(
        self,
        inspector=None,
        initializer_factory=None,
        process_name_resolver=None,
        retry_sleep=None,
        window_rect_provider=None,
        window_info_provider=None,
    ) -> None:
        self._inspector = inspector
        self._initializer_factory = initializer_factory
        self._process_name_resolver = process_name_resolver or _get_process_name
        self._retry_sleep = retry_sleep or time.sleep
        self._window_rect_provider = window_rect_provider or _window_rect_from_point
        self._window_info_provider = window_info_provider or _window_info_from_point
        self._requests: queue.Queue = queue.Queue()
        self._closed = False
        self._worker = threading.Thread(
            target=self._worker_loop,
            name="codex-uia-locator",
            daemon=True,
        )
        self._worker.start()

    def _control_from_point(self, x: int, y: int):
        if self._inspector is not None:
            return self._inspector(x, y)
        import uiautomation as auto

        return auto.ControlFromPoint(x, y)

    def _thread_initializer(self):
        if self._initializer_factory is not None:
            return self._initializer_factory()
        import uiautomation as auto

        return auto.UIAutomationInitializerInThread()

    def _inspect_sync(self, x: int, y: int) -> ControlInfo | None:
        control = self._control_from_point(x, y)
        if control is None:
            return None
        info = _read_control(control, self._process_name_resolver)
        window_rect = self._window_rect_provider(x, y)
        return replace(info, top_level_rect=window_rect) if window_rect else info

    def _worker_loop(self) -> None:
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            pass
        try:
            with self._thread_initializer():
                while True:
                    task = self._requests.get()
                    if task is None:
                        return
                    x, y, future = task
                    try:
                        future.set_result(self._inspect_sync(x, y))
                    except Exception as exc:
                        future.set_exception(exc)
        except Exception:
            while True:
                try:
                    task = self._requests.get_nowait()
                except queue.Empty:
                    return
                if task is None:
                    return
                _, _, future = task
                future.set_result(None)

    def inspect_point(self, x: int, y: int, timeout: float = 1.5) -> ControlInfo | None:
        if self._closed or not self._worker.is_alive():
            return None
        future: Future = Future()
        self._requests.put((x, y, future))
        try:
            return future.result(timeout=timeout)
        except Exception:
            return None

    def win32_hit_test(self, x: int, y: int) -> bool:
        info = self._window_info_provider(x, y)
        if info is None:
            return False
        process_name, (left, top, right, bottom) = info
        if not is_codex_process(process_name):
            return False
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            return False
        x_ratio = (x - left) / width
        y_ratio = (y - top) / height
        return 0.15 <= x_ratio <= 0.95 and y_ratio >= 0.85

    def hit_test(self, x: int, y: int) -> bool:
        for attempt in range(3):
            info = self.inspect_point(x, y)
            if info is not None and is_codex_editable(info):
                return True
            if attempt < 2:
                self._retry_sleep(0.03)
        return False

    def diagnose_point(self, x: int, y: int) -> dict[str, Any]:
        info = self.inspect_point(x, y)
        if info is None:
            return {"hit": False, "info": None}
        return {
            "hit": is_codex_editable(info),
            "info": {
                "control_type": info.control_type,
                "name": info.name,
                "process_id": info.process_id,
                "process_name": info.process_name,
                "top_level_name": info.top_level_name,
                "rect": info.rect,
                "top_level_rect": info.top_level_rect,
            },
        }

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._requests.put(None)
        if threading.current_thread() is not self._worker:
            self._worker.join(timeout=2)

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
