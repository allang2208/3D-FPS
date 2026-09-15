# DW715 单持退壳：手臂方向与掌面避让（2026-09-15）

本轮响应用户对 DonorPress 版本仍穿模的反馈。重新制作掌面倾斜和接触位置，将腕部支撑改为中立骨架关系下的整臂求解，并增加轴向退出和外侧移动空间。

完整制作依据、参数及源文件见 `SourceAssets/DanWesson715PalmClearance20260915/README.md`。

## 接入状态

- 七段 FBX 与可编辑 Blend 已导出，作者进程返回 0，日志含 `DW715_PALM_CLEARANCE_AUTHORING_COMPLETE`。
- 引擎目标：`/Game/Weapons/DanWesson715/PalmClearance20260915/Animations`。
- 单持空仓逐发 1–6 发及快速装填使用本轮资源；机械行程、弹药与音效时钟继承原动作。
- 七段动画均已导入保存，导入进程返回 0，日志含 `DW715_PALM_CLEARANCE_IMPORT_COMPLETE`；路径回执 `SourceAssets/DanWesson715PalmClearance20260915/import.json`。
- `Source/FPSGAME/Weapons/DanWesson715WeaponAssets.h` 的空仓逐发和快速装填路径已更新，必要 Editor 构建返回 0 / `Result: Succeeded`；日志 `Saved/BuildEditor/build-20260915-101118.log`。
- 未主动进行改后测试或验收，由用户测试。

## 发布整理

旧版依赖已提取到当前目录的 `reference_basis.py` 和独立 `import_assets.py`，不再读取 EjectHand/DonorPress 目录。原有 FBX 和 uasset 未因此重新生成；作者功能与运行版本保持。归档引用检查、散列与发布范围见 [整理记录](pistol-publication-20260915/README.md)。
