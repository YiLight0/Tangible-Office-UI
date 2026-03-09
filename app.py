# 文件说明（中文）：兼容入口，推荐改用 main.py。
# File Description (EN): Compatibility entrypoint; prefer using main.py.

from main import main


if __name__ == "__main__":
    raise SystemExit(main())
