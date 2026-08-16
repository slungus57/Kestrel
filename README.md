# Kestrel

**Keep your Roblox window awake.**

[![Release](https://img.shields.io/badge/release-v1.0.0-0d8dcc)](https://github.com/slungus57/Kestrel/releases)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-blue?logo=windows&logoColor=white)](https://www.microsoft.com/windows/)
[![Target](https://img.shields.io/badge/Target-Sober%20%2F%20SDI2-blue)](https://github.com/slungus57/Kestrel)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

⚠️ *REMINDER!* This project is fully vibecoded and was inspired by this reddit post. [OG post here]
❔ *Compatibility* This project may work on Roblox revivals aswell, although it is not guaranteed.
(https://www.reddit.com/r/robloxhackers/comments/1vpxpxk/i_made_a_linux_tool_for_roblox_that_lets_you_afk/)

Kestrel is a terminal-only Windows utility that periodically performs configurable OS-level keyboard actions. It uses `pynput` for normal keyboard input and does not inject into Roblox, inspect Roblox memory, modify Roblox files, hook game internals, or manipulate network traffic.

## Requirements

- Windows 10/11
- Python 3.11 or newer
- A normal terminal such as Windows Terminal, PowerShell, or Command Prompt

## Installation

From the Kestrel project directory:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

Optional configuration path:

```powershell
python main.py --config path\to\config.json
```

Show the configuration guide without starting the dashboard:

```powershell
python main.py --config-help
```

## Configuration

Kestrel automatically creates `config.json` with safe defaults if it is missing.

Example:

```json
{
    "enabled": false,
    "interval": 600,
    "randomization": 10,
    "actions": [
        {
            "key": "w",
            "duration": 1.0
        },
        {
            "key": "s",
            "duration": 1.0
        },
        {
            "key": "space",
            "duration": 0.2
        }
    ],
    "target_window": "Roblox"
}
```

### `enabled`

Boolean. When `true`, Kestrel starts active after initialization. When `false`, it starts stopped.

### `interval`

Number of seconds between action cycles.

- `600` = every 10 minutes
- `300` = every 5 minutes
- `60` = every minute
- `10` = every 10 seconds

### `randomization`

Non-negative number of seconds. Each interval is randomly adjusted by approximately `±randomization`.

`0` disables randomization.

### `actions`

An ordered list. Every action has:

- `key`: a supported keyboard key
- `duration`: how long that key is held, in seconds

`interval` and `duration` are intentionally different:

> **INTERVAL = time between cycles**  
> **DURATION = how long an individual key is held**

### `target_window`

Optional text matched against the focused Windows window title. With:

```json
"target_window": "Roblox"
```

Kestrel only sends keyboard input when a foreground window title contains `Roblox`.

Use:

```json
"target_window": null
```

to disable window filtering.

## Supported keys

Letters `a-z`, digits `0-9`, plus:

- `space`
- `enter`
- `escape`
- `tab`
- `shift`
- `ctrl`
- `alt`
- `backspace`
- `delete`
- `home`
- `end`
- `pageup`
- `pagedown`
- `left`
- `right`
- `up`
- `down`
- `f1` through `f12`

## Controls

### Dashboard

- `S` — start
- `P` — pause
- `X` — stop
- `R` — reload configuration
- `I` — information
- `L` — activity log
- `O` — open `config.json`
- `Q` — quit

### Global hotkeys

- `F8` — toggle active/inactive
- `F9` — emergency stop and release held keys

## Configuration reload

Edit `config.json`, then press `R`.

Kestrel validates the actual file and replaces the active configuration when it is valid. Invalid configuration is reported in a readable error message and does not crash the program.

## Activity log

Recent activity is shown in the dashboard and detailed events are persisted to:

```text
kestrel.log
```

Examples include startup, configuration reloads, cycle starts/completions, errors, and shutdown.

## Safety and scope

Kestrel is an OS-level keyboard automation utility. It intentionally does not:

- inject code into Roblox
- read Roblox memory
- modify Roblox processes or files
- hook Roblox internals
- manipulate game network traffic
- bypass anti-cheat systems
- implement exploits
- alter game data

## Troubleshooting

### `pynput` cannot register global hotkeys

Windows security software or another application may interfere with global keyboard hooks. Kestrel logs the failure and the dashboard remains usable.

### Roblox window is never activated

Check the exact visible Roblox window title or set:

```json
"target_window": null
```

to disable filtering.

### A configuration change is rejected

Press `R` after correcting the specific field named by the error message.

### I pressed `Q`

Kestrel stops automation, releases held keys, stops keyboard listeners and worker threads, flushes the activity log, stops Rich rendering, clears the terminal, and exits cleanly.

## Optional executable packaging

Kestrel is a normal Python project. If you later want a Windows executable, a tool such as PyInstaller can be used, for example:

```powershell
pip install pyinstaller
pyinstaller --onefile --name Kestrel main.py
```

Test the Python version first before packaging so that terminal input, Rich rendering, and global hotkeys are known to work on the target system.
