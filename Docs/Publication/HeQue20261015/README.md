# 合阙制作、最终首领接入与源码发布

本轮保留现有合阙模型与骨架，公开五类招式、承重移动、控制状态、悬心弱点、原创制作/导入工具和可复用技能记录。完整本机工程已接入废弃设施最终房间；公共源码切片与仍需其他框架前置的恢复补丁分开保存。

## 当前交付与验证边界

- 正式角色为 `/Game/Monsters/HeQue/BP_HeQue`，F6 稳定 ID 为 `HeQue`。随机地牢终末泵机大厅使用该角色，目标依次为击败合阙、成功搜刮宝箱、传送离开。
- 当前组合：RigV01 活体、WeightyMoveV02 移动、SideCrushV03 踢击、HeavyClampV02 快夹、RiftPressureV02 双发空气炮、PsychicV01 动作搭配 PsychicWaveV02 特效、JumpSlamV02 蓄力/特效搭配 CombatV03 腾空/下砸/收势、KnockdownV02、SoftDeathV02 连续软体。
- 踢击 10 米、撞不可行走障碍眩晕 2 秒；夹击实际扣血后眩晕 2 秒；跳砸实际扣血后致残 5 秒。精神波 CD 30 秒、转速 120°/秒、标准跳高 210 cm、空气炮 48 米，心脏真实 `HQ_CoreSwing` 受击面为弱点。
- 本机正式玩法修复进入 2026-10-15 23:17 的 Editor / Game 构建；地图备用库签名修复已在 22:56 保存。首次眩晕组件、复活后的输入锁/恐惧释放、服务器弱点接触复核、最终首领奖励零值遗漏和地图误预加载均有相应修复记录。
- 历史控制状态主客机普通网络与模拟延迟/丢包用例通过；默认预加载下客机重新载入正式地牢也已成功。完整地牢通关、真实宝箱并发交易、队伍返程及所有存档层一致性未跑完，用户明确改为自行测试。本次整理不重复游戏测试。
- 无渲染进程的预热兼容分支最后仅写入源码，尚未构建，保留在接入补丁中；不把它描述成已通过。公开切片没有在干净检出中独立编译。

详细记录见 [本机最终流程记录](../../Monsters/heque-dungeon-e2e-20261015.md)、[控制恢复记录](../../Monsters/heque-control-edge-audit-20261015.md) 和 [联机修改范围](../../Monsters/heque-network-audit-20261015.md)。

## 公开代码与依赖补丁

合阙自身运行代码、原生击退和控制清除、普通怪物公共入口的合阙分支、地图预加载排除与原创作者配方直接进入源目录。共享文件按本轮差异块暂存，保留工作区内其他怪物、武器、食物、地牢性能和档案框架修改。

`final-room-and-audits.patch` 保存 25 个路径的最终房间接入和自动化源代码，`integration-overlay.json` 列出每个目标的前置/结果 SHA-256。其依赖当前本机尚未公开的区域遭遇、共享进度、搜索容器和相关追踪接口；不能直接对公开 main 盲目套用或宣称公开源码已经能完整编译。

恢复时先取得并整合对应框架前置，对每个补丁目标核对其声明的前置内容，再审查套用差异。`new own source` 项为本任务独立新文件；其他项的前置可能是 HEAD，也可能是本机框架移除合阙增量后的内容，以逐文件散列为准。当前完整宿主已包含这些代码，不应再次应用补丁。

`published-files.json` 是本次精确发布清单，排除了日志、存档、机器状态、原模型和引擎资产。该清单不包含自身，避免递归散列。

## 归档与保留

46 个文件、233,361,252 字节已移动到本机 `trash/heque-retired-20261015/`，逐文件移动前后 SHA-256 一致。包括旧独立刚性链条尸体的作者/安装脚本、初版源码生成器、已完成的一次性关闭编辑器脚本、旧 Before 备份和有对应当前 Blend 的自动备份。恢复原路径与原因见 [归档清单](archive-manifest.json)；旧文档中的 Before/脚本路径可按此表追溯。

当前 Content、活体母版、合法原输入、混合版本重建依赖和失败证据保留原位。旧版本不等于废案：新版踢击/重夹/跳砸仍读取旧作者函数或运动记录，SoftDeathV02 仍读取旧 cage 做重心漂移对照，不能整目录搬走。运行中的编辑器和未保存图标没有被修改。

## 本机资产恢复边界

用户提供的 Meshy GLB、其模型/纹理派生物、密集蒙皮/动画采样、Blend/FBX、WAV、UE 包、自动化存档和构建产物未取得公开再分发核准，全部留本机。原创 HLSL 和作者代码可公开；它们不替代所需模型与合法资源。

制作工具读取 `SourceAssets/HeQueBoss20261014` 中保留的相应输入与记录，不是仅靠 Git 即可重建的素材包。角色原生类必须先完成常规构建，再执行导入；生成了新的时序头文件时，再做对应必要构建。后台导入和保存与用户运行验收分别记录。

| 交付部分 | 保留的制作入口 | 最终导入入口 |
|---|---|---|
| 活体骨架/基础动作 | `read_source.py`、`map_regions.py`、`author_rig_motion.py` | `install.py` |
| 承重移动 | `author_weighty_move_v02.py` | `install_weighty_move_v02.py` |
| 踢击与 AOE | `author_kick_impact_v03.py`、`author_kick_audio_v03.py`，保留早期函数/运动记录依赖 | `install_kick_impact_v03.py` |
| 快夹与空气炮射程 | `author_fast_clamp_v02.py`、`author_fast_clamp_audio_v02.py` | `install_fast_clamp_v02.py` |
| 空气炮表现 | `author_rift_pressure_v02.py`、`author_rift_audio_v02.py` | `install_rift_pressure_v02.py` |
| 悬心动作/恐惧与新版波前 | `author_psychic_v01.py`、`author_psychic_audio_v01.py`，再制作 V02 材质/壳体 | `install_psychic_v01.py`，再 `install_psychic_wave_v02.py` |
| 跳砸与战斗 V03 | `author_jump_slam_v02.py`、`author_jump_audio_v02.py`，再 `author_jump_slam_v03.py` | `install_jump_slam_v02.py`，再 `install_combat_v03.py` |
| 击飞/落地/起身 | `author_knockdown_v02.py` | `install_knockdown_v02.py` |
| 连续软体尸体 | `prepare_corpse_v02.py`、`author_corpse_v02.py` | `install_corpse_v02.py` |

自动化工具仅保留为明确请求后的诊断入口；当前用户测试入口是 F6 合阙，完整流程使用新生成的一轮废弃设施地牢。
