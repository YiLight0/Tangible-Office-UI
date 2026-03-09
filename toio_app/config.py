# 文件说明（中文）：集中管理小龙虾行为参数、锚点、状态动作池与扫描重试参数。
# File Description (EN): Centralized constants for crayfish behaviors, anchors, state action pools, and scan-retry settings.
#
# ----------------------------
# 动作规范（当前实现）
# ----------------------------
# 1) 地图与区域
# - 地图范围：x,y ∈ [75, 420]
# - 休息区： (75,75)  ~ (247,247)
# - Bug区：  (248,75) ~ (420,247)
# - 工作区： (75,248) ~ (420,420)
#
# 2) 运动原语（仅原地旋转 + 前后移动）
# - go_to(anchor): 分段“转向 -> 前进 -> 纠偏”，直到接近锚点（ARRIVE_THRESHOLD）
# - pause(t): 可被状态切换打断的停顿
# - look_left_right_small(): 小幅左看右看后回中
# - tiny_forward() / tiny_back(): 短距离前后试探
# - fidget(): 小幅摆头
# - panic_spin_move(): error 用的“左转+前进+右转+前进”碎步循环
# - peek_toward(anchor): 朝目标方向探一下再回收
#
# 3) 状态切换规则（键盘 1-6）
# - 1=idle, 2=writing, 3=researching, 4=executing, 5=syncing, 6=error
# - 启动后默认静止，等待按键触发状态
# - 任意时刻切换状态：立即打断当前动作，执行新状态入场动作，再进入该状态循环
# - ESC 退出；退出时强制停车并停声
#
# 4) 每个状态的主行为
# - idle: 只在 R 区活动，偏休息与偷看工作区
# - writing: 只在 W1/W2/W3，偏工位切换与专注停驻
# - researching: 主要在 Q 区巡检，偶尔去 W2 确认
# - executing: 按 E1->E2->E3->E4->E5 固定回路推进
# - syncing: 在 S1/S2/S3 做发送-回传往返
# - error: 在 B 区高频碎步、检查、求助、崩溃动作
#
# 5) 随机事件策略（低频）
# - 每轮主动作结束后，不是必触发
# - 先过状态级门控概率 STATE_RANDOM_TRIGGER（已下调）
# - 触发后按该状态 random_events 权重只选 1 个事件执行
#
# 6) 声音策略
# - 6 个状态各自有签名音（STATE_SOUNDS）
# - 进入状态立即播放一次
# - 之后每 STATE_SOUND_PERIOD_SEC 秒自动播放一次（当前为 5 秒）
# - 声音参数：音高 note(0-127) + 时长 duration(<=2.55s) + 固定间隔/音量
#
# 7) 当前目标倾向
# - 明显状态差异：先到远点再入场（entry_*_stage）
# - 减少原地小碎动：随机事件低频化，主动作优先
# - 保持“像小动物”而非持续陀螺旋转

SCAN_MAX_TRIES = 6
SCAN_RETRY_DELAY = 2.0
SCAN_TIMEOUT = 8.0
STATE_COMMAND_FILE = "state_command.json"

MAP_BOUNDS = {"x": (75, 420), "y": (75, 420)}
REGIONS = {
    "rest": ((75, 75), (247, 247)),
    "bug": ((248, 75), (420, 247)),
    "work": ((75, 248), (420, 420)),
}

ANCHORS = {
    # Rest area
    "R1": (115, 115),
    "R2": (200, 115),
    "R3": (160, 160),
    "R4": (115, 210),
    "R5": (210, 210),
    # Bug area
    "B1": (285, 115),
    "B2": (380, 115),
    "B3": (335, 160),
    "B4": (285, 210),
    "B5": (385, 210),
    # Writing
    "W1": (130, 290),
    "W2": (245, 290),
    "W3": (360, 290),
    # Research
    "Q1": (120, 360),
    "Q2": (220, 390),
    "Q3": (330, 370),
    "Q4": (170, 330),
    "Q5": (300, 330),
    # Executing loop
    "E1": (150, 270),
    "E2": (245, 260),
    "E3": (340, 270),
    "E4": (320, 340),
    "E5": (170, 340),
    # Syncing
    "S1": (120, 400),
    "S2": (370, 400),
    "S3": (245, 400),
}

