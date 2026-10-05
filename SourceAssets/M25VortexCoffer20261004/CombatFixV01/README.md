# M25 战斗修复 V01

2026-10-05，按用户要求修复撕咬命中与联机击杀奖励；地牢刷新接入留待后续。

- `M25BiteComponent.cpp`：嘴部球形扫掠只收集 Pawn，选择玩家根碰撞体。地面不再抢占最早命中；身体到嘴、嘴到玩家胶囊轴的 Visibility 射线继续处理墙体和障碍遮挡。初始重叠时不再用不可靠的 ImpactPoint 作为遮挡射线终点。
- `M25Damage.cpp`：玩家控制器击杀统一调用 `ColdSteelSkills::AwardKillByOwner`，由公共接口选择主机/单机档案或客机对应的服务器影子档案；沿用一次性死亡结算与奖励去重。
- 保留撕咬 2 倍播放速度、80 cm 接触半径、110 cm 起手距离、伤害和独立冷却；沿用已有魔法、弱点、死亡及 LOD 资产。
- 不修改地牢刷怪器或刷怪池，不新增音效；无蓝图属性或资产改动，无需重新导入。

原源码片段对应的完整文件备份在 `Before/`。构建入口 `build_native.ps1`，后台串行完成 Game/Editor 目标，等待已运行构建和 DLL 占用者自然退出。

当前状态：源码已落盘，Game/Editor Development 两个目标后台构建均成功（退出码 0），正式 EXE/DLL 已生成；构建回执位于 `Records/build_FPSGAME.json` 和 `Records/build_FPSGAMEEditor.json`。未运行游戏、自动测试或验收，由用户体验。

2026-10-05 整理：上文旧备份已移入仓库根 trash/m25-retired-20261005 的同阶段相对目录；逐文件映射见 Docs/AssetArchives/m25-retired-20261005.json。生产源与当前资源保留。
