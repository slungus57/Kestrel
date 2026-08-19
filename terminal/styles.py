"""Shared Rich styles for the Kestrel terminal UI."""

from rich.console import Console
from rich.theme import Theme

GREEN = "#6FAF72"
BRIGHT_GREEN = "#91C995"
SOFT_GREEN = "#557F59"
TEXT = "#D9E2DA"
SECONDARY = "#9BA89D"
DIM = "#566158"
WARNING = "#C8A85B"
ERROR = "#C96A67"
SUCCESS = "#7FBC82"
BLACK = "#000000"

THEME = Theme({
    "kestrel": GREEN,
    "bright_kestrel": BRIGHT_GREEN,
    "soft_kestrel": SOFT_GREEN,
    "text": TEXT,
    "secondary": SECONDARY,
    "dimtext": DIM,
    "warning": WARNING,
    "error": ERROR,
    "success": SUCCESS,
})

CONSOLE = Console(theme=THEME, color_system="truecolor", highlight=False)

WORDMARK = r""" /$$   /$$                       /$$                         /$$
| $$  /$$/                      | $$                        | $$
| $$ /$$/   /$$$$$$   /$$$$$$$ /$$$$$$    /$$$$$$   /$$$$$$ | $$
| $$$$$/   /$$__  $$ /$$_____/|_  $$_/   /$$__  $$ /$$__  $$| $$
| $$  $$  | $$$$$$$$|  $$$$   | $$    | $$  \__/| $$$$$$$$| $$
| $$\  $$ | $$_____/ \____  $$  | $$ /$$| $$      | $$_____/| $$
| $$ \  $$|  $$$$$$$ /$$$$$$$/  |  $$$$/| $$      |  $$$$$$$| $$
|__/  \__/ \_______/|_______/    \___/  |__/       \_______/|__/"""
