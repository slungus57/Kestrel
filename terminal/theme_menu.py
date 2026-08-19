"""Terminal-only theme menu."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .themes import PRESETS, ThemeManager


def theme_screen(console, manager: ThemeManager, status: str | None = None) -> None:
    console.clear()

    table = Table.grid(padding=(0, 2), expand=True)
    table.add_column(style="kestrel", width=7, no_wrap=True)
    table.add_column(style="text")
    table.add_column(style="secondary", justify="right")

    table.add_row("1", PRESETS["1"][0], "default")
    table.add_row("2", PRESETS["2"][0], "")
    table.add_row("3", PRESETS["3"][0], "")
    table.add_row("4", PRESETS["4"][0], "")
    table.add_row("5", PRESETS["5"][0], "")
    table.add_row("6", PRESETS["6"][0], "")
    table.add_row("C", "Custom colors", "edit theme.json")
    table.add_row("R", "Reset to Natural Green", "")
    table.add_row("B", "Back", "")

    colors = Table.grid(padding=(0, 1))
    colors.add_column(style="secondary", width=12)
    colors.add_column(style="text")
    for key, label in [
        ("primary", "Primary"), ("bright", "Bright"), ("soft", "Soft"),
        ("text", "Text"), ("secondary", "Secondary"), ("dim", "Dim"),
        ("warning", "Warning"), ("error", "Error"), ("success", "Success"),
    ]:
        value = manager.palette[key]
        colors.add_row(label, Text(f"{value}", style="text"))

    body = Text()
    body.append("THEME MENU\n\n", style="kestrel")
    body.append("Current theme: ", style="secondary")
    body.append(manager.name + "\n\n", style="text")

    if status:
        body.append(status + "\n\n", style="success" if status.startswith("✓") else "error")

    console.print(Panel(body, border_style="kestrel", padding=(1, 2)))
    console.print(Panel(table, title="[kestrel]PRESETS & ACTIONS[/kestrel]", border_style="dimtext", padding=(0, 1)))
    console.print(Panel(colors, title="[kestrel]CURRENT COLORS[/kestrel]", border_style="dimtext", padding=(0, 1)))
    console.print("Theme changes apply immediately and are saved to theme.json.", style="secondary")
    console.print("Press [kestrel]B[/kestrel] or [kestrel]Esc[/kestrel] to return.", style="dimtext")