STATE_KEY_MAP = {
    "0": "stopped",
    "1": "idle",
    "2": "writing",
    "3": "researching",
    "4": "executing",
    "5": "syncing",
    "6": "error",
}
DEFAULT_STATE = "idle"
VALID_STATES = {"stopped", "idle", "writing", "researching", "executing", "syncing", "error"}
STATE_ALIASES = {
    "0": "stopped",
    "1": "idle",
    "2": "writing",
    "3": "researching",
    "4": "executing",
    "5": "syncing",
    "6": "error",
    "stop": "stopped",
    "pause": "stopped",
}
STATE_RANDOM_TRIGGER = {
    "stopped": 0.0,
    "idle": 0.08,
    "writing": 0.07,
    "researching": 0.10,
    "executing": 0.06,
    "syncing": 0.08,
    "error": 0.12,
}

STATE_ACTIONS = {
    "stopped": {
        "entry": ["entry_stopped"],
        "main": ["stopped_hold"],
        "random_events": [],
    },
    "idle": {
        "entry": ["entry_idle"],
        "main": ["idle_roam_rest", "idle_center_rest", "idle_peek_work"],
        "random_events": [
            {"name": "idle_change_posture", "prob": 0.45},
            {"name": "idle_dream_twitch", "prob": 0.20},
            {"name": "idle_almost_go_work", "prob": 0.35},
        ],
    },
    "writing": {
        "entry": ["entry_writing"],
        "main": ["writing_switch_desk", "writing_focus_typing", "writing_stretch"],
        "random_events": [
            {"name": "writing_inspiration", "prob": 0.45},
            {"name": "writing_restructure_doc", "prob": 0.20},
            {"name": "writing_stuck_thinking", "prob": 0.35},
        ],
    },
    "researching": {
        "entry": ["entry_researching"],
        "main": ["research_scan", "research_compare_pair", "research_patrol_chain"],
        "random_events": [
            {"name": "research_new_clue", "prob": 0.45},
            {"name": "research_overload", "prob": 0.20},
            {"name": "research_confirm_info", "prob": 0.35},
        ],
    },
    "executing": {
        "entry": ["entry_executing"],
        "main": ["execute_round", "execute_wait_reply", "execute_push_next"],
        "random_events": [
            {"name": "execute_speed_up", "prob": 0.45},
            {"name": "execute_mid_realign", "prob": 0.30},
            {"name": "execute_final_sprint", "prob": 0.25},
        ],
    },
    "syncing": {
        "entry": ["entry_syncing"],
        "main": ["sync_send", "sync_return", "sync_full_cycle"],
        "random_events": [
            {"name": "sync_fast_network", "prob": 0.35},
            {"name": "sync_network_jitter", "prob": 0.25},
            {"name": "sync_resend", "prob": 0.15},
            {"name": "sync_done_nod", "prob": 0.25},
        ],
    },
    "error": {
        "entry": ["entry_error"],
        "main": ["error_panic_loop", "error_check_points", "error_seek_help", "error_freeze_then_panic"],
        "random_events": [
            {"name": "error_extra_panic", "prob": 0.35},
            {"name": "error_existential", "prob": 0.20},
            {"name": "error_bigger_panic", "prob": 0.30},
            {"name": "error_try_help", "prob": 0.15},
        ],
    },
}

ARRIVE_THRESHOLD = 24.0
HEADING_THRESHOLD = 10.0
TURN_SPEED = 38
MOVE_SPEED = 42
TINY_MOVE_SPEED = 30
SMALL_TURN_SEC = 0.14
MEDIUM_TURN_SEC = 0.24
BIG_TURN_SEC = 0.36
SHORT_MOVE_SEC = 0.16
STEP_SLEEP = 0.06

# State sound signatures: (midi_note, duration_sec)
STATE_SOUNDS = {
    "idle": [(60, 0.18), (64, 0.18)],
    "writing": [(62, 0.10), (62, 0.10), (65, 0.12)],
    "researching": [(60, 0.10), (64, 0.12), (67, 0.14)],
    "executing": [(55, 0.12), (55, 0.12), (55, 0.12)],
    "syncing": [(60, 0.10), (67, 0.10), (60, 0.18)],
    "error": [(76, 0.08), (72, 0.08), (76, 0.08), (72, 0.10)],
}
STATE_SOUND_GAP_SEC = 0.03
STATE_SOUND_VOLUME = 120
STATE_SOUND_PERIOD_SEC = 5.0
