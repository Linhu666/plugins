from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from pathlib import PureWindowsPath
from typing import Callable, Protocol

from .codex_locator import _get_process_name, is_codex_process


class ClipboardBackend(Protocol):
    def get_text(self) -> str | None: ...
    def set_text(self, text: str) -> None: ...


class InputBackend(Protocol):
    def send_ctrl_v(self) -> None: ...


def encode_clipboard_utf16(text: str) -> bytes:
    return (text + "\0").encode("utf-16-le")


def decode_clipboard_utf16(raw: bytes) -> str:
    return raw.decode("utf-16-le").rstrip("\0")



def enable_dpi_awareness() -> bool:
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return True
    except Exception:
        pass
    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        return shcore.SetProcessDpiAwareness(2) == 0
    except Exception:
        return False


def get_foreground_process_name() -> str:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
    return _get_process_name(int(process_id.value))


def is_foreground_codex() -> bool:
    return is_codex_process(get_foreground_process_name())


class Win32Clipboard:
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    def __init__(self) -> None:
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user32.OpenClipboard.argtypes = [wintypes.HWND]
        self.user32.OpenClipboard.restype = wintypes.BOOL
        self.user32.CloseClipboard.restype = wintypes.BOOL
        self.user32.EmptyClipboard.restype = wintypes.BOOL
        self.user32.GetClipboardData.argtypes = [wintypes.UINT]
        self.user32.GetClipboardData.restype = wintypes.HANDLE
        self.user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        self.user32.SetClipboardData.restype = wintypes.HANDLE
        self.kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        self.kernel32.GlobalAlloc.restype = wintypes.HANDLE
        self.kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
        self.kernel32.GlobalLock.restype = wintypes.LPVOID
        self.kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
        self.kernel32.GlobalUnlock.restype = wintypes.BOOL
        self.kernel32.GlobalFree.argtypes = [wintypes.HANDLE]
        self.kernel32.GlobalFree.restype = wintypes.HANDLE

    def _open(self) -> None:
        for _ in range(10):
            if self.user32.OpenClipboard(None):
                return
            time.sleep(0.02)
        raise OSError("Unable to open Windows clipboard")

    def get_text(self) -> str | None:
        self._open()
        try:
            handle = self.user32.GetClipboardData(self.CF_UNICODETEXT)
            if not handle:
                return None
            pointer = self.kernel32.GlobalLock(handle)
            if not pointer:
                return None
            try:
                return ctypes.wstring_at(pointer)
            finally:
                self.kernel32.GlobalUnlock(handle)
        finally:
            self.user32.CloseClipboard()

    def set_text(self, text: str) -> None:
        raw = encode_clipboard_utf16(text)
        self._open()
        try:
            if not self.user32.EmptyClipboard():
                raise OSError("Unable to clear Windows clipboard")
            handle = self.kernel32.GlobalAlloc(self.GMEM_MOVEABLE, len(raw))
            if not handle:
                raise OSError("Unable to allocate clipboard memory")
            pointer = self.kernel32.GlobalLock(handle)
            if not pointer:
                self.kernel32.GlobalFree(handle)
                raise OSError("Unable to lock clipboard memory")
            try:
                ctypes.memmove(pointer, raw, len(raw))
            finally:
                self.kernel32.GlobalUnlock(handle)
            if not self.user32.SetClipboardData(self.CF_UNICODETEXT, handle):
                self.kernel32.GlobalFree(handle)
                raise OSError("Unable to set Windows clipboard data")
        finally:
            self.user32.CloseClipboard()


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]


class Win32Input:
    INPUT_KEYBOARD = 1
    VK_CONTROL = 0x11
    VK_V = 0x56
    KEYEVENTF_KEYUP = 0x0002

    def send_ctrl_v(self) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.SendInput.argtypes = [
            wintypes.UINT,
            ctypes.POINTER(INPUT),
            ctypes.c_int,
        ]
        user32.SendInput.restype = wintypes.UINT
        events = (INPUT * 4)()
        definitions = [
            (self.VK_CONTROL, 0),
            (self.VK_V, 0),
            (self.VK_V, self.KEYEVENTF_KEYUP),
            (self.VK_CONTROL, self.KEYEVENTF_KEYUP),
        ]
        for event, (virtual_key, flags) in zip(events, definitions):
            event.type = self.INPUT_KEYBOARD
            event.union.ki.wVk = virtual_key
            event.union.ki.wScan = 0
            event.union.ki.dwFlags = flags
            event.union.ki.time = 0
            event.union.ki.dwExtraInfo = 0
        sent = user32.SendInput(len(events), events, ctypes.sizeof(INPUT))
        if sent != len(events):
            raise OSError(ctypes.get_last_error(), "SendInput failed")


def paste_text(
    text: str,
    target_active: bool,
    clipboard: ClipboardBackend | None = None,
    input_backend: InputBackend | None = None,
    restore_clipboard: bool = True,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    clipboard = clipboard or Win32Clipboard()
    input_backend = input_backend or Win32Input()
    old_text = clipboard.get_text() if restore_clipboard else None
    clipboard.set_text(text)
    if not target_active:
        return False
    input_backend.send_ctrl_v()
    sleep(0.5)
    if restore_clipboard and old_text is not None:
        clipboard.set_text(old_text)
    return True
