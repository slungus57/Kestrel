"""Kestrel theme persistence, presets, and runtime color application."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from copy import deepcopy

from rich.theme import Theme

from .styles import CONSOLE


DEFAULT_THEME = {
    "primary": "#6FAF72",
    "bright": "#91C995",
    "soft": "#557F59",
    "text": "#D9E2DA",
    "secondary": "#9BA89D",
    "dim": "#566158",
    "warning": "#C8A85B",
    "error": "#C96A67",
    "success": "#7FBC82",
}

PRESETS = {
    "1": ("Natural Green", DEFAULT_THEME),
    "2": ("Forest", {
        "primary": "#4F8A5B", "bright": "#84BC8C", "soft": "#3D6845",
        "text": "#DCE7DE", "secondary": "#9CAD9E", "dim": "#58665A",
        "warning": "#C5A45E", "error": "#BE6866", "success": "#73B67C",
    }),
    "3": ("Ocean Blue", {
        "primary": "#5C91B8", "bright": "#8DB8D5", "soft": "#456F8D",
        "text": "#DBE5EC", "secondary": "#9BAAB5", "dim": "#58656D",
        "warning": "#C7A85D", "error": "#C76E6A", "success": "#78B58F",
    }),
    "4": ("Warm Amber", {
        "primary": "#B18A4E", "bright": "#D0B67B", "soft": "#806536",
        "text": "#E8E1D5", "secondary": "#AEA69A", "dim": "#69645B",
        "warning": "#D0A453", "error": "#C86B65", "success": "#8EB07D",
    }),
    "5": ("Rosewood", {
        "primary": "#A56A72", "bright": "#CF969E", "soft": "#744C52",
        "text": "#E8DDDF", "secondary": "#B0A1A4", "dim": "#6B5E61",
        "warning": "#C4A35D", "error": "#C96969", "success": "#7CB18A",
    }),
    "6": ("Monochrome", {
        "primary": "#B8B8B8", "bright": "#F0F0F0", "soft": "#777777",
        "text": "#E4E4E4", "secondary": "#AAAAAA", "dim": "#666666",
        "warning": "#C0C0C0", "error": "#D0D0D0", "success": "#C8C8C8",
    }),
}


class ThemeError(ValueError):
    """Raised for invalid theme data."""


class ThemeManager:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.palette = deepcopy(DEFAULT_THEME)
        self.name = "Natural Green"
        self._overlay_active = False

    @staticmethod
    def _validate_hex(value: object, name: str) -> str:
        if not isinstance(value, str) or not value.startswith("#") or len(value) != 7:
            raise ThemeError(f'Invalid "{name}": expected a #RRGGBB color.')
        try:
            int(value[1:], 16)
        except ValueError as exc:
            raise ThemeError(f'Invalid "{name}": expected a #RRGGBB color.') from exc
        return value.upper()

    @classmethod
    def validate_palette(cls, data: object) -> dict[str, str]:
        if not isinstance(data, dict):
            raise ThemeError("Theme must be a JSON object.")
        result = {}
        for key in DEFAULT_THEME:
            if key not in data:
                raise ThemeError(f'Missing theme color "{key}".')
            result[key] = cls._validate_hex(data[key], key)
        return result

    def load(self) -> tuple[bool, str | None]:
        if not self.path.exists():
            self.save(self.palette, self.name)
            self.apply(self.palette, persist=False, name=self.name)
            return True, None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ThemeError("theme.json root must be an object.")
            name = raw.get("name", "Custom")
            palette = raw.get("colors")
            palette = self.validate_palette(palette)
            self.apply(palette, persist=False, name=str(name))
            return True, None
        except (OSError, json.JSONDecodeError, ThemeError) as exc:
            return False, str(exc)

    def save(self, palette: dict[str, str], name: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"name": name, "colors": palette}
        self.path.write_text(json.dumps(payload, indent=4) + "\n", encoding="utf-8")

    def apply(self, palette: dict[str, str], *, persist: bool = True, name: str = "Custom") -> None:
        validated = self.validate_palette(palette)
        if self._overlay_active:
            CONSOLE.pop_theme()
        CONSOLE.push_theme(Theme({
            "kestrel": validated["primary"],
            "bright_kestrel": validated["bright"],
            "soft_kestrel": validated["soft"],
            "text": validated["text"],
            "secondary": validated["secondary"],
            "dimtext": validated["dim"],
            "warning": validated["warning"],
            "error": validated["error"],
            "success": validated["success"],
        }))
        self._overlay_active = True
        self.palette = validated
        self.name = name
        if persist:
            self.save(validated, name)

    def use_preset(self, key: str) -> str:
        if key not in PRESETS:
            raise ThemeError(f"Unknown theme preset: {key}")
        name, palette = PRESETS[key]
        self.apply(palette, name=name)
        return name

    def reset(self) -> str:
        self.apply(DEFAULT_THEME, name="Natural Green")
        return self.name

    def open_custom_editor(self) -> tuple[bool, str | None]:
        try:
            if not self.path.exists():
                self.save(self.palette, self.name)
            result = subprocess.run(["notepad.exe", str(self.path)], check=False)
            if result.returncode not in (0, None):
                return False, f"Theme editor exited with code {result.returncode}."
            return self.load()
        except Exception as exc:
            return False, str(exc)
