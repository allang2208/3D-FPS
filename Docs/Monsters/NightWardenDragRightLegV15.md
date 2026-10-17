# 守寝者 V15：100STYLE 拖右腿移动（2026-10-17）

> 历史制作记录；2026-10-17 当前 V18 移动仍被用户否定并转待办。旧版本源/资产可能已归档，恢复位置与当前状态以 [收尾记录](../Publication/NightWarden20261017/README.md) 为准。

> 2026-10-17 用户已否定本套移动，活动蓝图现已改用 [V16 前倾行走](NightWardenBentForwardV16.md)。下文保留 V15 制作和保存记录，V15 不作为已认可动作模板。

用户选定 `DragRightLeg_FW`。当前制作使用原作者的 100STYLE 动捕作为独立动作源，重定向到 V14 裸身模型的原有骨架，保留左手修复、现有待机和百目挥击。

## 动作来源

- 数据集：100STYLE，Ian Mason、Sebastian Starke、Taku Komura，2022。
- 原作者页面：https://www.ianxmason.com/100style/
- 原始文件：`SourceAssets/NightWarden20261015/MovementCandidates20261017/DragRightLeg_FW.bvh`。
- 授权：CC BY 4.0。署名与许可副本在 `SourceAssets/NightWarden20261015/V15DragRightLeg/Source/`。
- 仅使用原始骨骼动作；供 UE 导入的骨骼标记网格由本地制作，不使用 Geno 角色模型。

## 制作范围

原动捕为 60 FPS、11803 帧，包含行走和转向。按原作者 `Frame_Cuts.csv` 的有效区间，从源文件零起点第 1731 至 1817 帧截取一个完整直行周期：87 个采样点，约 1.433 秒。源步幅约 75.05 cm，源周期平均速度约 52.36 cm/s。

使用完整原动作的左右差异，不镜像健康腿来生成拖行腿。先经 UE 原生 IK Rig / IK Retargeter 映射脊柱、头颈、锁骨、手臂和双腿，再针对原脚底表面制作接地与循环。右脚属于有意滑动的拖行脚，步速拟合使用左支撑脚；角色移动继续由现有 AI 和 CharacterMovement 控制。

## 当前进度

源周期 `.blend`、供体 FBX、UE 原生重定向资产、V14 身体上的完整接地修形源文件、最终动画和原 `BP_NightWarden` 均已保存。`V15DragRightLeg/Records/ue_delivery.json` 中 `complete=true`；后台导入命令退出码为 0。没有启动编辑器、试玩或验收渲染。

完成体型适配后，周期仍为 87 个采样点、约 1.433 秒；按左脚支撑拟合的步速为 51.2948 cm/s。已同步更新 `SourceWalkSpeed`、`WalkSpeed` 和移动组件 `MaxWalkSpeed`，原有实际速度驱动步频逻辑继续使用。候选源为 `V15DragRightLeg/Authoring/NightWarden_DragRightLeg_V15.blend`，动画轨道为 `V15DragRightLeg/Motion/drag_keys.json`。

最终动画：`/Game/Monsters/NightWarden/V07WaistStride/DragRightLegV15/Animations/A_NightWarden_DragRightLeg_V15`。活动入口仍为 `/Game/Monsters/NightWarden/BP_NightWarden`；V14 裸身与左手修复、V08 待机、V12 百目挥击和 Yaw 100 度/秒的转身设置保留。可从 F6 重新生成守寝者查看候选，实机表现待用户确认。

重建入口：

1. `Scripts/prepare_drag_stride_v15.py`：原 BVH 选段与供体制作。
2. `Scripts/v15_background.ps1 -Stage Retarget`：导入供体并保存 UE 原生重定向输出。
3. `Scripts/author_drag_stride_v15.py`：V14 身体接地、去平移与循环烘焙。
4. `Scripts/v15_background.ps1 -Stage Install`：保存新动画并同步蓝图中的步速基准及实际移速。

上述脚本均位于 `SourceAssets/NightWarden20261015/Scripts/`。不启动编辑器、试玩或渲染；制作与资产保存不代表用户已认可视觉效果。
