# 文件说明（中文）：toio 连接管理，包含扫描、重试、连接与失败提示。
# File Description (EN): toio connection management with scan, retry, connect, and failure diagnostics.

import asyncio
from typing import Optional

from .compat import apply_bleak_winrt_compat
from .config import SCAN_MAX_TRIES, SCAN_RETRY_DELAY, SCAN_TIMEOUT

apply_bleak_winrt_compat()
from toio import ToioCoreCube


async def connect_cube_with_retry() -> Optional[ToioCoreCube]:
    cube = ToioCoreCube()
    for i in range(1, SCAN_MAX_TRIES + 1):
        print(f"[SCAN] attempt {i}/{SCAN_MAX_TRIES}...")
        try:
            await asyncio.wait_for(cube.scan(), timeout=SCAN_TIMEOUT)
            await cube.connect()
            print("toio connected.")
            return cube
        except asyncio.TimeoutError:
            print(f"[SCAN] timeout ({SCAN_TIMEOUT:.0f}s).")
        except AssertionError:
            print("[CONNECT] no scanned interface yet, retrying...")
        except Exception as e:
            print(f"[ERROR] scan/connect failed: {e}")
        await asyncio.sleep(SCAN_RETRY_DELAY)

    print("[SCAN] No toio detected after retries.")
    print("Please check: power on, nearby, Bluetooth enabled, not connected by other app.")
    try:
        await cube.disconnect()
    except Exception:
        pass
    return None
