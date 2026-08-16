"""Windows foreground-window detection without touching Roblox internals."""

from __future__ import annotations

import ctypes
from ctypes import wintypes


_user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None


def get_foreground_window_title() -> str:
    if _user32 is None:
        return ""
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = _user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def target_window_is_focused(target: str | None) -> bool:
    if not target:
        return True
    title = get_foreground_window_title()
    return target.casefold() in title.casefold()
