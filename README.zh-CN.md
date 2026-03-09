# OpenClaw Toio 小龙虾控制器

语言切换：[English](README.md) | **中文** | [日本語](README.ja.md)

这是一个基于事件驱动状态机的 toio 控制项目，用固定锚点和区域把小车表现成“办公室里的小龙虾”。

## 1. 项目能力

- 运行单个 toio 小车的行为状态机
- 使用固定地图区域与锚点（休息区/工作区/Bug区）
- 支持两种控制方式：
  - 键盘 `0-6`、`ESC`
  - 外部命令 `python set_state.py <状态> "<描述>"`
- 状态音效每 5 秒循环播报一次
- 启停安全：
  - 启动默认静止（`stopped`）
  - 退出强制停电机并停声音

## 2. 状态说明

- `stopped`：静止，电机与声音停止
- `idle`：休息区动作
- `writing`：写作区动作
- `researching`：研究区巡游
- `executing`：执行回路
- `syncing`：同步往返
- `error`：Bug区慌乱动作

状态切换为可抢占：新状态会打断当前动作，先执行新状态入场动作，再进入其循环。

## 3. 运行控制

### 键盘

- `0`: stopped
- `1`: idle
- `2`: writing
- `3`: researching
- `4`: executing
- `5`: syncing
- `6`: error
- `ESC`: 退出

### 外部命令

在程序运行期间，从另一个终端执行：

```bash
python set_state.py 3 "开始研究"
python set_state.py error "进入报错态"
python set_state.py 0 "手动急停"
```

支持状态输入：

- 数字：`0..6`
- 文本：`stopped|idle|writing|researching|executing|syncing|error`

## 4. 文件结构

```text
.
├── main.py                  # 主入口（推荐）
├── app.py                   # 兼容入口，转发到 main.py
├── set_state.py             # 兼容入口，转发到 scripts/set_state.py
├── scripts/
│   ├── __init__.py
│   └── set_state.py         # 外部状态命令写入器
├── toio_app/
│   ├── __init__.py
│   ├── behavior.py          # 状态机与动作原语
│   ├── compat.py            # bleak/toio 兼容补丁
│   ├── config.py            # 锚点、概率、状态配置、声音配置
│   ├── connection.py        # 蓝牙扫描与连接重试
│   ├── pose.py              # 位姿解析与通知
│   ├── runner.py            # 主流程编排与命令监听
│   └── state.py             # 共享位姿状态
├── SKILL.md
├── LICENSE
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

## 5. 安装与运行

### 环境要求

- Python 3.10+
- 蓝牙可用
- toio 放在可识别 mat/码点纸上（用于位置读取）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动

推荐：

```bash
python main.py
```

兼容旧命令：

```bash
python app.py
```

## 6. 参数调优

主要配置在 `toio_app/config.py`：

- 地图区域与锚点
- 状态动作池与随机事件权重
- 随机触发门控概率
- 声音序列与播放周期
- 转向/移动阈值与时长

## 7. 开发建议

- 行为逻辑只改 `toio_app/behavior.py`
- 流程与输入监听改 `toio_app/runner.py`
- 连接逻辑改 `toio_app/connection.py`
- 常量配置改 `toio_app/config.py`

## 8. 快速校验

```bash
python -m py_compile main.py app.py set_state.py scripts/set_state.py toio_app/*.py
```

## 9. 许可证

MIT，见 [LICENSE](LICENSE)。
