"""Rich live dashboard for Kestrel."""

from __future__ import annotations

from datetime import datetime
import time

from rich.align import Align
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .styles import (
    BLACK,
    BRIGHT_GREEN,
    CONSOLE,
    DIM,
    GREEN,
    SECONDARY,
    SUCCESS,
    TEXT,
    WARNING,
    ERROR,
)


def format_seconds(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_countdown(seconds: float | None) -> str:
    if seconds is None:
        return "--:--"
    seconds = max(0, int(seconds + 0.999))
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def format_interval(seconds: float) -> str:
    if seconds >= 3600 and seconds % 3600 == 0:
        return f"Every {int(seconds / 3600)}h"
    if seconds >= 60:
        mins = seconds / 60
        if mins.is_integer():
            return f"Every {int(mins)}m"
        return f"Every {mins:.1f}m"
    return f"Every {seconds:.1f}s"


def action_sequence(config) -> str:
    return " → ".join(a.key.upper() if a.key != "space" else "SPACE" for a in config.actions)


def make_section(title: str, body: RenderableType, *, height: int | None = None):
    return Panel(
        body,
        title=f"[kestrel]{title}[/kestrel]",
        border_style=SOFT_BORDER(title),
        padding=(0, 1),
        height=height,
    )


def SOFT_BORDER(_title: str) -> str:
    return GREEN


def kv_table(rows: list[tuple[str, str]], value_style: str = "text") -> Table:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dimtext", no_wrap=True)
    table.add_column(style=value_style, overflow="ellipsis")
    for label, value in rows:
        table.add_row(label, value)
    return table


def status_text(active: bool, paused: bool, waiting: bool) -> tuple[str, str]:
    if paused:
        return "● PAUSED", "warning"
    if active and waiting:
        return "● WAITING FOR ROBLOX WINDOW", "warning"
    if active:
        return "● ACTIVE", "success"
    return "● STOPPED", "dimtext"


class Dashboard:
    def __init__(self, app) -> None:
        self.app = app
        self.started_monotonic = time.monotonic()
        self.last_update = time.monotonic()

    def render(self) -> Layout:
        config = self.app.config
        snap = self.app.automation.snapshot()
        now = time.monotonic()
        uptime = now - self.started_monotonic

        waiting = "Waiting for Roblox window" in snap.current_action
        status, status_style = status_text(snap.active, snap.paused, waiting)

        header = Table.grid(expand=True)
        header.add_column()
        header.add_column(justify="right")
        title = Text("KESTREL", style="kestrel bold")
        subtitle = Text("Keep your Roblox window awake", style="secondary")
        header.add_row(title, Text.from_markup(f"[{status_style}]{status}[/{status_style}]"))
        header.add_row(subtitle, Text(f"Cycle #{snap.cycle:03d}", style="dimtext"))

        config_body = kv_table([
            ("Mode", "Keyboard Automation"),
            ("Actions", action_sequence(config)),
            ("Interval", format_interval(config.interval)),
            ("Random", f"±{config.randomization:.1f}s" if config.randomization else "±0s"),
            ("Enabled", "Yes" if config.enabled else "No"),
            ("Target", config.target_window or "Any window"),
        ])

        activity_body = kv_table([
            ("Status", status),
            ("Cycle", f"#{snap.cycle:03d}"),
            ("Current", snap.current_action),
            ("Next", datetime.fromtimestamp(
                time.time() + max(0, snap.next_cycle_at - now)
            ).strftime("%I:%M %p").lstrip("0") if snap.next_cycle_at is not None else "--"),
            ("Uptime", format_seconds(uptime)),
        ])

        remaining = None
        total = config.interval
        if snap.next_cycle_at is not None and snap.active:
            remaining = max(0.0, snap.next_cycle_at - now)
        ratio = 0.0 if remaining is None else max(0.0, min(1.0, remaining / max(total, 0.01)))
        bar_width = 34
        filled = int(bar_width * (1 - ratio))
        bar = Text("━" * filled, style="kestrel") + Text("━" * (bar_width - filled), style="dimtext")
        countdown = format_countdown(remaining)

        countdown_group = Group(
            Align.center(Text(countdown, style="bright_kestrel bold", justify="center")),
            Align.center(bar),
            Align.center(
                Text(
                    f"Next cycle in {format_seconds(remaining) if remaining is not None else 'not scheduled'}",
                    style="secondary",
                    justify="center",
                )
            ),
        )

        recent = list(self.app.recent_events)[-5:]
        log_table = Table.grid(expand=True, padding=(0, 1))
        log_table.add_column(style="dimtext", no_wrap=True, width=8)
        log_table.add_column(style="text", overflow="ellipsis")
        for event in recent:
            try:
                timestamp, message = event.split("  ", 1)
            except ValueError:
                timestamp, message = "", event
            log_table.add_row(timestamp, message)
        if not recent:
            log_table.add_row("--:--:--", "No activity yet.")

        controls = Text()
        for key, label in [
            ("S", "Start"), ("P", "Pause"), ("X", "Stop"), ("R", "Reload"),
            ("I", "Info"), ("L", "Log"), ("O", "Config"), ("Q", "Quit"),
        ]:
            controls.append(f"[{key}]", style="kestrel bold")
            controls.append(f" {label}  ", style="secondary")

        top = Layout(name="top", size=8)
        top.split_row(
            Layout(Panel(header, border_style=DIM, padding=(0, 1)), ratio=1),
            Layout(Panel(activity_body, title="[kestrel]CURRENT ACTIVITY[/kestrel]", border_style=GREEN, padding=(0, 1)), ratio=1),
        )

        middle = Layout(name="middle", minimum_size=10)
        middle.split_row(
            Layout(Panel(config_body, title="[kestrel]CONFIGURATION[/kestrel]", border_style=GREEN, padding=(0, 1)), ratio=1),
            Layout(Panel(countdown_group, title="[kestrel]NEXT CYCLE[/kestrel]", border_style=GREEN, padding=(0, 1)), ratio=1),
        )

        bottom = Layout(name="bottom", size=9)
        bottom.split_column(
            Layout(Panel(log_table, title="[kestrel]ACTIVITY[/kestrel]", border_style=GREEN, padding=(0, 1)), ratio=1),
            Layout(Panel(Align.center(controls), title="[kestrel]CONTROLS[/kestrel]", border_style=DIM, padding=(0, 0), height=3)),
        )

        root = Layout()
        root.split_column(top, middle, bottom)
        return root

    def render_startup(self):
        from .styles import WORDMARK
        console = CONSOLE
        console.clear()
        console.print("")
        console.print(Align.center(Text(WORDMARK, style="kestrel")))
        console.print(Align.center(Text("Keep your Roblox window awake", style="text")))
        console.print(Align.center(Text("────────────────────────────────────────────", style="dimtext")))
        console.print("")
        console.print(Align.center(Text("Initializing...", style="secondary")))
        console.print(Align.center(Text("✓ Configuration loaded", style="success")))
        console.print(Align.center(Text("✓ Keyboard automation ready", style="success")))
        console.print(Align.center(Text("✓ Hotkeys registered", style="success")))
        console.print("")
        console.print(Align.center(Text("Starting dashboard...", style="secondary")))
        time.sleep(0.7)
        console.clear()
