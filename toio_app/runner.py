# 文件说明（中文）：主流程编排，集成连接、位姿通知、数字键事件驱动状态机和生命周期管理。
# File Description (EN): Main orchestrator integrating connection, pose notifications, numeric-key event state machine, and lifecycle management.

import asyncio
import json
from pathlib import Path
from typing import Callable, Optional

from pynput import keyboard

from .behavior import CrayfishBehavior
from .connection import connect_cube_with_retry
from .config import STATE_ALIASES, STATE_COMMAND_FILE, STATE_KEY_MAP, VALID_STATES
from .pose import id_notification_handler, initial_read_once


def normalize_key(key) -> Optional[str]:
    try:
        if key.char:
            ch = key.char.lower()
            if ch in STATE_KEY_MAP:
                return ch
    except AttributeError:
        pass

    if key == keyboard.Key.esc:
        return "esc"
    return None


def start_keyboard_listener(
    stop_event: asyncio.Event,
    loop: asyncio.AbstractEventLoop,
    on_state_change: Callable[[str, str, str], None],
):
    def on_press(key):
        name = normalize_key(key)
        if name is None:
            return
        if name == "esc":
            loop.call_soon_threadsafe(stop_event.set)
            return False
        state_name = STATE_KEY_MAP.get(name)
        if state_name:
            loop.call_soon_threadsafe(on_state_change, state_name, "keyboard", "")

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    return listener


def normalize_state_name(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    key = str(raw).strip().lower()
    key = STATE_ALIASES.get(key, key)
    if key in VALID_STATES:
        return key
    return None


async def watch_external_state_command(
    stop_event: asyncio.Event,
    on_state_change: Callable[[str, str, str], None],
):
    command_path = Path(STATE_COMMAND_FILE)
    last_mtime_ns: Optional[int] = None
    while not stop_event.is_set():
        try:
            if command_path.exists():
                stat = command_path.stat()
                mtime_ns = stat.st_mtime_ns
                if last_mtime_ns != mtime_ns:
                    last_mtime_ns = mtime_ns
                    data = json.loads(command_path.read_text(encoding="utf-8"))
                    state = normalize_state_name(data.get("state"))
                    desc = str(data.get("desc", "")).strip()
                    if state:
                        on_state_change(state, "external", desc)
                    else:
                        print(f"[external] invalid state ignored: {data.get('state')}")
        except Exception as e:
            print(f"[external] command read failed: {e}")

        await asyncio.sleep(0.2)


async def run() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    requested_state = {"name": None}

    print("Connecting to toio...")
    print("Controls:")
    print("  0 : stopped (still)")
    print("  1 : idle")
    print("  2 : writing")
    print("  3 : researching")
    print("  4 : executing")
    print("  5 : syncing")
    print("  6 : error")
    print("  ESC   : quit")
    print(f"Event keys: {', '.join(STATE_KEY_MAP.keys())}")
    print('External control: python set_state.py <state> "<desc>"')
    print("Startup behavior: still (wait for key 0-6).")
    print("Place the cube on a toio mat / code sheet for position reads.")

    cube = await connect_cube_with_retry()
    if cube is None:
        return

    try:
        await cube.api.id_information.register_notification_handler(id_notification_handler)
        print("Position notification registered.")

        await initial_read_once(cube)
        try:
            await cube.api.motor.motor_control(0, 0)
        except Exception:
            pass

        def on_state_change(new_state: str, source: str, desc: str):
            old = requested_state["name"]
            requested_state["name"] = new_state
            detail = f", desc={desc}" if desc else ""
            print(f"[switch:{source}] {old} -> {new_state}{detail}")

        listener = start_keyboard_listener(stop_event, loop, on_state_change)
        external_cmd_task = asyncio.create_task(
            watch_external_state_command(stop_event, on_state_change)
        )
        behavior = CrayfishBehavior(
            cube=cube,
            stop_event=stop_event,
            get_requested_state=lambda: requested_state["name"],
        )
        behavior_task = asyncio.create_task(behavior.run())

        try:
            await stop_event.wait()
        except KeyboardInterrupt:
            stop_event.set()
        finally:
            print("Stopping...")
            listener.stop()

            try:
                await cube.api.motor.motor_control(0, 0)
            except Exception:
                pass
            try:
                await cube.api.sound.stop()
            except Exception:
                pass

            try:
                await cube.api.id_information.unregister_notification_handler(
                    id_notification_handler
                )
            except Exception:
                pass

            behavior_task.cancel()
            external_cmd_task.cancel()
            await asyncio.gather(
                behavior_task, external_cmd_task, return_exceptions=True
            )

            try:
                await cube.api.motor.motor_control(0, 0)
            except Exception:
                pass
    finally:
        try:
            await cube.api.motor.motor_control(0, 0)
        except Exception:
            pass
        try:
            await cube.api.sound.stop()
        except Exception:
            pass
        try:
            await cube.disconnect()
        except Exception:
            pass

    print("Program exited.")
