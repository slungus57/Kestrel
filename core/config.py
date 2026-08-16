"""Configuration loading and validation for Kestrel."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


SUPPORTED_SPECIAL_KEYS = {
    "space": "space",
    "enter": "enter",
    "escape": "esc",
    "esc": "esc",
    "tab": "tab",
    "shift": "shift",
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "backspace": "backspace",
    "delete": "delete",
    "home": "home",
    "end": "end",
    "pageup": "page_up",
    "pagedown": "page_down",
    "left": "left",
    "right": "right",
    "up": "up",
    "down": "down",
    **{f"f{i}": f"f{i}" for i in range(1, 13)},
}


@dataclass(frozen=True)
class Action:
    key: str
    duration: float


@dataclass(frozen=True)
class KestrelConfig:
    enabled: bool
    interval: float
    randomization: float
    actions: tuple[Action, ...]
    target_window: str | None
    source_path: Path


class ConfigError(ValueError):
    """Raised when config.json is invalid."""


def default_config() -> dict[str, Any]:
    return {
        "enabled": False,
        "interval": 600,
        "randomization": 0,
        "actions": [
            {"key": "w", "duration": 1.0},
            {"key": "s", "duration": 1.0},
            {"key": "space", "duration": 0.2},
        ],
        "target_window": "Roblox",
    }


def _fail(message: str) -> None:
    raise ConfigError(message)


def validate_key(key: Any, index: int) -> str:
    if not isinstance(key, str):
        _fail(f'Invalid action #{index}: "key" must be a string.')
    key = key.strip().lower()
    if not key:
        _fail(f"Invalid action #{index}: key cannot be empty.")
    if len(key) == 1 and (key.isalpha() or key.isdigit()):
        return key
    if key in SUPPORTED_SPECIAL_KEYS:
        return key
    _fail(f'Invalid action #{index}: unknown key "{key}".')


def load_config(path: Path) -> tuple[KestrelConfig, bool]:
    created = False
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default_config(), indent=4) + "\n", encoding="utf-8")
        created = True

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(f"Invalid JSON in {path.name}: line {exc.lineno}, column {exc.colno}.")
    except OSError as exc:
        _fail(f"Unable to read {path}: {exc}")

    if not isinstance(raw, dict):
        _fail("Configuration root must be a JSON object.")

    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        _fail('Invalid "enabled": expected true or false.')

    interval = raw.get("interval")
    if not isinstance(interval, (int, float)) or isinstance(interval, bool):
        _fail('Invalid "interval": expected a positive number.')
    interval = float(interval)
    if interval <= 0:
        _fail('Invalid "interval": expected a positive number.')

    randomization = raw.get("randomization", 0)
    if not isinstance(randomization, (int, float)) or isinstance(randomization, bool):
        _fail('Invalid "randomization": expected a non-negative number.')
    randomization = float(randomization)
    if randomization < 0:
        _fail('Invalid "randomization": expected a non-negative number.')
    if randomization >= interval:
        # The exact interval is sampled as interval +/- randomization.
        # Keep the minimum strictly positive.
        randomization = min(randomization, max(0.0, interval - 0.01))

    actions_raw = raw.get("actions")
    if not isinstance(actions_raw, list) or not actions_raw:
        _fail('Invalid "actions": expected a non-empty array.')

    actions: list[Action] = []
    for idx, item in enumerate(actions_raw, start=1):
        if not isinstance(item, dict):
            _fail(f"Invalid action #{idx}: expected an object.")
        if "key" not in item:
            _fail(f'Invalid action #{idx}: missing "key".')
        if "duration" not in item:
            _fail(f'Invalid action #{idx}: missing "duration".')
        key = validate_key(item["key"], idx)
        duration = item["duration"]
        if not isinstance(duration, (int, float)) or isinstance(duration, bool):
            _fail(f'Invalid duration in action #{idx}: expected a positive number.')
        duration = float(duration)
        if duration <= 0:
            _fail(f"Invalid duration in action #{idx}: expected a positive number.")
        actions.append(Action(key=key, duration=duration))

    target_window = raw.get("target_window")
    if target_window is not None and not isinstance(target_window, str):
        _fail('Invalid "target_window": expected a string or null.')
    if isinstance(target_window, str):
        target_window = target_window.strip() or None

    return KestrelConfig(
        enabled=enabled,
        interval=interval,
        randomization=randomization,
        actions=tuple(actions),
        target_window=target_window,
        source_path=path,
    ), created
