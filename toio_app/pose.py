# 文件说明（中文）：位姿数据解析、ID 通知处理与初始位姿读取逻辑。
# File Description (EN): Pose parsing, ID-notification handling, and initial pose read logic.

from .compat import apply_bleak_winrt_compat
from .state import PoseState, shared

apply_bleak_winrt_compat()
from toio import IdInformation


def extract_pose_from_id_info(id_info) -> PoseState:
    if id_info is None:
        return PoseState(detected=False, raw_type="None")

    type_name = type(id_info).__name__

    if type_name == "PositionId":
        center = getattr(id_info, "center", None)
        if center is not None:
            point = getattr(center, "point", None)
            angle = getattr(center, "angle", None)
            if point is not None:
                x = getattr(point, "x", None)
                y = getattr(point, "y", None)
                return PoseState(
                    x=x,
                    y=y,
                    angle=angle,
                    detected=(x is not None and y is not None and angle is not None),
                    raw_type=type_name,
                )

        point = getattr(id_info, "point", None)
        angle = getattr(id_info, "angle", None)
        if point is not None:
            x = getattr(point, "x", None)
            y = getattr(point, "y", None)
            return PoseState(
                x=x,
                y=y,
                angle=angle,
                detected=(x is not None and y is not None and angle is not None),
                raw_type=type_name,
            )

    if type_name == "PositionIdMissed":
        return PoseState(detected=False, raw_type=type_name)

    return PoseState(detected=False, raw_type=type_name)


def id_notification_handler(payload: bytearray):
    id_info = IdInformation.is_my_data(payload)
    shared.update_pose(extract_pose_from_id_info(id_info))


async def initial_read_once(cube):
    try:
        id_info = await cube.api.id_information.read()
        pose = extract_pose_from_id_info(id_info)
        shared.update_pose(pose)
        if pose.detected:
            print(f"[INIT] x={pose.x}, y={pose.y}, angle={pose.angle}")
        else:
            print(f"[INIT] position unavailable, type={pose.raw_type}")
    except Exception as e:
        print(f"[INIT] read failed: {e}")
