# 守寝者 V16：100STYLE 前倾行走（2026-10-17）

> 历史制作记录；2026-10-17 当前 V18 移动仍被用户否定并转待办。旧版本源/资产可能已归档，恢复位置与当前状态以 [收尾记录](../Publication/NightWarden20261017/README.md) 为准。

> 用户随后通过截图否定本版：动作更加僵硬，像鞠躬走路。替换制作见 [V17 Rampage 双足重步](NightWardenRampageBipedV17.md)。下文仅为 V16 的历史制作和保存记录，不能作为已认可动作模板。

用户否定 V15 拖右腿移动，要求换一套。本轮选用 `BentForward_FW`，保留原动捕的躯干前倾、摆臂和双脚交替支撑，适配现有 V14 裸身与左手修复骨架。

## 来源与制作

动作来自 100STYLE，Ian Mason、Sebastian Starke、Taku Komura（2022），原作者页面为 https://www.ianxmason.com/100style/ 。使用本地原始 `MovementCandidates20261017/BentForward_FW.bvh`；CC BY 4.0 许可及署名副本位于 `V16BentForward/Source/`。供体骨骼标记网格为本地制作。

从原作者有效区间 `[387, 6766]` 中，选择零起点第 5889 至 5957 帧：60 FPS、69 个采样点、约 1.133 秒。源周期位移约 96.33 cm，平均速度约 84.99 cm/s。经过 UE 原生 IK 链重定向后，制作原地循环和原脚底表面的接地修形；最终游戏步速使用双脚支撑段的向后速度拟合。

制作保留四层输入：原 BVH、选段供体、UE 原生重定向结果、原身体上的适配成品。修改范围仅为移动动画及对应速度，现有裸身、左手修复、待机、百目挥击与转身逻辑沿用。

## 交付状态

源周期、供体 FBX、UE 原生重定向资产、身体适配制作源、最终动画和原 `BP_NightWarden` 均已保存。`SourceAssets/NightWarden20261015/V16BentForward/Records/ue_delivery.json` 中 `complete=true`；重定向与最终安装的后台命令均以退出码 0 完成。

最终周期为 69 个采样点、约 1.133 秒。双脚支撑速度拟合得到 81.5672 cm/s，已同步到 `SourceWalkSpeed`、`WalkSpeed` 和移动组件 `MaxWalkSpeed`；现有按实际移动速度调整步频的逻辑继续使用。原裸身与左手修复、V08 待机、V12 百目挥击以及 Yaw 100 度/秒的转身设置保留。

活动蓝图现已从 V15 拖右腿动画切换到 V16 前倾行走；替换前蓝图备份为 `V16BentForward/Records/BP_NightWarden.before_v16.uasset`。用户可在 F6 的原守寝者入口重新生成角色体验。

没有启动游戏或执行画面测试，最终效果交由用户确认。

## 重建入口

脚本位于 `SourceAssets/NightWarden20261015/Scripts/`：

1. `prepare_bent_stride_v16.py`：选择完整直行周期并导出供体。
2. `v16_background.ps1 -Stage Retarget`：导入并保存 UE 原生重定向。
3. `author_bent_stride_v16.py`：在原身体上制作接地、循环及双脚支撑速度。
4. `v16_background.ps1 -Stage Install`：保存独立动画并更新原 `BP_NightWarden`。

独立动画路径为 `/Game/Monsters/NightWarden/V07WaistStride/BentForwardV16/Animations/A_NightWarden_BentForward_V16`。制作源位于 `V16BentForward/Authoring/NightWarden_BentForward_V16.blend`；最终保存状态以 `Records/ue_delivery.json` 为准。
