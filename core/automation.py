"""Interruptible OS-level keyboard automation engine."""

from __future__ import annotations

from dataclasses import dataclass
import random
import threading
import time
from typing import Callable

from pynput import keyboard

from .config import Action, KestrelConfig
from .window_detection import target_window_is_focused


KEY_MAP = {
    "space": keyboard.Key.space,
    "enter": keyboard.Key.enter,
    "escape": keyboard.Key.esc,
    "esc": keyboard.Key.esc,
    "tab": keyboard.Key.tab,
    "shift": keyboard.Key.shift,
    "ctrl": keyboard.Key.ctrl,
    "control": keyboard.Key.ctrl,
    "alt": keyboard.Key.alt,
    "backspace": keyboard.Key.backspace,
    "delete": keyboard.Key.delete,
    "home": keyboard.Key.home,
    "end": keyboard.Key.end,
    "pageup": keyboard.Key.page_up,
    "pagedown": keyboard.Key.page_down,
    "left": keyboard.Key.left,
    "right": keyboard.Key.right,
    "up": keyboard.Key.up,
    "down": keyboard.Key.down,
    **{f"f{i}": getattr(keyboard.Key, f"f{i}") for i in range(1, 13)},
}


@dataclass(frozen=True)
class AutomationSnapshot:
    active: bool
    paused: bool
    current_action: str
    cycle: int
    next_cycle_at: float | None
    last_error: str | None


class AutomationEngine:
    def __init__(
        self,
        config_provider: Callable[[], KestrelConfig],
        log: Callable[[str], None],
        state_change: Callable[[], None],
    ) -> None:
        self._config_provider = config_provider
        self._log = log
        self._state_change = state_change

        self._controller = keyboard.Controller()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._run = threading.Event()
        self._run.set()
        self._lock = threading.RLock()

        self._held: set[object] = set()
        self._cycle = 0
        self._current_action = "Waiting..."
        self._next_cycle_at: float | None = None
        self._last_error: str | None = None
        self._active = False
        self._paused = False

    def start(self) -> None:
        with self._lock:
            self._paused = False
            self._active = True
            self._run.set()
            self._last_error = None
            self._next_cycle_at = time.monotonic()
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(
                    target=self._worker,
                    name="kestrel-automation",
                    daemon=True,
                )
                self._thread.start()
        self._state_change()

    def pause(self) -> None:
        with self._lock:
            self._paused = True
            self._active = False
            self._run.clear()
            self._next_cycle_at = None
            self._current_action = "Paused"
        self._release_all()
        self._state_change()

    def stop(self) -> None:
        with self._lock:
            self._paused = False
            self._active = False
            self._run.clear()
            self._next_cycle_at = None
            self._current_action = "Stopped"
        self._release_all()
        self._state_change()

    def toggle(self) -> bool:
        with self._lock:
            active = self._active
        if active:
            self.pause()
        else:
            self.start()
        return not active

    def emergency_stop(self) -> None:
        self._run.clear()
        with self._lock:
            self._active = False
            self._paused = False
            self._next_cycle_at = None
            self._current_action = "Emergency stopped"
        self._release_all()
        self._log("Emergency stop requested")
        self._state_change()

    def shutdown(self) -> None:
        self._stop.set()
        self._run.clear()
        self._release_all()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._thread = None
        with self._lock:
            self._active = False
            self._paused = False
            self._next_cycle_at = None
            self._current_action = "Stopped"

    def snapshot(self) -> AutomationSnapshot:
        with self._lock:
            return AutomationSnapshot(
                active=self._active,
                paused=self._paused,
                current_action=self._current_action,
                cycle=self._cycle,
                next_cycle_at=self._next_cycle_at,
                last_error=self._last_error,
            )

    def _resolve_key(self, name: str):
        if len(name) == 1:
            return keyboard.KeyCode.from_char(name)
        return KEY_MAP[name]

    def _interruptible_wait(self, seconds: float) -> bool:
        end = time.monotonic() + max(0.0, seconds)
        while not self._stop.is_set():
            remaining = end - time.monotonic()
            if remaining <= 0:
                return True
            if self._stop.wait(min(remaining, 0.1)):
                return False
            with self._lock:
                if not self._active:
                    return False
        return False

    def _press_action(self, action: Action) -> bool:
        config = self._config_provider()
        if config.target_window and not target_window_is_focused(config.target_window):
            with self._lock:
                self._current_action = "Waiting for Roblox window"
            self._state_change()
            return False

        key = self._resolve_key(action.key)
        with self._lock:
            self._current_action = f"Holding {action.key.upper()}..."
            self._held.add(key)
        self._controller.press(key)
        self._state_change()

        try:
            return self._interruptible_wait(action.duration)
        finally:
            try:
                self._controller.release(key)
            finally:
                with self._lock:
                    self._held.discard(key)
                    self._current_action = "Waiting..."
                self._state_change()

    def _release_all(self) -> None:
        with self._lock:
            held = list(self._held)
            self._held.clear()
        for key in held:
            try:
                self._controller.release(key)
            except Exception:
                pass

    def _worker(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                active = self._active
            if not active:
                self._stop.wait(0.1)
                continue

            config = self._config_provider()
            started = False
            try:
                # Start launches the first cycle immediately. Subsequent
                # cycles use the configured interval measured from completion.
                if self._execute_cycle(config):
                    started = True
                else:
                    # A target-window/focus check can temporarily block a cycle.
                    # Avoid a busy loop while remaining responsive to stop requests.
                    with self._lock:
                        active = self._active
                    if active:
                        self._stop.wait(0.25)
                    continue
            except Exception as exc:
                self._release_all()
                with self._lock:
                    self._last_error = str(exc)
                    self._current_action = "Error"
                    self._active = False
                    self._next_cycle_at = None
                self._log(f"Automation error: {exc}")
                self._state_change()
                continue

            if not started:
                continue

            config = self._config_provider()
            interval = max(0.01, config.interval)
            if config.randomization:
                jitter = random.uniform(-config.randomization, config.randomization)
                interval = max(0.01, interval + jitter)

            with self._lock:
                self._next_cycle_at = time.monotonic() + interval
                self._current_action = "Waiting..."
            self._state_change()

            while not self._stop.is_set():
                with self._lock:
                    active = self._active
                    next_at = self._next_cycle_at
                if not active or next_at is None:
                    break
                remaining = next_at - time.monotonic()
                if remaining <= 0:
                    break
                if self._stop.wait(min(remaining, 0.1)):
                    break

    def _execute_cycle(self, config: KestrelConfig) -> bool:
        with self._lock:
            if not self._active:
                return False

        if config.target_window and not target_window_is_focused(config.target_window):
            with self._lock:
                self._current_action = "Waiting for Roblox window"
            self._state_change()
            self._interruptible_wait(0.25)
            return False

        with self._lock:
            self._cycle += 1
            cycle = self._cycle
            self._current_action = "Starting cycle..."
        self._log(f"Cycle #{cycle:03d} started")
        self._state_change()

        for action in config.actions:
            with self._lock:
                if not self._active:
                    return False
            if not self._press_action(action):
                if self._stop.is_set():
                    return False
                with self._lock:
                    active = self._active
                if not active:
                    return False
                # Losing focus safely aborts the current cycle rather than
                # sending input into another application.
                return False

        self._log(f"Cycle #{cycle:03d} completed")
        with self._lock:
            self._current_action = "Waiting..."
        self._state_change()
        return True
