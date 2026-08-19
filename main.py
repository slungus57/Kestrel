from __future__ import annotations

import argparse
from collections import deque
import json
import msvcrt
from pathlib import Path
import subprocess
import sys
import threading
import time
from datetime import datetime

from rich.live import Live
from rich.panel import Panel
from rich.console import Console
from rich.text import Text

from core.automation import AutomationEngine
from core.config import ConfigError, KestrelConfig, load_config
from core.hotkeys import HotkeyManager
from terminal.dashboard import Dashboard
from terminal.help import activity_screen, config_help, info_screen
from terminal.theme_menu import theme_screen
from terminal.styles import CONSOLE, ERROR
from terminal.themes import PRESETS, ThemeManager, ThemeError

PRESET_KEYS = set(PRESETS.keys())


class KestrelApp:
    def __init__(self, config_path: Path):
        self.console = CONSOLE
        self.config_path = config_path.resolve()
        self.config: KestrelConfig | None = None
        self.theme_manager = ThemeManager(self.config_path.parent / "theme.json")
        self._theme_status: str | None = None
        self.recent_events: deque[str] = deque(maxlen=100)
        self._events_lock = threading.RLock()
        self._state_lock = threading.RLock()
        self._running = True
        self._view = "dashboard"
        self._view_request = None
        self._reload_error: str | None = None
        self._input_thread: threading.Thread | None = None
        self._input_stop = threading.Event()

        self.automation = AutomationEngine(
            config_provider=self.get_config,
            log=self.log_event,
            state_change=self.request_refresh,
        )
        self.hotkeys = HotkeyManager(
            toggle_callback=self._hotkey_toggle,
            emergency_callback=self._hotkey_emergency,
            error_callback=self._hotkey_error,
        )
        self.dashboard = Dashboard(self)
        theme_ok, theme_error = self.theme_manager.load()
        if not theme_ok:
            self._theme_status = f"✗ Theme load failed: {theme_error}"

    def get_config(self) -> KestrelConfig:
        with self._state_lock:
            if self.config is None:
                raise RuntimeError("Configuration is not loaded.")
            return self.config

    def request_refresh(self):
        # Live rendering polls state; this hook is retained for future
        # event-driven refresh and makes state-change intent explicit.
        pass

    def log_event(self, message: str) -> None:
        line = f"{datetime.now():%H:%M:%S}  {message}"
        with self._events_lock:
            self.recent_events.append(line)
        try:
            with (self.config_path.parent / "kestrel.log").open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass

    def _hotkey_toggle(self):
        if self._running:
            self.automation.toggle()
            self.log_event("F8 toggled automation")

    def _hotkey_emergency(self):
        if self._running:
            self.automation.emergency_stop()

    def _hotkey_error(self, message: str):
        self.log_event(message)

    def load_initial_config(self):
        try:
            config, created = load_config(self.config_path)
            with self._state_lock:
                self.config = config
            if created:
                self.log_event(f"Created default configuration: {self.config_path.name}")
            else:
                self.log_event("Configuration loaded")
            return True
        except ConfigError as exc:
            self._reload_error = str(exc)
            self.log_event(f"Configuration error: {exc}")
            return False

    def reload_config(self):
        try:
            config, created = load_config(self.config_path)
            previous = self.config
            with self._state_lock:
                self.config = config
            self._reload_error = None
            self.log_event(
                "Configuration reloaded" if not created else "Configuration recreated and loaded"
            )
            # Reloading does not silently start automation. It does update the
            # active worker's provider for the next action/interval.
            if previous and previous.enabled and not config.enabled:
                self.automation.stop()
            return True
        except ConfigError as exc:
            self._reload_error = str(exc)
            self.log_event(f"Configuration reload failed: {exc}")
            return False

    def open_config(self):
        try:
            subprocess.Popen(["notepad.exe", str(self.config_path)])
            self.log_event("Opened config.json")
        except Exception as exc:
            self.log_event(f"Unable to open config.json: {exc}")

    def start(self):
        self.automation.start()
        self.log_event("Automation started")

    def pause(self):
        self.automation.pause()
        self.log_event("Automation paused")

    def stop(self):
        self.automation.stop()
        self.log_event("Automation stopped")

    def show_help(self):
        self._view = "help"

    def show_info(self):
        self._view = "info"

    def show_log(self):
        self._view = "log"

    def show_theme(self):
        self._theme_status = None
        self._view = "theme"

    def show_dashboard(self):
        self._view = "dashboard"

    def quit(self):
        self._running = False

    def _read_input_char(self):
        if not msvcrt.kbhit():
            return None
        try:
            char = msvcrt.getwch()
        except Exception:
            return None
        if char in ("\x00", "\xe0"):
            # Consume the second scan-code character for arrows/F-keys so the
            # terminal input loop doesn't interpret it as a command.
            if msvcrt.kbhit():
                msvcrt.getwch()
            return None
        return char

    def _input_loop(self):
        while not self._input_stop.is_set():
            char = self._read_input_char()
            if char is None:
                time.sleep(0.03)
                continue
            key = char.lower()
            if self._view.startswith("theme-static"):
                if key == "q":
                    self.quit()
                else:
                    self._handle_theme_key(key, char)
                continue
            if key == "s":
                self.start()
            elif key == "p":
                self.pause()
            elif key == "x":
                self.stop()
            elif key == "r":
                self.reload_config()
            elif key == "i":
                self.show_info()
            elif key == "l":
                self.show_log()
            elif key == "o":
                self.open_config()
            elif key == "t":
                self.show_theme()
            elif key == "q":
                self.quit()
            elif key == "b" or char == "\x1b":
                self.show_dashboard()

    def _handle_theme_key(self, key: str, raw_char: str) -> None:
        if key in PRESET_KEYS:
            try:
                name = self.theme_manager.use_preset(key)
                self._theme_status = f"✓ Applied {name}"
                self.log_event(f"Theme changed to {name}")
            except ThemeError as exc:
                self._theme_status = f"✗ {exc}"
            self._view = "theme"
            return
        if key == "r":
            name = self.theme_manager.reset()
            self._theme_status = f"✓ Reset to {name}"
            self.log_event(f"Theme reset to {name}")
            self._view = "theme"
            return
        if key == "c":
            ok, message = self.theme_manager.open_custom_editor()
            if ok:
                self._theme_status = f"✓ Loaded {self.theme_manager.name}"
                self.log_event(f"Custom theme loaded: {self.theme_manager.name}")
            else:
                self._theme_status = f"✗ Theme reload failed: {message}"
                self.log_event(f"Theme reload failed: {message}")
            self._view = "theme"
            return
        if key == "b" or raw_char == "\x1b":
            self._theme_status = None
            self.show_dashboard()

    def start_input(self):
        self._input_thread = threading.Thread(
            target=self._input_loop, name="kestrel-terminal-input", daemon=True
        )
        self._input_thread.start()

    def stop_input(self):
        self._input_stop.set()
        thread = self._input_thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)

    def render_view(self):
        if self._view == "help":
            config_help(self.console, str(self.config_path))
            self._view = "help-static"
            return None
        if self._view == "info":
            info_screen(self.console, str(self.config_path))
            self._view = "info-static"
            return None
        if self._view == "log":
            with self._events_lock:
                events = list(self.recent_events)
            activity_screen(self.console, events)
            self._view = "log-static"
            return None
        if self._view.endswith("-static"):
            return None
        return self.dashboard.render()

    def handle_return_from_static_view(self):
        if self._view.endswith("-static"):
            self._view = "dashboard"

    def run(self):
        self.dashboard.render_startup()
        self.log_event("Kestrel started")

        if not self.load_initial_config():
            self.console.print(
                Panel(
                    self._reload_error or "Unable to load configuration.",
                    title="[error]CONFIGURATION ERROR[/error]",
                    border_style=ERROR,
                )
            )
            self.console.print("Press Q to quit, or R after fixing config.json.", style="secondary")
        self.hotkeys.start()
        self.start_input()

        # Enabled=true means Kestrel starts active intentionally.
        if self.config and self.config.enabled:
            self.start()

        live = Live(self.dashboard.render(), console=self.console, refresh_per_second=8, transient=False)
        live_started = False
        try:
            live.start()
            live_started = True
            while self._running:
                if self._view == "dashboard":
                    live.update(self.dashboard.render(), refresh=True)
                    time.sleep(0.08)
                    continue

                if live_started:
                    live.stop()
                    live_started = False

                if self._view == "theme":
                    theme_screen(self.console, self.theme_manager, self._theme_status)
                    self._view = "theme-static"
                elif self._view == "info":
                    info_screen(self.console, str(self.config_path))
                    self._view = "info-static"
                elif self._view == "help":
                    config_help(self.console, str(self.config_path))
                    self._view = "help-static"
                elif self._view == "log":
                    with self._events_lock:
                        events = list(self.recent_events)
                    activity_screen(self.console, events)
                    self._view = "log-static"

                # The input thread remains active while the static screen is
                # displayed. B/Esc switches back to the dashboard.
                while self._running and self._view.endswith("-static"):
                    time.sleep(0.05)

                if self._running and not live_started:
                    live = Live(self.dashboard.render(), console=self.console, refresh_per_second=8, transient=False)
                    live.start()
                    live_started = True

        except KeyboardInterrupt:
            self._running = False
        finally:
            try:
                if live_started:
                    live.stop()
            finally:
                self.shutdown()

    def shutdown(self):
        self._running = False
        self.stop_input()
        self.automation.shutdown()
        self.hotkeys.stop()
        self.log_event("Kestrel shut down")
        self.console.clear()
        shutdown_title = Text("KESTREL", style="kestrel")
        shutdown_title.stylize("bold")
        self.console.print(shutdown_title)
        self.console.print("Clean shutdown complete.", style="success")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Kestrel — Keep your Roblox window awake."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.json"),
        help="Path to the JSON configuration file.",
    )
    parser.add_argument(
        "--config-help",
        action="store_true",
        help="Display the terminal-only configuration guide and exit.",
    )
    return parser.parse_args()


def main():
    if sys.platform != "win32":
        print("Kestrel prioritizes Windows because terminal input and optional window detection use Windows APIs.")
        raise SystemExit(2)

    args = parse_args()
    if args.config_help:
        config_help(CONSOLE, str(args.config.resolve()))
        return

    app = KestrelApp(args.config)
    app.run()


if __name__ == "__main__":
    main()
