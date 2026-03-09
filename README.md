# OpenClaw Toio Crayfish Controller

Language: **English** | [中文](README.zh-CN.md) | [日本語](README.ja.md)

Event-driven controller for toio cube that simulates an "office crayfish" role with fixed-map anchors, interruptible state switching, and periodic state sounds.

## 1. What This Project Does

- Runs a behavior state machine for one toio cube.
- Uses fixed map zones and anchor points (rest/work/bug areas).
- Supports two control channels:
  - Keyboard (`0-6`, `ESC`)
  - External command (`python set_state.py <state> "<desc>"`)
- Plays per-state sound signatures every 5 seconds while active.
- Enforces safe startup/exit:
  - Startup is still (`stopped`) until a state command arrives.
  - Exit always stops motor and sound.

## 2. State Model

- `stopped`: freeze mode, motor/sound off
- `idle`: rest-area behavior
- `writing`: writing-area behavior
- `researching`: research-area roaming
- `executing`: deterministic loop on E anchors
- `syncing`: back-and-forth sync path on S anchors
- `error`: panic-like bug-area behavior

State switching is preemptive: a new state interrupts current action, then runs entry behavior of the new state.

## 3. Runtime Control

### Keyboard

- `0`: stopped
- `1`: idle
- `2`: writing
- `3`: researching
- `4`: executing
- `5`: syncing
- `6`: error
- `ESC`: quit

### External command

From another terminal while runtime is active:

```bash
python set_state.py 3 "start researching"
python set_state.py error "panic mode"
python set_state.py 0 "manual stop"
```

Accepted state inputs:

- Numeric: `0..6`
- Text: `stopped|idle|writing|researching|executing|syncing|error`

## 4. Project Structure

```text
.
├── main.py                  # Primary runtime entrypoint (recommended)
├── app.py                   # Compatibility entrypoint forwarding to main.py
├── set_state.py             # Compatibility CLI entrypoint forwarding to scripts/set_state.py
├── scripts/
│   ├── __init__.py
│   └── set_state.py         # External state command writer
├── toio_app/
│   ├── __init__.py
│   ├── behavior.py          # State machine and motion primitives
│   ├── compat.py            # bleak/toio compatibility shim
│   ├── config.py            # Anchors, probabilities, state configs, sound configs
│   ├── connection.py        # BLE scan/connect with retries
│   ├── pose.py              # Position parsing and notifications
│   ├── runner.py            # Orchestration and command listeners
│   └── state.py             # Shared pose state
├── SKILL.md
├── LICENSE
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

## 5. Setup

### Requirements

- Python 3.10+
- BLE-capable host with Bluetooth enabled
- toio cube on readable toio mat/code sheet for position-based behaviors

### Install

```bash
pip install -r requirements.txt
```

## 6. Run

Recommended:

```bash
python main.py
```

Compatibility:

```bash
python app.py
```

## 7. Configuration and Tuning

Main tuning file: `toio_app/config.py`

You can adjust:

- Anchor coordinates and map regions
- State action pools and random event weights
- Random event trigger gates per state
- Sound sequences and playback interval
- Motion timing and thresholds

## 8. Development Notes

- Keep behavior logic in `toio_app/behavior.py`.
- Keep orchestration/input/watchers in `toio_app/runner.py`.
- Keep BLE connection logic in `toio_app/connection.py`.
- Keep constants in `toio_app/config.py`.

## 9. Quick Validation

```bash
python -m py_compile main.py app.py set_state.py scripts/set_state.py toio_app/*.py
```

## 10. License

MIT. See [LICENSE](LICENSE).
