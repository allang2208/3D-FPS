# 巫婆移动时双脚穿裙修复（2026-10-03）

用户确认：双脚穿出裙身在正常移动时就会发生。本轮针对行走姿态处理。

## 原模型和动画对照

- 活体仍引用 `/Game/Monsters/WitchRebuilt/SK_WitchRebuilt`，原版 LowerDrape07、UpperDrape07 布料资产继续使用。
- 对照原 `WitchRebuilt_Master.blend`、`WitchRebuilt_Walk.blend` 与独立的 `WitchRebuilt_CorpseFollow.blend`。原裙身有 14767 个顶点，原版裙身权重绑定 pelvis；CorpseFollow 的裙身改为多腿骨权重，它是独立的尸体网格。
- 原版步行片段的抬脚位移可以超过裙身前后范围。源文件参考腿长约 87.38 cm，裙摆最低点约在骨盆下方 89.13 cm，前后范围约为 +17.18/-29.02 cm。
- 现有长袍腿部节点此前只在起身阶段启用，且位于步幅、地面与腿部 IK 之前。正常行走没有最终的长袍范围约束。

以上是文件和引用对照，不是本轮运行画面的验收结论。对照记录位于 `SourceAssets/WitchLegRestore20261003/Receipts/`。

## 实现

修改 `WitchRecoveryLegNode.h/.cpp` 和 `WitchRebuiltAnimInstance.cpp`：

- 正常行走启用现有长袍腿部节点，并按 WalkAlpha 混合。
- 节点移至步幅、FootPlacement 和 LegIK 之后，使最终输出的腿部姿态符合裙身范围。
- 保留原步行片段、脚部旋转和垂直抬落。脚趾高于裙摆时，依据原裙身尺寸渐进收回越界的前后位移，同时限制横向跨出或交叉。脚趾落在裙摆以下时，允许露出原有脚部。
- 起身仍使用原来的恢复混合与接地分支；倒地和死亡不启用行走约束。

本轮没有改写模型、动画或布料资产。原版资产不需要重新导入。之前的尸体物理与法杖碰撞修复保持原有实现。

## 构建与交付

源码备份：`SourceAssets/WitchLegRestore20261003/Before/`。

构建回执：`SourceAssets/WitchLegRestore20261003/Receipts/delivery.json`。Game 与 Editor 常规构建均已成功，日志分别为 `Saved/BuildGame/witch-walking-leg-restore-20261003-014505.log`（45.40 秒）与 `Saved/BuildEditor/build-20261003-014806.log`（11.02 秒）。Editor 构建在用户保存并关闭 UE 后，通过 `Tools/Build/Build-Editor.ps1` 完成，标准 `UnrealEditor-FPSGAME.dll` 已更新。

本轮未启动编辑器或游戏，未进行运行测试、截图或渲染验收，交由用户测试移动时的裙摆与脚部表现。
