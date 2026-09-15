# DW715 单持退壳手姿重做（2026-09-15）

**历史废案：用户随后反馈仍穿模，当前已由 PalmClearance 替代。** 本文保留当时制作记录；旧作者目录和引擎输出移至 `trash/pistol-animation-20260915/` 下相同相对路径。当前入口与状态见 [掌面避让版本](dw715-single-palm-clearance-20260915.md)。

用户否定 EjectHand 版按压手姿，要求参考 GitHub 左轮动画。本次使用 [ThirdPersonShooter-AnimationSets](https://github.com/ZenXChaos/ThirdPersonShooter-AnimationSets) 的指节方向及前臂相对手掌姿态，重新适配 DW715 的按压接触和撤手路径。参考中没有与 715 完全一致的退壳按压片段，因此这是骨骼姿态适配。

改动集中于单持空仓退壳：整臂配合掌面朝向，外侧接近、轴向按压、先退出再取弹。右手持枪、弹仓机械轨道、逐发装填节奏、快速装填器和声音时序沿用原有动作；双持仍使用已制作的 RevolverReloadFlickV6。

## 文件

- 作者源及资料记录：`SourceAssets/DanWesson715DonorPress20260915/README.md`、`author_actions.py`、`animation.json`。
- 可编辑源：同目录 `DanWesson715_DonorPress_Editable.blend`。
- 导出：`Animations/` 下七个 FBX，覆盖空仓逐发装填 1–6 发与快速装填。
- 运行引用：`Source/FPSGAME/Weapons/DanWesson715WeaponAssets.h`。
- 引擎目录：`/Game/Weapons/DanWesson715/DonorPress20260915/Animations`。

## 接入状态

- 最终动作导出完成，进程退出 0。
- Editor 构建首次遇到合并编译变量遮蔽错误：`CombatStatusFormula.cpp` 的 lambda 参数 `Magic` 与 `VoxelBuildPersistence.cpp` 的文件常量同名。仅将该参数及其使用处改名为 `bMagicDamage`；不改变伤害计算。
- 随后构建遇到并行修改中的 UI 未声明变量，读取当前文件时该处已经由并行工作修正，本任务未改该 UI 文件。最终 `Build-Editor.ps1` 返回 0，记录 `Result: Succeeded` / `Target is up to date`；日志 `Saved/BuildEditor/build-20260915-095803.log`。
- 七个动画资产全部导入并保存，导入进程返回 0，日志含 `DW715_DONOR_PRESS_IMPORT_COMPLETE`；路径回执为 `SourceAssets/DanWesson715DonorPress20260915/import.json`。
- 未运行改后测试、PIE、游戏截图或验收，由用户测试。资料点云图仅用于用户要求的 GitHub 源动作学习，不作为改后效果证明。
