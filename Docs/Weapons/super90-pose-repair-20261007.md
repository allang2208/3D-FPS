# M4 Super90 待机与 ADS 姿态修复

后续用户截图指出左臂在腰射和 ADS 下仍有拧折；对应的蒙皮迁移问题另见 [左臂与衣袖蒙皮修复](super90-arm-skin-repair-20261007.md)。

用户反馈：待机看不到枪，ADS 时两只手分离。2026-10-06 的导入与编译完成不代表该版画面已通过验收。

## 根因与修改

原制作脚本对新建零长度 EditBone 先指定矩阵再指定长度，实际保存的部分骨轴与脚本记录的期望矩阵不同。烘焙仍使用期望参考矩阵，导致姿态的局部变换基底错误。读取现有 Blender 源及 UE 保存姿态后，错误已出现在 Blender 烘焙动作中；压缩后的 UE 动作也保留了它。错误待机中手腕相距约 117 cm，远大于作者源动作的持握距离。

修复保留现有网格、实际参考骨架及 56 份装备适配，不更换绑定。每个骨骼的目标姿态按以下关系转换，再基于实际父子参考矩阵烘焙：

`目标姿态 = 归一化源姿态 × 期望参考矩阵的逆 × 实际参考矩阵`

因此保留作者的网格形变与机械接触，同时适配已保存的原生骨轴。重制范围为原有 11 段动画，不修改装填事务、弹药、伤害或动作时长。原制作入口 `author_super90.py` 同步修正；专项入口为 `SourceAssets/Super90PoseRepair20261007/repair_animation_basis.py`。

该原生绑定中，枪身物理上方向是 Blender `WPN_root` 的局部 +Y；经过 FBX 坐标转换，在 UE 中对应局部 -Y。腰射标定对 Super90 使用 UE 的 -Y 轴，共用 M4 标尺仍使用自己的局部 Z 轴。ADS 也从同一帧枪根读取相同上方向，避免瞄线对齐后滚转失控。方向修正作用于整个枪械与双臂组件。

## 交付记录

- 可编辑源：`SourceAssets/BenelliM4Super9020261006/Super90_Gameplay_Editable.blend`。
- 修复前备份：`SourceAssets/Super90PoseRepair20261007/Super90_BeforePoseRepair.blend`。
- 动作导出记录：`SourceAssets/Super90PoseRepair20261007/authoring_receipt.json`。
- UE 资产保存记录：`SourceAssets/Super90PoseRepair20261007/import_receipt.json`，仅在实际保存后追加。
- 本次不启动游戏、不渲染、不进行运行或视觉验收；最终画面由用户测试。

已完成：2026-10-07 00:30 后台 `FPSGAMEEditor Win64 Development` 构建成功，返回 `Target is up to date` / `Result: Succeeded`；00:30:59 commandlet 完成 11 段动画重导入与保存。没有重新打开图形编辑器，也没有启动游戏测试。

构建日志：`Saved/BuildEditor/build-20261007-003038.log`。导入日志：`SourceAssets/Super90PoseRepair20261007/import_commandlet.log`。实际制作进度及交付回执分别为同目录 `production_status.log` 和 `delivery_status.json`。这些记录说明构建与资产保存完成，不代表用户视觉验收通过。
