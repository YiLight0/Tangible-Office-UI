# OpenClaw Toio Crayfish Skill Project

Event-driven toio control project that simulates an "office crayfish" behavior model.

## Features

- State machine with 7 states: `stopped`, `idle`, `writing`, `researching`, `executing`, `syncing`, `error`
- Two state control channels:
  - Keyboard: `0-6` during runtime
  - External command: `python set_state.py <state> "<desc>"`
- Position-based behavior on fixed anchors
- Periodic state signature sounds (every 5 seconds)
- Robust startup/exit safety (motor and sound stop)

## Project Structure

```text
.
├── app.py                  # Runtime entrypoint
├── set_state.py            # Compatibility CLI entrypoint
├── scripts/
│   └── set_state.py        # External state command writer
├── toio_app/
│   ├── __init__.py
│   ├── behavior.py         # State machine and action primitives
│   ├── compat.py           # bleak/toio compatibility patch
│   ├── config.py           # Anchors, probabilities, constants
│   ├── connection.py       # Scan/connect with retry
│   ├── pose.py             # Pose extraction and notifications
│   ├── runner.py           # Orchestration and command listening
│   └── state.py            # Shared pose state
├── SKILL.md
├── LICENSE
├── .gitignore
├── requirements.txt
└── pyproject.toml
```

## Quick Start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the app:

```bash
python app.py
```

3. Switch state from another terminal:

```bash
python set_state.py 3 "start researching"
python set_state.py error "panic mode"
python set_state.py 0 "stop"
```

## Keyboard Mapping

- `0`: stopped
- `1`: idle
- `2`: writing
- `3`: researching
- `4`: executing
- `5`: syncing
- `6`: error
- `ESC`: quit

## Notes

- This project targets Python 3.10+.
- Ensure Bluetooth is enabled and the cube is on a readable mat/code sheet.
