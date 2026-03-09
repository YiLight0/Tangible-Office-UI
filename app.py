# 文件说明（中文）：项目入口文件，负责启动异步主流程。
# File Description (EN): Project entry point; starts the async main flow.

import asyncio

from toio_app import run


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n[EXIT] Interrupted by user.")
