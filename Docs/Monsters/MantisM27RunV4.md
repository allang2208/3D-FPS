# 螳螂-M27：俯身奔跑 V4

2026-10-06。用户确认隐身技能成功后，要求加入弯腰俯身奔跑，接敌后使用奔跑移动。

## 参考与制作

选用本机突变体-3 的 `A_Mutant3_FeralRun`。它来自 Epic 的 [Paragon: Khaimera](https://www.fab.com/listings/e7c665c1-8c13-42f0-9152-0753008853d7) `Jog_Fwd`，具备完整腿步、骨盆起伏和反向摆臂。另读取 `FeralSprint` 作为速度/动作方向备选；最终采用常规奔跑，以适合螳螂长镰与恢复环绕。

沿用 ClawV3 的原生 UE 解剖重定向器，目标仍为 BindingV2 骨架。离线将腰背前倾朝约 40° 调整，骨盆降低 8 cm，颈部反向补偿以保留前视；腿链依原步伐拟合脚掌落点，前臂沿原肘平面进一步屈起，必要时整臂抬高保留约 20 cm 镰尖离地距离。双镰随原有完整身体动作运动，不修改蒙皮、网格或骨骼参考姿态。

成品为 2 秒、60 fps、121 帧（含循环端点）的原地循环，末帧闭合至首帧。根据低位支撑阶段的脚部后移量，制作参考速度为 **356.98 cm/s**；实际移动设为 **340 cm/s**，运行时按真实速度与参考速度的比例播放。以上是制作参数，不代表视觉/地形验收结果。

## 游戏接入

- 正式动画：`/Game/Monsters/MantisM27/RunV4/Animations/A_M27_HunchedRun_RunV4`。
- 原 F6 入口：`/Game/Monsters/MantisM27/BP_MantisM27`。
- 现有 `Chase` 状态使用的 `WalkClip` 是通用移动槽，接入新奔跑动画；`WalkSpeed` 为 340，`SourceMoveSpeed` 为 356.98，`CloakMoveSpeed` 为 340。
- 未接敌仍使用原待机；接敌追击、隐身撤离/环绕以及接敌后的返回移动均使用奔跑。停止或堵路时现有速度门控切回待机。
- 保留 ClawV3 双镰攻击、BindingV2 绑骨、隐身材质、每秒 5% 回血、两次一次性触发和 80% 恢复条件。
- 复用现有状态机、移动/动画速率逻辑，无 C++ 修改，无新增 Tick、运行时 IK 或寻路开销。

## 文件与状态

- `Tools/MantisM27/retarget_run_v4.py`：读取本机参考并生成原生重定向制作输入。
- `Tools/MantisM27/author_run_v4.py`：离线姿态适配、可编辑 Blend 与 FBX 导出。
- `Tools/MantisM27/import_run_v4.py`：正式动画导入、蓝图编译与保存。
- `SourceAssets/MantisM27/RunV4/Delivery/motion_manifest.json`：制作参数。
- `SourceAssets/MantisM27/RunV4/ue_run_receipt.json`：实际资产保存与接入状态。`animation_saved`、`blueprint_connected` 同为 true 才代表本轮实际保存完成。

动画源及派生采样、Blend、FBX、uasset 继承原 UE 素材许可，不作为 CC0 或可公开再分发素材。没有运行游戏、截图、渲染或自动验收；由用户体验实际效果。
