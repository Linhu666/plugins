from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes

from .windows import enable_dpi_awareness


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    ctypes.c_size_t,
    ctypes.c_ssize_t,
)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint", wintypes.RECT),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", wintypes.BYTE * 32),
    ]


def color_ref(hex_color: str) -> int:
    value = hex_color.lstrip("#")
    red, green, blue = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    return red | (green << 8) | (blue << 16)


class OverlayWindow:
    WM_DESTROY = 0x0002
    WM_PAINT = 0x000F
    WM_TIMER = 0x0113
    WM_CLOSE = 0x0010
    WM_NCHITTEST = 0x0084
    WM_MOUSEACTIVATE = 0x0021
    WM_APP_SHOW = 0x8001
    WM_APP_HIDE = 0x8002
    TIMER_ID = 1
    WIDTH = 380
    HEIGHT = 72

    def __init__(self) -> None:
        self._thread = None
        self._ready = threading.Event()
        self._hwnd = None
        self._pending = ("", "", "#2F80ED", None)
        self._pending_lock = threading.Lock()
        self._wndproc = WNDPROC(self._window_proc)
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._class_name = f"CodexVoiceOverlay_{id(self)}"
        self._background_brush = None
        self._last_error = ""

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        enable_dpi_awareness()
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, name="codex-voice-overlay", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2)

    def show(self, title: str, subtitle: str, color: str, duration: float | None = None) -> None:
        with self._pending_lock:
            self._pending = (title, subtitle, color, duration)
        if self._hwnd:
            self._user32.PostMessageW(self._hwnd, self.WM_APP_SHOW, 0, 0)

    def hide(self) -> None:
        if self._hwnd:
            self._user32.PostMessageW(self._hwnd, self.WM_APP_HIDE, 0, 0)

    def stop(self) -> None:
        if self._hwnd:
            self._user32.PostMessageW(self._hwnd, self.WM_CLOSE, 0, 0)
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        try:
            user32 = self._user32
            gdi32 = self._gdi32
            kernel32 = self._kernel32
            user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
            user32.DefWindowProcW.restype = ctypes.c_ssize_t
            user32.CreateWindowExW.argtypes = [
                wintypes.DWORD,
                wintypes.LPCWSTR,
                wintypes.LPCWSTR,
                wintypes.DWORD,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.HWND,
                wintypes.HMENU,
                wintypes.HINSTANCE,
                wintypes.LPVOID,
            ]
            user32.CreateWindowExW.restype = wintypes.HWND
            user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
            user32.RegisterClassW.restype = wintypes.ATOM
            user32.SetWindowPos.argtypes = [
                wintypes.HWND,
                wintypes.HWND,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.UINT,
            ]
            user32.SetWindowPos.restype = wintypes.BOOL
            user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.ShowWindow.restype = wintypes.BOOL
            user32.InvalidateRect.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.BOOL]
            user32.UpdateWindow.argtypes = [wintypes.HWND]
            user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
            user32.BeginPaint.restype = wintypes.HDC
            user32.EndPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
            user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
            user32.DrawTextW.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.RECT), wintypes.UINT]
            user32.DrawTextW.restype = ctypes.c_int
            user32.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
            gdi32.CreateRoundRectRgn.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
            gdi32.CreateRoundRectRgn.restype = wintypes.HANDLE
            gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
            gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
            gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
            gdi32.SelectObject.restype = wintypes.HANDLE
            gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
            gdi32.RoundRect.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
            gdi32.Ellipse.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
            gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
            gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
            gdi32.CreateFontW.restype = wintypes.HANDLE
            gdi32.GetStockObject.restype = wintypes.HANDLE
            kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
            kernel32.GetModuleHandleW.restype = wintypes.HMODULE

            instance = kernel32.GetModuleHandleW(None)
            self._background_brush = gdi32.CreateSolidBrush(color_ref("#242832"))
            window_class = WNDCLASSW()
            window_class.lpfnWndProc = self._wndproc
            window_class.hInstance = instance
            window_class.hbrBackground = self._background_brush
            window_class.lpszClassName = self._class_name
            user32.RegisterClassW(ctypes.byref(window_class))
            ex_style = 0x08000000 | 0x00000008 | 0x00000020 | 0x00000080
            hwnd = user32.CreateWindowExW(
                ex_style,
                self._class_name,
                "Codex Voice",
                0x80000000,
                0,
                0,
                self.WIDTH,
                self.HEIGHT,
                None,
                None,
                instance,
                None,
            )
            if not hwnd:
                self._last_error = f"CreateWindowExW failed: {ctypes.get_last_error()}"
                return
            self._hwnd = hwnd
            region = gdi32.CreateRoundRectRgn(0, 0, self.WIDTH + 1, self.HEIGHT + 1, 18, 18)
            if region:
                user32.SetWindowRgn(hwnd, region, True)
            self._position_window()
            self._ready.set()
            message = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
        except Exception as exc:
            self._last_error = str(exc)
        finally:
            self._ready.set()
            self._hwnd = None

    def _position_window(self) -> None:
        rect = wintypes.RECT()
        if not self._user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            return
        x = rect.left + (rect.right - rect.left - self.WIDTH) // 2
        y = rect.bottom - self.HEIGHT - 24
        self._user32.SetWindowPos(
            self._hwnd,
            wintypes.HWND(-1),
            x,
            y,
            self.WIDTH,
            self.HEIGHT,
            0x0010 | 0x0020,
        )

    def _window_proc(self, hwnd, message, wparam, lparam):
        user32 = self._user32
        if message == self.WM_APP_SHOW:
            with self._pending_lock:
                title, subtitle, color, duration = self._pending
            if duration is None:
                user32.KillTimer(hwnd, self.TIMER_ID)
            else:
                user32.SetTimer(hwnd, self.TIMER_ID, max(100, int(duration * 1000)), None)
            user32.ShowWindow(hwnd, 4)
            user32.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
            user32.InvalidateRect(hwnd, None, True)
            user32.UpdateWindow(hwnd)
            return 0
        if message == self.WM_APP_HIDE or message == self.WM_TIMER:
            if message == self.WM_TIMER:
                user32.KillTimer(hwnd, self.TIMER_ID)
            user32.ShowWindow(hwnd, 0)
            return 0
        if message == self.WM_PAINT:
            try:
                self._paint(hwnd)
            except Exception as exc:
                self._last_error = str(exc)
            return 0
        if message == self.WM_NCHITTEST:
            return -1
        if message == self.WM_MOUSEACTIVATE:
            return 3
        if message == self.WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        if message == self.WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def _paint(self, hwnd) -> None:
        user32 = self._user32
        gdi32 = self._gdi32
        paint = PAINTSTRUCT()
        hdc = user32.BeginPaint(hwnd, ctypes.byref(paint))
        try:
            client = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(client))
            background = gdi32.CreateSolidBrush(color_ref("#242832"))
            gdi32.SelectObject(hdc, background)
            gdi32.SelectObject(hdc, gdi32.GetStockObject(8))
            gdi32.RoundRect(hdc, 0, 0, client.right, client.bottom, 20, 20)
            gdi32.DeleteObject(background)
            with self._pending_lock:
                title, subtitle, color, _ = self._pending
            indicator = gdi32.CreateSolidBrush(color_ref(color))
            gdi32.SelectObject(hdc, indicator)
            gdi32.Ellipse(hdc, 20, 28, 34, 42)
            gdi32.DeleteObject(indicator)
            gdi32.SetBkMode(hdc, 1)
            title_font = gdi32.CreateFontW(-18, 0, 0, 0, 600, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
            subtitle_font = gdi32.CreateFontW(-14, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
            gdi32.SetTextColor(hdc, color_ref("#FFFFFF"))
            gdi32.SelectObject(hdc, title_font)
            title_rect = wintypes.RECT(50, 8, client.right - 14, 36)
            user32.DrawTextW(hdc, title, -1, ctypes.byref(title_rect), 0x0004 | 0x0020)
            gdi32.SetTextColor(hdc, color_ref("#C5CAD5"))
            gdi32.SelectObject(hdc, subtitle_font)
            subtitle_rect = wintypes.RECT(50, 34, client.right - 14, 62)
            user32.DrawTextW(hdc, subtitle, -1, ctypes.byref(subtitle_rect), 0x0004 | 0x0020 | 0x8000)
            gdi32.DeleteObject(title_font)
            gdi32.DeleteObject(subtitle_font)
        finally:
            user32.EndPaint(hwnd, ctypes.byref(paint))


class OverlayPresenter:
    def __init__(self, overlay) -> None:
        self.overlay = overlay

    def notify(self, status: str, message: str) -> None:
        if status == "recording":
            self.overlay.show("正在听写", "松开鼠标结束", "#EB5757", None)
        elif status == "transcribing":
            self.overlay.show("正在本地转写", "请稍候", "#F2C94C", None)
        elif status == "pasted":
            self.overlay.show("已粘贴", message, "#27AE60", 1.2)
        elif status == "copied":
            self.overlay.show("已复制", "请手动粘贴", "#27AE60", 1.2)
        elif status == "empty":
            self.overlay.show("未识别到语音", message, "#828282", 1.2)
        elif status == "error":
            self.overlay.show("语音输入失败", message, "#C0392B", 2.0)
        else:
            self.overlay.hide()
