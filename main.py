# 文件说明（中文）：项目主入口文件，负责启动异步主流程。
# File Description (EN): Primary project entrypoint; starts the async main flow.

import asyncio

from toio_app import run


def main() -> int:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n[EXIT] Interrupted by user.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
