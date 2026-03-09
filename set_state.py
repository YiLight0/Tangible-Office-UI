# 文件说明（中文）：兼容入口，转发到 scripts/set_state.py。
# File Description (EN): Compatibility entrypoint forwarding to scripts/set_state.py.

from scripts.set_state import main


if __name__ == "__main__":
    raise SystemExit(main())
