# 文件说明（中文）：小龙虾行为状态机与动作原语，实现 1-6 事件驱动行为切换。
# File Description (EN): Crayfish behavior state machine and motion primitives for event-driven mode switching (keys 1-6).

import asyncio
import math
import random
from typing import Callable, Optional

from .config import (
    ANCHORS,
    ARRIVE_THRESHOLD,
    BIG_TURN_SEC,
    HEADING_THRESHOLD,
    MEDIUM_TURN_SEC,
    MOVE_SPEED,
    SHORT_MOVE_SEC,
    SMALL_TURN_SEC,
    STATE_ACTIONS,
    STATE_SOUND_GAP_SEC,
    STATE_SOUND_PERIOD_SEC,
    STATE_SOUND_VOLUME,
    STATE_SOUNDS,
    STATE_RANDOM_TRIGGER,
    STEP_SLEEP,
    TINY_MOVE_SPEED,
    TURN_SPEED,
)
from .state import shared
from .compat import apply_bleak_winrt_compat

apply_bleak_winrt_compat()
from toio import MidiNote, Note


def _norm_angle_deg(v: float) -> float:
    while v > 180:
        v -= 360
    while v <= -180:
        v += 360
    return v


class CrayfishBehavior:
    def __init__(
        self,
        cube,
        stop_event: asyncio.Event,
        get_requested_state: Callable[[], Optional[str]],
    ):
        self.cube = cube
        self.stop_event = stop_event
        self.get_requested_state = get_requested_state
        self.current_state: Optional[str] = None
        self.current_anchor: Optional[str] = None
        self.execute_route = ["E1", "E2", "E3", "E4", "E5"]
        self.execute_idx = 0
        self.execute_fast_left = 0
        self.last_q_anchor = "Q4"
        self.next_sound_at = 0.0

    def _log(self, action_type: str, action_name: str, target: Optional[str] = None):
        target_msg = f", target={target}" if target else ""
        print(f"[state={self.current_state}] [{action_type}] {action_name}{target_msg}")

    def _should_abort(self) -> bool:
        if self.stop_event.is_set():
            return True
        requested = self.get_requested_state()
        return self.current_state is not None and requested != self.current_state

    async def _pause_interruptible(self, duration: float) -> bool:
        end = asyncio.get_running_loop().time() + max(0.0, duration)
        while asyncio.get_running_loop().time() < end:
            if self._should_abort():
                return False
            await self._maybe_play_periodic_state_sound()
            remain = end - asyncio.get_running_loop().time()
            await asyncio.sleep(min(STEP_SLEEP, max(0.01, remain)))
        return not self._should_abort()

    async def _motor_for(self, left: int, right: int, duration: float) -> bool:
        if self._should_abort():
            return False
        await self.cube.api.motor.motor_control(left, right)
        ok = await self._pause_interruptible(duration)
        await self.cube.api.motor.motor_control(0, 0)
        await self._pause_interruptible(0.04)
        return ok and (not self._should_abort())

    async def _turn_left(self, duration: float) -> bool:
        return await self._motor_for(-TURN_SPEED, TURN_SPEED, duration)

    async def _turn_right(self, duration: float) -> bool:
        return await self._motor_for(TURN_SPEED, -TURN_SPEED, duration)

    async def tiny_forward(self) -> bool:
        self._log("primitive", "tiny_forward")
        return await self._motor_for(TINY_MOVE_SPEED, TINY_MOVE_SPEED, SHORT_MOVE_SEC)

    async def tiny_back(self) -> bool:
        self._log("primitive", "tiny_back")
        return await self._motor_for(-TINY_MOVE_SPEED, -TINY_MOVE_SPEED, SHORT_MOVE_SEC)

    async def pause(self, duration: float) -> bool:
        self._log("primitive", f"pause({duration:.2f}s)")
        return await self._pause_interruptible(duration)

    async def look_left_right_small(self) -> bool:
        self._log("primitive", "look_left_right_small")
        return (
            await self._turn_left(SMALL_TURN_SEC)
            and await self._pause_interruptible(0.12)
            and await self._turn_right(SMALL_TURN_SEC * 2)
            and await self._pause_interruptible(0.12)
            and await self._turn_left(SMALL_TURN_SEC)
        )

    async def fidget(self) -> bool:
        self._log("primitive", "fidget")
        return (
            await self._turn_left(SMALL_TURN_SEC * 0.6)
            and await self._pause_interruptible(0.08)
            and await self._turn_right(SMALL_TURN_SEC * 0.6)
        )

    async def panic_spin_move(self, loops: int = 3, amp: float = 1.0) -> bool:
        self._log("primitive", f"panic_spin_move(loops={loops},amp={amp:.1f})")
        for _ in range(loops):
            if not await self._turn_left(MEDIUM_TURN_SEC * amp):
                return False
            if not await self._motor_for(MOVE_SPEED, MOVE_SPEED, SHORT_MOVE_SEC):
                return False
            if not await self._turn_right(MEDIUM_TURN_SEC * amp):
                return False
            if not await self._motor_for(MOVE_SPEED, MOVE_SPEED, SHORT_MOVE_SEC):
                return False
        return True

    async def _turn_toward_anchor(self, anchor_name: str) -> bool:
        pose = shared.get_pose()
        if not pose.detected or pose.x is None or pose.y is None or pose.angle is None:
            return await self.fidget()

        tx, ty = ANCHORS[anchor_name]
        dx = tx - pose.x
        dy = ty - pose.y
        target_heading = math.degrees(math.atan2(dy, dx))
        diff = _norm_angle_deg(target_heading - pose.angle)

        if abs(diff) <= HEADING_THRESHOLD:
            return True

        turn_dur = max(0.08, min(MEDIUM_TURN_SEC, abs(diff) / 180.0 * MEDIUM_TURN_SEC))
        # toio angle increases clockwise on mat coordinates:
        # positive diff means target is clockwise from current heading.
        if diff > 0:
            return await self._turn_right(turn_dur)
        return await self._turn_left(turn_dur)

    async def peek_toward(self, target_anchor: str) -> bool:
        self._log("primitive", "peek_toward", target_anchor)
        return (
            await self._turn_toward_anchor(target_anchor)
            and await self.tiny_forward()
            and await self._pause_interruptible(0.22)
            and await self.tiny_back()
        )

    async def go_to(self, anchor_name: str) -> bool:
        self._log("primitive", "go_to", anchor_name)
        tx, ty = ANCHORS[anchor_name]

        # Turn in short chunks toward the target.
        for _ in range(12):
            if self._should_abort():
                return False
            pose = shared.get_pose()
            if not pose.detected or pose.x is None or pose.y is None or pose.angle is None:
                await self.fidget()
                break
            dx = tx - pose.x
            dy = ty - pose.y
            if math.hypot(dx, dy) <= ARRIVE_THRESHOLD:
                self.current_anchor = anchor_name
                return True
            heading = math.degrees(math.atan2(dy, dx))
            diff = _norm_angle_deg(heading - pose.angle)
            if abs(diff) <= HEADING_THRESHOLD:
                break
            turn_dur = max(0.08, min(MEDIUM_TURN_SEC, abs(diff) / 180.0 * MEDIUM_TURN_SEC))
            # positive diff => clockwise turn.
            if diff > 0:
                if not await self._turn_right(turn_dur):
                    return False
            else:
                if not await self._turn_left(turn_dur):
                    return False

        # Move to target in short bursts. No sideways or curved control is used.
        for _ in range(40):
            if self._should_abort():
                return False
            pose = shared.get_pose()
            if not pose.detected or pose.x is None or pose.y is None or pose.angle is None:
                if not await self._motor_for(MOVE_SPEED, MOVE_SPEED, SHORT_MOVE_SEC):
                    return False
                continue

            dx = tx - pose.x
            dy = ty - pose.y
            dist = math.hypot(dx, dy)
            if dist <= ARRIVE_THRESHOLD:
                self.current_anchor = anchor_name
                return True

            heading = math.degrees(math.atan2(dy, dx))
            diff = _norm_angle_deg(heading - pose.angle)
            if abs(diff) > 32:
                if diff > 0:
                    if not await self._turn_right(SMALL_TURN_SEC):
                        return False
                else:
                    if not await self._turn_left(SMALL_TURN_SEC):
                        return False
            else:
                move_sec = max(0.10, min(0.34, dist / 330.0))
                if not await self._motor_for(MOVE_SPEED, MOVE_SPEED, move_sec):
                    return False

        self.current_anchor = anchor_name
        return True

    def _pick_random(self, items):
        return items[random.randrange(len(items))]

    async def play_state_sound(self, state_name: str) -> None:
        seq = STATE_SOUNDS.get(state_name)
        if not seq:
            return
        try:
            await self.cube.api.sound.stop()
        except Exception:
            pass
        try:
            notes = []
            for midi_note, duration_sec in seq:
                duration_ms = int(max(0.01, min(2.55, duration_sec)) * 1000)
                midi_value = int(max(0, min(127, midi_note)))
                notes.append(
                    MidiNote(
                        duration_ms=duration_ms,
                        note=Note(midi_value),
                        volume=STATE_SOUND_VOLUME,
                    )
                )
                if STATE_SOUND_GAP_SEC > 0:
                    notes.append(
                        MidiNote(
                            duration_ms=int(STATE_SOUND_GAP_SEC * 1000),
                            note=Note.NO_SOUND,
                            volume=0,
                        )
                    )
            if notes:
                await self.cube.api.sound.play_midi(repeat=1, midi_notes=notes)
            self._log("sound", f"state_signature:{state_name}")
        except Exception as e:
            self._log("sound", f"state_signature_failed:{state_name}", str(e))

    async def _maybe_play_periodic_state_sound(self) -> None:
        if not self.current_state:
            return
        now = asyncio.get_running_loop().time()
        if now < self.next_sound_at:
            return
        await self.play_state_sound(self.current_state)
        self.next_sound_at = now + STATE_SOUND_PERIOD_SEC

    def _next_execute_anchor(self) -> str:
        self.execute_idx = (self.execute_idx + 1) % len(self.execute_route)
        return self.execute_route[self.execute_idx]

    async def entry_idle(self) -> bool:
        self._log("entry", "entry_idle_stage", "R1")
        self._log("entry", "entry_idle", "R3")
        return (
            await self.go_to("R1")
            and await self.pause(0.2)
            and await self.go_to("R3")
            and await self.pause(0.8)
        )

    async def entry_writing(self) -> bool:
        self._log("entry", "entry_writing_stage", "W3")
        self._log("entry", "entry_writing", "W2")
        return (
            await self.go_to("W3")
            and await self.pause(0.2)
            and await self.go_to("W2")
            and await self.look_left_right_small()
            and await self.pause(0.6)
        )

    async def entry_researching(self) -> bool:
        target = self._pick_random(["Q4", "Q5"])
        self.last_q_anchor = target
        self._log("entry", "entry_researching_stage", "Q1")
        self._log("entry", "entry_researching", target)
        return await self.go_to("Q1") and await self.pause(0.2) and await self.go_to(target)

    async def entry_executing(self) -> bool:
        self.execute_idx = 0
        self.execute_fast_left = 0
        self._log("entry", "entry_executing_stage", "E5")
        self._log("entry", "entry_executing", "E1")
        return (
            await self.go_to("E5")
            and await self.pause(0.15)
            and await self.go_to("E1")
            and await self.pause(0.25)
        )

    async def entry_syncing(self) -> bool:
        self._log("entry", "entry_syncing_stage", "S2")
        self._log("entry", "entry_syncing", "S1")
        return (
            await self.go_to("S2")
            and await self.pause(0.2)
            and await self.go_to("S1")
            and await self.pause(0.5)
        )

    async def entry_error(self) -> bool:
        self._log("entry", "entry_error_stage", "B5")
        self._log("entry", "entry_error", "B3")
        return (
            await self.go_to("B5")
            and await self.pause(0.15)
            and await self.go_to("B3")
            and await self.panic_spin_move(loops=2, amp=1.0)
        )

    async def entry_stopped(self) -> bool:
        self._log("entry", "entry_stopped")
        try:
            await self.cube.api.motor.motor_control(0, 0)
        except Exception:
            pass
        try:
            await self.cube.api.sound.stop()
        except Exception:
            pass
        return await self.pause(0.05)

    async def stopped_hold(self) -> bool:
        self._log("main", "stopped_hold")
        try:
            await self.cube.api.motor.motor_control(0, 0)
        except Exception:
            pass
        return await self.pause(0.3)

    async def idle_roam_rest(self) -> bool:
        target = random.choices(["R1", "R2", "R4", "R5"], weights=[1, 1, 1, 2], k=1)[0]
        self._log("main", "idle_roam_rest", target)
        return (
            await self.go_to(target)
            and await self.look_left_right_small()
            and await self.pause(1.2)
        )

    async def idle_center_rest(self) -> bool:
        self._log("main", "idle_center_rest", "R3")
        return await self.go_to("R3") and await self.fidget() and await self.pause(1.8)

    async def idle_peek_work(self) -> bool:
        self._log("main", "idle_peek_work", "R5")
        return await self.go_to("R5") and await self.peek_toward("W2") and await self.pause(0.9)

    async def writing_switch_desk(self) -> bool:
        cands = ["W1", "W2", "W3"]
        if self.current_anchor in cands:
            cands.remove(self.current_anchor)
        target = self._pick_random(cands)
        self._log("main", "writing_switch_desk", target)
        return (
            await self.go_to(target)
            and await self.pause(0.35)
            and await self.look_left_right_small()
            and await self.pause(0.25)
        )

    async def writing_focus_typing(self) -> bool:
        self._log("main", "writing_focus_typing", "W2")
        return (
            await self.go_to("W2")
            and await self.fidget()
            and await self.fidget()
            and await self.pause(1.2)
        )

    async def writing_stretch(self) -> bool:
        target = self._pick_random(["W1", "W2", "W3"])
        self._log("main", "writing_stretch", target)
        return (
            await self.go_to(target)
            and await self._turn_left(BIG_TURN_SEC)
            and await self.pause(0.20)
            and await self._turn_right(BIG_TURN_SEC * 2)
            and await self.pause(0.20)
            and await self._turn_left(BIG_TURN_SEC)
        )

    async def research_scan(self) -> bool:
        target = self._pick_random(["Q1", "Q2", "Q3", "Q4", "Q5"])
        self.last_q_anchor = target
        self._log("main", "research_scan", target)
        return await self.go_to(target) and await self.look_left_right_small() and await self.pause(0.4)

    async def research_compare_pair(self) -> bool:
        pair = self._pick_random([("Q1", "Q4"), ("Q4", "Q2"), ("Q2", "Q5"), ("Q5", "Q3")])
        self.last_q_anchor = pair[1]
        self._log("main", "research_compare_pair", f"{pair[0]}->{pair[1]}")
        return (
            await self.go_to(pair[0]) and await self.pause(0.25) and await self.go_to(pair[1]) and await self.pause(0.8)
        )

    async def research_patrol_chain(self) -> bool:
        route = self._pick_random([["Q1", "Q2", "Q3"], ["Q4", "Q5"]])
        self._log("main", "research_patrol_chain", "->".join(route))
        for name in route:
            self.last_q_anchor = name
            if not (await self.go_to(name) and await self.pause(0.22)):
                return False
        return True

    async def execute_round(self) -> bool:
        nxt = self._next_execute_anchor()
        self._log("main", "execute_round", nxt)
        pause_t = 0.10 if self.execute_fast_left > 0 else 0.18
        if self.execute_fast_left > 0:
            self.execute_fast_left -= 1
        return await self.go_to(nxt) and await self.pause(pause_t)

    async def execute_wait_reply(self) -> bool:
        nxt = self._next_execute_anchor()
        self._log("main", "execute_wait_reply", nxt)
        if not await self.go_to(nxt):
            return False
        if nxt in {"E2", "E4"}:
            return await self.pause(0.55) and await self.fidget()
        return await self.pause(0.12)

    async def execute_push_next(self) -> bool:
        nxt = self._next_execute_anchor()
        self._log("main", "execute_push_next", nxt)
        return await self.go_to(nxt) and await self.pause(0.06)

    async def sync_send(self) -> bool:
        self._log("main", "sync_send", "S1->S3->S2")
        return (
            await self.go_to("S1")
            and await self.go_to("S3")
            and await self.pause(0.35)
            and await self.go_to("S2")
            and await self.pause(0.45)
        )

    async def sync_return(self) -> bool:
        self._log("main", "sync_return", "S2->S3->S1")
        return (
            await self.go_to("S2")
            and await self.go_to("S3")
            and await self.pause(0.35)
            and await self.go_to("S1")
            and await self.pause(0.45)
        )

    async def sync_full_cycle(self) -> bool:
        self._log("main", "sync_full_cycle", "send+return")
        return await self.sync_send() and await self.sync_return()

    async def error_panic_loop(self) -> bool:
        self._log("main", "error_panic_loop", "B3")
        return await self.go_to("B3") and await self.panic_spin_move(loops=3, amp=1.0)

    async def error_check_points(self) -> bool:
        route = self._pick_random([["B3", "B1", "B5"], ["B3", "B2", "B4"]])
        self._log("main", "error_check_points", "->".join(route))
        for name in route:
            if not (await self.go_to(name) and await self.pause(0.18)):
                return False
        return True

    async def error_seek_help(self) -> bool:
        target = self._pick_random(["B4", "B5"])
        self._log("main", "error_seek_help", target)
        return (
            await self.go_to(target)
            and await self.peek_toward("W2")
            and await self.tiny_back()
        )

    async def error_freeze_then_panic(self) -> bool:
        target = self.current_anchor if self.current_anchor in {"B1", "B2", "B3", "B4", "B5"} else "B3"
        self._log("main", "error_freeze_then_panic", target)
        return (
            await self.go_to(target)
            and await self.pause(0.8)
            and await self._turn_left(BIG_TURN_SEC)
            and await self.panic_spin_move(loops=2, amp=1.0)
        )

    async def _event_idle_change_posture(self) -> bool:
        return await self.tiny_back() and await self.tiny_forward()

    async def _event_idle_dream_twitch(self) -> bool:
        return await self.tiny_forward() and await self.pause(0.35)

    async def _event_idle_almost_go_work(self) -> bool:
        if self.current_anchor != "R5":
            return True
        return await self.peek_toward("W2") and await self.tiny_back()

    async def _event_writing_inspiration(self) -> bool:
        return await self.tiny_forward()

    async def _event_writing_restructure_doc(self) -> bool:
        target = self._pick_random(["W1", "W2", "W3"])
        return await self.go_to(target)

    async def _event_writing_stuck_thinking(self) -> bool:
        return await self._turn_left(MEDIUM_TURN_SEC) and await self._turn_right(MEDIUM_TURN_SEC * 2) and await self._turn_left(MEDIUM_TURN_SEC) and await self.pause(0.5)

    async def _event_research_new_clue(self) -> bool:
        target = self._pick_random(["Q1", "Q2", "Q3", "Q4", "Q5"])
        if target == self.last_q_anchor:
            target = self._pick_random(["Q1", "Q2", "Q3", "Q4", "Q5"])
        self.last_q_anchor = target
        return await self.go_to(target)

    async def _event_research_overload(self) -> bool:
        return await self._turn_left(MEDIUM_TURN_SEC) and await self._turn_right(MEDIUM_TURN_SEC) and await self._turn_left(MEDIUM_TURN_SEC) and await self._turn_right(MEDIUM_TURN_SEC)

    async def _event_research_confirm_info(self) -> bool:
        back = self.last_q_anchor if self.last_q_anchor in {"Q1", "Q2", "Q3", "Q4", "Q5"} else "Q4"
        return await self.go_to("W2") and await self.pause(0.3) and await self.go_to(back)

    async def _event_execute_speed_up(self) -> bool:
        self.execute_fast_left = 4
        return await self.pause(0.1)

    async def _event_execute_mid_realign(self) -> bool:
        return await self.tiny_forward() and await self.fidget()

    async def _event_execute_final_sprint(self) -> bool:
        return await self.tiny_forward()

    async def _event_sync_fast_network(self) -> bool:
        return await self.pause(0.12)

    async def _event_sync_network_jitter(self) -> bool:
        return await self.pause(0.8) and await self.look_left_right_small()

    async def _event_sync_resend(self) -> bool:
        target = self._pick_random(["S1", "S2"])
        return await self.go_to(target) and await self.sync_send()

    async def _event_sync_done_nod(self) -> bool:
        return await self.fidget()

    async def _event_error_extra_panic(self) -> bool:
        return await self.panic_spin_move(loops=2, amp=1.0)

    async def _event_error_existential(self) -> bool:
        return await self.pause(0.7) and await self.panic_spin_move(loops=1, amp=1.1)

    async def _event_error_bigger_panic(self) -> bool:
        return await self.panic_spin_move(loops=2, amp=1.3)

    async def _event_error_try_help(self) -> bool:
        return await self.peek_toward("W2") and await self.tiny_back()

    def _action_method(self, name: str):
        return getattr(self, name)

    async def _run_entry(self, state_name: str) -> bool:
        for entry_name in STATE_ACTIONS[state_name]["entry"]:
            self._log("entry", entry_name)
            if not await self._action_method(entry_name)():
                return False
        return True

    async def _run_random_event_if_any(self, state_name: str) -> bool:
        gate_prob = STATE_RANDOM_TRIGGER.get(state_name, 0.08)
        if random.random() >= gate_prob:
            self._log("event", "none")
            return True

        candidates = []
        weights = []
        for e in STATE_ACTIONS[state_name]["random_events"]:
            if e["name"] == "idle_almost_go_work" and self.current_anchor != "R5":
                continue
            candidates.append(e["name"])
            weights.append(e["prob"])
        if not candidates:
            self._log("event", "none")
            return True

        event_name = random.choices(candidates, weights=weights, k=1)[0]
        self._log("event", event_name)
        handler_name = "_event_" + event_name
        handler = getattr(self, handler_name, None)
        if handler is None:
            return True
        return await handler()

    async def run(self) -> None:
        while not self.stop_event.is_set():
            requested = self.get_requested_state()
            if requested is None:
                await asyncio.sleep(STEP_SLEEP)
                continue
            if requested != self.current_state:
                self.current_state = requested
                self._log("switch", f"state->{self.current_state}")
                self.next_sound_at = 0.0
                await self._maybe_play_periodic_state_sound()
                if not await self._run_entry(self.current_state):
                    continue
                if self._should_abort():
                    continue

            await self._maybe_play_periodic_state_sound()
            main_name = self._pick_random(STATE_ACTIONS[self.current_state]["main"])
            self._log("main", main_name)
            main_ok = await self._action_method(main_name)()
            if not main_ok or self._should_abort():
                continue
            if not await self._run_random_event_if_any(self.current_state):
                continue
