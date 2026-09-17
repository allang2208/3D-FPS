# M4 基底版空仓换弹（2026-09-17 23:05 状态）

按参考视频重新设计换弹动作前的备份。

- `A_ASH12_reload_empty.uasset` — 当时引擎内的片段
- `A_ASH12_reload_empty.fbx` — 当时的导出源
- `build.py` — 当时的构建脚本（含节拍重映射 TIME_WARP、左臂路径 RELOAD_PATH、入位顿挫 JOLT）

特征：节拍按参考重排（出匣 12% / 进匣 46% / 入位 74%）、左臂按作者路径驱动、入位有 2.5°/8 mm 顿挫；手臂表演仍来自已认可的 M4 空仓换弹。
恢复方式：把 uasset 拷回 `Content/Weapons/ASH12/Integrated20260917/Animations/`，或回滚 build.py 后重跑。
