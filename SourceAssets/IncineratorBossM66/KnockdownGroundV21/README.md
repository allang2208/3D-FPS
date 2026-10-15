# M66 V21：击飞落地与起身接地修正

后续 [V22 联机复查](../RecoveryNetworkV22/README.md) 保留本版两段动画，并修复客机死亡等待期间的姿态回跳、网格放置与网络平滑缓存不同步；实际三进程结果见 V22 记录。

2026-10-15，针对用户报告的击飞倒地、起身浮空进行定向排查与修订。

18:21 后台 commandlet 返回 0，两段新动画及原角色蓝图均已保存。导入后的压缩姿态比较已完成，详见 `Records/import.json`、`Records/compressed-support.json` 与 `Records/delivery_receipt.json`。

## 原因

原角色仍引用 ReactionsV03 的落地与起身动作。旧动作按全模型最低顶点接地，最低点主要在脚尖；倒地时躯干仍高于地面，起身延续了这个悬空姿态。当前 V17 网格与原 V01 网格应用旧动作均有相同问题。

UE 源数据及压缩/重定向后的骨骼采样均保留 M66_Root 的高度变化，未发现导入时丢失位移。M66_Rig 是导入容器根骨，锁定它不等于锁定其下的 M66_Root。运行时倒地期间已禁用站立脚部接地修正，未将此次问题归因于站立 IK。

## 修改

- 使用当前 FurnaceBreathV17 完整骨架制作两段独立 V21 动画，不重导网格、不改变权重。
- 落地末段改为躯干侧倒并获得表面支撑；起身从同一倒地姿势开始。
- 巨掌在身体侧面撑地，解算完整肩、肘、腕链及其辅助骨后代，保留骨长。
- 起身中段将双脚逐渐放平并恢复承重，避免只用一个脚尖或脚跟支撑。
- 保留 Landing 0.90 s、GetUp 3.20 s；不更改服务器反应阶段、控制持续时间或主客机统一动画时钟。
- 仅将原 BP_M66RigPreview 的 land_clip、get_up_clip 指向新资产。模型、空中、死亡、攻击、物理资产、弱点及烟雾配置沿用现有版本。

## 文件与接入

- 制作源：`Authoring/M66_recovery_v21.blend`
- 导出：`Export/A_M66_Landing_V21.fbx`、`Export/A_M66_GetUp_V21.fbx`
- 目标资产：`/Game/Monsters/IncineratorBossM66/KnockdownGroundV21/A_M66_Landing_V21`、`A_M66_GetUp_V21`
- 原角色：`/Game/Monsters/IncineratorBossM66/BP_M66RigPreview`
- 修改前蓝图备份：`Before/BP_M66RigPreview.uasset`（实际导入时保存）；旧 V03 动画保留。

实际接入状态以 `Records/import.json` 为准，成功状态为 `animations_and_original_character_saved`。本轮没有原生代码修改，无需构建新 DLL。

## 定向排查证据

- `Records/active-assets.json`：修订前实际资产引用、源/压缩姿态。
- `Records/source-support.json`：旧 V01/V17 源网格与 V03 姿态支撑高度。
- `Records/animation_manifest.json`：新动作时长、帧数和源表面支撑采样。
- `Records/recovery-00.png`、`recovery-06.png`、`recovery-14.png`、`recovery-26.png`：Blender 中立材质诊断图，非游戏截图。
- `Records/compressed-support.json`：导入后使用 UE 压缩姿态驱动当前源蒙皮表面的定向比较。

同一当前网格、同一平面参考下的压缩姿态结果：倒地末帧的躯干/背囊支撑表面离地从约 44.48 cm 降至约 0.001 cm；起身 1.60 s 时原先左脚离地约 30.79 cm，修正后约 0.17 cm，右脚保持接地。该结果不包含游戏中的胶囊地板间隙、地形坡度或动画切换混合。

以上为动作与导入数据检查。未启动游戏、PIE 或主客机实测，实际地形、受控连击和联机表现由用户体验。
