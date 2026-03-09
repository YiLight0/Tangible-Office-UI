---
name: openclaw-toio-crayfish
description: Control a toio cube as an office-crayfish behavior agent with event-driven state transitions, fixed map anchors, keyboard and external command switching, and periodic sound signatures. Use when implementing, debugging, or extending this project's state machine, motion primitives, and runtime orchestration.
---

# OpenClaw Toio Crayfish Skill

Use this repository to run and evolve a toio behavior skill project.

## Core Runtime

- Start runtime with `python main.py` (recommended).
- `python app.py` is kept as a compatibility entrypoint.
- Runtime listens for:
  - Keyboard states: `0-6`
  - External commands written via `python set_state.py <state> "<desc>"`

## State Semantics

- `stopped`: hard stop, no movement, no sound
- `idle`, `writing`, `researching`, `executing`, `syncing`, `error`: behavior states driven by `toio_app/behavior.py`

## Editing Rules

- Keep anchors, probabilities, and state mappings in `toio_app/config.py`.
- Keep movement primitives and state loops in `toio_app/behavior.py`.
- Keep connection logic in `toio_app/connection.py`.
- Keep orchestration and event input in `toio_app/runner.py`.

## Verification

- After changes, run:

```bash
python -m py_compile main.py app.py set_state.py scripts/set_state.py toio_app/*.py
```

- Validate behavior:
  - Startup should remain still until state command is received.
  - State switch should interrupt current actions and enter target state flow.
  - Exit should always stop motor and sound.
