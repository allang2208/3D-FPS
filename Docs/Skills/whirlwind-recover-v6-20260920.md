# 大旋风：外送后摇 Recover V6（2026-09-20）

用户要求：旋转块结束后，将武器向外伸到参考视频中的位置，再恢复待机。沿用 `BV18b4y1774T` 3:00–3:04 的风车攻击参考，本轮着重观察本机 `ImpactV5/Reference/frame_24.jpg`、`frame_25.jpg`（约 183.33–183.50 秒）中剑指向前上方、握柄送离胸前的姿态。视频缺少完整三维信息，本动作是按该意图重建的双手剑收势。

## 动作

- 0.00–1.30 秒：从当前运行资产直接保留已有源关键帧，包括蓄势和两圈旋转。
- 1.30–1.48 秒：双手跟随握柄向外送，剑尖指向前上方偏右。
- 1.48–1.54 秒：维持伸展轮廓并轻微卸力。
- 1.54–1.82 秒：平滑收回原待机。数据中的后摇仍为 0.52 秒；480 fps 资产长度按原来的 874 个间隔保存。

普通柄作者源以 V5 已烘焙 Blend 为逐帧基底，仅重做 recover。起点用 0.065 秒五次平滑修正接入原轨迹；双手相对握柄同步运输，固定骨长求解肩肘，前臂滚转随握姿传递，辅助骨和手指沿用各自父骨关系。加长柄复用既有左手 18 mm 握距适配。

## 接入

本轮已通过 `Tools/AssetPipeline/mcp_call_codex.ps1` 的互斥批次完成普通柄导入、加长柄制作和当前资产保存：

- `/Game/Weapons/AzureRunesword20260913/A_RuneSword_WhirlwindV5`
- `/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_WhirlwindV5`

运行时继续引用上述路径；它们的 `Whirlwind.RecoverRevision` 元数据现为 `OutwardRecoverV6`。先在各自目录保留 `A_RuneSword_WhirlwindV5_BeforeRecoverV6`，再写入后摇骨骼轨道，不替换资产对象。V6 制作资产名为 `A_RuneSword_WhirlwindRecoverV6`，也保存在各自目录。骨骼轨道在旋转结束点及之前取自接入时当前资产；其他资产属性、通知和 C++ 加载路径继续沿用。

作者目录：`SourceAssets/Whirlwind20260920/RecoverV6/`。

- `author_recover.py`：关键姿态、时间曲线、双臂求解和普通柄 Blend/FBX 制作入口。
- `WhirlwindRecover_Manny_Editable.blend`、`Export/A_RuneSword_WhirlwindRecoverV6.fbx`：本轮完整可编辑源与普通柄导出。
- `author_long_grip.py`、`LongGripExport/`：加长柄适配脚本、完整 FBX 与可编辑左臂关键帧。
- `import_recover.py`：导入和写入当前运行资产；已完成时通过元数据跳过发布，不用于同名反复覆盖新版本。
- `authoring.json`、`import_receipt.json`、`import-bridge-01.txt`：作者参数和本轮保存结果。

原 `ImpactV5` Blend/FBX 保留为制作基底，当前收势源以 `RecoverV6` 为准。本轮没有更改 C++、技能数值、相机转动或已完成的屏幕黄色边缘模糊修正，不需要原生编译。

仅完成制作、导出、导入和保存；未运行游戏测试、预览渲染、截图或验收，由用户测试。授权模型、Blend/FBX、uasset 和密集关键帧继续保留在本机素材范围，不随公开源码分发。
