# OpenClaw Toio ザリガニコントローラー

言語: [English](README.md) | [中文](README.zh-CN.md) | **日本語**

このプロジェクトは、固定アンカーと状態機械で toio を「オフィスのザリガニ」として動かすイベント駆動ランタイムです。

## 1. できること

- 1台の toio に対する状態機械制御
- 固定マップ領域・アンカーによる行動制御
- 2種類の状態変更手段:
  - キーボード `0-6`, `ESC`
  - 外部コマンド `python set_state.py <state> "<desc>"`
- 状態シグネチャ音を 5 秒ごとに再生
- 安全な起動/終了:
  - 起動直後は `stopped`（静止）
  - 終了時はモーターとサウンドを停止

## 2. 状態

- `stopped`: 完全停止（モーター/音停止）
- `idle`: 休憩エリア行動
- `writing`: 執筆エリア行動
- `researching`: 調査エリア巡回
- `executing`: 実行ループ行動
- `syncing`: 同期往復行動
- `error`: バグエリアのパニック行動

状態遷移は割り込み可能です。新しい状態指示が来ると現在動作を中断し、新状態の入場動作を実行してから通常ループに入ります。

## 3. 操作方法

### キーボード

- `0`: stopped
- `1`: idle
- `2`: writing
- `3`: researching
- `4`: executing
- `5`: syncing
- `6`: error
- `ESC`: 終了

### 外部コマンド

ランタイム実行中に別ターミナルで:

```bash
python set_state.py 3 "research start"
python set_state.py error "panic"
python set_state.py 0 "manual stop"
```

有効な状態入力:

- 数値: `0..6`
- 文字列: `stopped|idle|writing|researching|executing|syncing|error`

## 4. 構成

```text
.
├── main.py                  # メインエントリポイント（推奨）
├── app.py                   # 互換エントリ（main.pyへ転送）
├── set_state.py             # 互換CLI（scripts/set_state.pyへ転送）
├── scripts/
│   ├── __init__.py
│   └── set_state.py         # 外部状態コマンドの書き込み
├── toio_app/
│   ├── __init__.py
│   ├── behavior.py          # 状態機械と動作プリミティブ
│   ├── compat.py            # bleak/toio 互換パッチ
│   ├── config.py            # アンカー、確率、状態/音設定
│   ├── connection.py        # BLEスキャンと接続リトライ
│   ├── pose.py              # 位置情報解析と通知
│   ├── runner.py            # 実行オーケストレーション
│   └── state.py             # 共有姿勢状態
├── SKILL.md
├── LICENSE
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

## 5. セットアップと実行

### 要件

- Python 3.10+
- Bluetooth 有効
- 位置情報取得のため toio mat / コードシート上で使用

### 依存インストール

```bash
pip install -r requirements.txt
```

### 起動

推奨:

```bash
python main.py
```

互換:

```bash
python app.py
```

## 6. チューニング

主な設定は `toio_app/config.py`:

- マップ領域とアンカー
- 状態アクションプールとランダムイベント重み
- ランダム発火ゲート確率
- サウンドシーケンスと再生周期
- 旋回/移動のしきい値と時間

## 7. 開発ガイド

- 行動ロジック: `toio_app/behavior.py`
- ランタイム制御: `toio_app/runner.py`
- 接続処理: `toio_app/connection.py`
- 定数設定: `toio_app/config.py`

## 8. クイック検証

```bash
python -m py_compile main.py app.py set_state.py scripts/set_state.py toio_app/*.py
```

## 9. ライセンス

MIT。詳細は [LICENSE](LICENSE) を参照。
