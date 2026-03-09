# 文件说明（中文）：共享运行状态定义（仅位姿状态）及线程安全访问。
# File Description (EN): Shared runtime state (pose only) with thread-safe access helpers.

import threading
from dataclasses import dataclass
from typing import Optional


@dataclass
class PoseState:
    x: Optional[int] = None
    y: Optional[int] = None
    angle: Optional[int] = None
    detected: bool = False
    raw_type: str = "Unknown"


class SharedState:
    def __init__(self):
        self.pose = PoseState()
        self.lock = threading.Lock()

    def update_pose(self, pose: PoseState):
        with self.lock:
            self.pose = pose

    def get_pose(self) -> PoseState:
        with self.lock:
            return PoseState(
                x=self.pose.x,
                y=self.pose.y,
                angle=self.pose.angle,
                detected=self.pose.detected,
                raw_type=self.pose.raw_type,
            )


shared = SharedState()
