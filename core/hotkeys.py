"""Global F8/F9 hotkeys with clean listener lifecycle."""

from __future__ import annotations

from typing import Callable

from pynput import keyboard


class HotkeyManager:
    def __init__(
        self,
        toggle_callback: Callable[[], None],
        emergency_callback: Callable[[], None],
        error_callback: Callable[[str], None],
    ) -> None:
        self._toggle_callback = toggle_callback
        self._emergency_callback = emergency_callback
        self._error_callback = error_callback
        self._listener: keyboard.GlobalHotKeys | None = None

    def start(self) -> None:
        if self._listener is not None:
            return
        try:
            self._listener = keyboard.GlobalHotKeys({
                "<f8>": self._toggle_callback,
                "<f9>": self._emergency_callback,
            })
            self._listener.start()
        except Exception as exc:
            self._listener = None
            self._error_callback(f"Global hotkeys unavailable: {exc}")

    def stop(self) -> None:
        listener = self._listener
        self._listener = None
        if listener is not None:
            try:
                listener.stop()
                listener.join(timeout=1.5)
            except Exception:
                pass
