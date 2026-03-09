# 文件说明（中文）：外部状态切换工具，运行时写入状态命令供 app.py 监听。
# File Description (EN): External state switch tool; writes command for app.py runner to consume.

import json
import sys
from pathlib import Path

from toio_app.config import STATE_ALIASES, STATE_COMMAND_FILE, VALID_STATES


def normalize_state_name(raw: str):
    key = raw.strip().lower()
    key = STATE_ALIASES.get(key, key)
    if key in VALID_STATES:
        return key
    return None


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python set_state.py <state> "<desc>"')
        print(
            "state: 0|1|2|3|4|5|6 or stopped|idle|writing|researching|executing|syncing|error"
        )
        return 1

    state = normalize_state_name(sys.argv[1])
    desc = sys.argv[2] if len(sys.argv) >= 3 else ""

    if not state:
        print(f"Invalid state: {sys.argv[1]}")
        return 1

    payload = {"state": state, "desc": desc}
    path = Path(STATE_COMMAND_FILE)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"[set_state] state={state}, desc={desc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
