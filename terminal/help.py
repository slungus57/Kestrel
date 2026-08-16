"""Terminal-only help screens."""

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from .styles import GREEN, TEXT, SECONDARY, DIM


def config_help(console: Console, config_path: str) -> None:
    sections = [
        ("enabled", "true/false. Starts Kestrel active when true. Default: false."),
        ("interval", "Seconds between completed action cycles. Example: 600 = 10 minutes."),
        ("randomization", "Seconds of random +/- jitter applied to each interval. 0 disables it."),
        ("actions", "Ordered list of key actions."),
        ("key", "A letter, digit, or supported special/function key."),
        ("duration", "Seconds that the individual key remains held."),
        ("target_window", "Optional substring matched against the focused Windows title. Use null to disable filtering."),
    ]
    lines = [
        ("CONFIGURATION GUIDE", "kestrel"),
        ("", ""),
        ("INTERVAL", "kestrel"),
        ("Time between cycles. This is not how long a key is held.", "text"),
        ("Examples: 600 = 10m, 300 = 5m, 60 = 1m.", "secondary"),
        ("", ""),
        ("DURATION", "kestrel"),
        ("How long each individual key is held.", "text"),
        ("Examples: 1.0 = 1 second, 0.1 = 100 milliseconds.", "secondary"),
        ("", ""),
        ("PROPERTIES", "kestrel"),
    ]
    for name, desc in sections:
        lines.append((f"{name:<15} {desc}", "text"))

    lines.extend([
        ("", ""),
        ("EXAMPLE", "kestrel"),
        ('{', "secondary"),
        ('    "enabled": false,', "secondary"),
        ('    "interval": 600,', "secondary"),
        ('    "randomization": 10,', "secondary"),
        ('    "actions": [', "secondary"),
        ('        {"key": "w", "duration": 1.0},', "secondary"),
        ('        {"key": "space", "duration": 0.2}', "secondary"),
        ('    ],', "secondary"),
        ('    "target_window": "Roblox"', "secondary"),
        ('}', "secondary"),
        ("", ""),
        ("SUPPORTED KEYS", "kestrel"),
        ("Letters a-z, digits 0-9, space, enter, escape, tab, shift, ctrl, alt,", "text"),
        ("backspace, delete, home, end, pageup, pagedown, arrows, and F1-F12.", "text"),
        ("", ""),
        ("CONFIG FILE", "kestrel"),
        (config_path, "secondary"),
        ("", ""),
        ("Press B or Esc to return.", "dimtext"),
    ])

    text = Text()
    for value, style in lines:
        text.append(value + "\n", style=style)
    console.clear()
    console.print(Panel(text, border_style=GREEN, padding=(1, 2), title="[kestrel]CONFIGURATION GUIDE[/kestrel]"))


def info_screen(console: Console, config_path: str) -> None:
    text = Text()
    rows = [
        ("Kestrel", "Keep your Roblox window awake"),
        ("", ""),
        ("S", "Start automation"),
        ("P", "Pause automation and release held keys"),
        ("X", "Stop automation"),
        ("R", "Reload config.json"),
        ("O", "Open config.json in the default editor"),
        ("I", "Open this configuration guide"),
        ("L", "Open the activity log"),
        ("Q", "Quit safely"),
        ("F8", "Global active/inactive toggle"),
        ("F9", "Global emergency stop"),
        ("", ""),
        ("INTERVAL", "Time between action cycles"),
        ("DURATION", "How long an individual key is held"),
        ("RANDOMIZATION", "Random +/- seconds around interval"),
        ("TARGET WINDOW", "Only automate when the configured window is focused"),
        ("", ""),
        ("B / ESC", "Return to dashboard"),
    ]
    for key, value in rows:
        if not key:
            text.append("\n")
        else:
            text.append(f"{key:<16}", style="kestrel")
            text.append(f"{value}\n", style="text")
    console.clear()
    console.print(Panel(text, border_style=GREEN, padding=(1, 2), title="[kestrel]INFO[/kestrel]"))


def activity_screen(console: Console, events: list[str]) -> None:
    console.clear()
    body = Text()
    body.append("ACTIVITY LOG\n\n", style="kestrel")
    if events:
        for event in events:
            body.append(event + "\n", style="text")
    else:
        body.append("No activity yet.\n", style="secondary")
    body.append("\nPress B or Esc to return.", style="dimtext")
    console.print(Panel(body, border_style=GREEN, padding=(1, 2), title="[kestrel]ACTIVITY[/kestrel]"))
