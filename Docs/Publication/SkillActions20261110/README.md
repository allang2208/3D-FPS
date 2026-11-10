# 连斩、跃击、武器附焰与弓技能恢复材料

本批保存 2026-11-07 至 11-10 的专属实现、共享宿主增量、具体配置与制作配方。完整本机工程位于 `D:/FPS3D/FPSGAME`，当前运行源码仍以工程根目录为准。这里是可审阅的恢复材料，不是第二套开发源码；共享宿主中交织的其他工作没有整文件发布，本批尚未完整集成到公开运行树。

## 内容

| 范围 | 本机当前实现 | 发布入口 |
| --- | --- | --- |
| 连斩 | 双手剑四段；前方普攻范围、每段去重；生命／削韧同倍率；第一下加速、停帧、镜头与四段第三人称共用时钟 | `ChainSlash*`、`RuneSwordChainSlash*`、身体同步补丁、技能配置 |
| 双手锤快速近战 | V8 柄尾前顶，1.30 s，总接触时刻为 28/120 s；动作、镜头、柄尾探针一致 | `WarhammerQuickCombatMotion.h`、`WarhammerQuickCombatMarker.h`、V8 作者配方与消费者摘录 |
| 跃击 | 0.5 s 蓄力；普通地形按 0.75 s 求解，大落差继续物理下落；实际触地触发伤害、镜头冲击及免控解除 | `ProductionLeap*`、`LeapStrike*`、原生移动／控制入口与配置 |
| 灼锋焰甲／星髓 | 原版四层暖色供体，武器局部空间跟随；锤按表面附着、枪绕手、弓附箭；恢复星髓充能蓝焰筛选 | `FlameArmor*`、`HammerFireSurfaces*`、`FPSFlameArmorPresentation.cpp`、`StarMarrowFlames.cpp` 补丁 |
| 元素箭／箭雨 | 火箭复用暖焰；冰箭为寒气及白粒子；箭雨使用普通射箭波形并保留五声错位播放 | `ElementalArrow*`、搭箭／飞行箭补丁、箭雨调度补丁及声音作者配方 |

数值摘录见 [skills.entries.json](Config/skills.entries.json)：连斩 L1–20 每段伤害／削韧 40%→120%、CD 25→15 s、体力 40→60；跃击伤害／削韧 160%→320%、CD 30→20 s、体力 45→65、半径 2.5→4 m、最大水平跳距 9→15 m。两者起手前扣费，释放／直接击杀／同次多杀分别训练，多杀额外经验每次限一次。

## 合并与恢复

1. [source-manifest.json](source-manifest.json) 将每份材料映射到正式源路径。`Source/Source/FPSGAME/...` 是专属实现快照，恢复时去掉最前面的 `Source/`。`Authors/` 下保留原 `SourceAssets/` 或 `Tools/` 路径；脚本依赖这些位置，应按清单还原后使用，不在本目录直接运行。
2. `Integration/*.patch` 基于本轮修改前的真实本机文件，不假定能直接套到公开 HEAD。按 UTF-8、去 BOM、统一 LF 计算 SHA-256：匹配清单的 `after_sha256_lf` 表示已接入；匹配 `before_sha256_lf` 才进行补丁检查与应用。其他散列按当前文件手工合并，不覆盖共享源码。[consumer-excerpts.json](Integration/consumer-excerpts.json) 补充声明、输入、UI、档案冷却、控制入口等消费者；片段带定位上下文，不是完整编译单元。
3. [prerequisites.json](Integration/prerequisites.json) 记录公共基线、直接依赖／共享宿主及本机输入散列。旧公开宿主缺少部分 `ColdSteelStatusModel`、`ProductionToolComponent`、武器组件及联机诊断框架前置，须先合并相应接口。技能目录与快捷栏需注册 `chainSlash`／`leapStrike`；档案迁移至 v32，包含两组冷却字段、服务器校验、拥有者恢复及一次性训练结算。专属实现依赖完整本机前置，不能用本批历史构建结果宣称公开克隆可独立构建。
4. 将两个技能条目按键合入 `Content/ColdSteelData/skills.json`；将 [leap-status.json](Config/leap-status.json) 按 `type=leapControlImmune` 合入状态列表。保留其他技能和状态。已有身体动作入口摘录为 [player-body.routes.json](Config/player-body.routes.json)，使用 `Tools/PlayerBody/config_transaction.py` 逐键合并，不替换整个 `clips`。本轮第一人称动画路径由 `ChainSlashAssets.h`、`WarhammerQuickCombatMotion.h`、`LeapStrikeMotion.h` 持有；第三人称复用现有身体动作并由新分段时钟驱动。
5. 按 [cook-paths.ini](Config/cook-paths.ini) 保留现有显式打包目录及其上级覆盖；其内容只是配置，不表示重新执行过 Cook。按原 `/Game` 路径恢复二进制内容，再按需要进行构建或用户授权的检查。

跃击移动接入还包括原生 `PhysFalling`、`ApplyRootMotionToVelocity`、`ProcessLanded` 覆盖；不能只恢复动画。免控消费者分别覆盖状态公式、失衡、强推、恐惧、抓取、手脑及雾中视觉控制，减速入口保留。实际落地解除视角限制和免控，动画播放结束不能提前替代触地。

## 制作链与本机资产

- 连斩：`ChainSlash20261107` 的握点读取、轨迹／肩根工具、`RootClearance/fit_arms.py`、`author_motion.py`、`save_motion.py`；`Feedback/fit_camera.py` 与 `bake_effects.py` 处理镜头和折射带。需要保留的 `HighlandBroadbladeSweep20261104/VideoFitV3/author_v3.py`、`SwordUppercut20261003/GripRecoveryV15/inputs.json`、实际握姿／拟合数据及参考视频仍在本机。
- 快速近战：`WarhammerQuickReference20261107` 的原生输入、V8 `author_motion.py`、参考镜头求解、柄尾标记与 `save_motion.py`。跃击复用这些原生输入，通过 `LeapStrike20261107/Review/author_leap.py` 和 `save_motion.py` 烘焙连续动作。跃击 `Review/Before/frames-120.json` 是有效作者输入，不能按目录名清理。
- 暖焰：先恢复原版星髓蓝焰及已有流体工具，再运行 `StarMarrowRestore20261108/restore_warm_sword.py` 得到 V11；该脚本仍导入 `FlameArmorSword20261108/install.py` 的共用暖色函数。随后 `FlameArmorAllWeapons20261108/install_all_weapons.py` 生成 V12。锤用 `FlameArmorHammer20261109/bake_surface.py` 和 `install_surface_fire.py`；V13 路径保存的是 V16 内容。`FlameArmorWeaponsReview20261109/repair_random.py`、`repair_visibility.py` 保留后续 CPU 随机和可见度修订。不得运行已归档的 V9/V10 替换当前结构。
- 火／冰箭分别使用 `ElementalArrowWarmFire20261109`、`ElementalArrowColdMist20261109` 配方；保留现有权威伤害和减速。箭雨用 `ArrowRainDescentAudio20261109/prepare.py`、`install.py` 及更新后的 `Tools/Skills/prepare_magic_arrow_rain_sources.py`。当前供体是 `/Game/Weapons/DarkBow20260925/AudioVideoDirect20260926/S_BowVideoDirect_Release`，不是已否定的 MP3。

UE 动画、Niagara／材质、模型／PBR、声音、图标、视频、完整姿态和表面采样不公开上传。需要的原路径主要是 `/Game/Skills/ChainSlash20261107`、`/Game/Weapons/SteelWarhammer20261014/{QuickReferenceV8,LeapStrikeV2}`、`/Game/Skills/FlameArmor20261108`、`/Game/Skills/FlameArmor20261109/HammerSurfaceV13`、星髓原供体与元素箭／箭雨资源。内容目录为本机 F 盘内容仓的联接，本次未移动生产 `Content`。

`ChainSlashCameraKeys.inl`、`WarhammerQuickReferenceCamera.h` 和 `HammerFireSurfaceData.inl` 是参考／几何派生数据，保留本机并记录散列；恢复编译需要这些输入或重新生成。通用流体作者工具、UE Niagara 编辑桥、原生 V9 手模和供体动画也须从完整宿主恢复。作者程序公开不等于素材许可和二进制也公开。

## 归档与证据

[archive-summary.json](archive-summary.json) 记录 34 个文件、2,152,333 字节的归档；逐文件原路径、目标、原因、替代物和 SHA-256 在本机 `trash/SkillActions20261110/manifest.json`。移后已读回散列。内容为被否定的 V9 随机火焰、V10 旧跟随作者链、旧箭雨 MP3 与两份空的保存回执，另有两份多余的发布草稿。旧快速近战 25 文件备份、当前共用材料、有效制作输入和检查证据保留；归档不删除用户外部音效原件。

[audit-summary.json](Evidence/audit-summary.json) 是此前专项检查的最终结果摘录：13 组原生诊断共 937 项、连斩监听／专服与焰甲／星髓监听共四组真实本机 UDP 检查通过；完整本机 Editor／Game 构建成功。首轮失败和夹具修订仍在本机。这些结果未覆盖跃击真实双端位移、完整档案心跳、公网、断线重连或新一轮画面／听感。

本次整理仅核对归档、提交内容、语法、散列、依赖说明与推送范围；没有启动 UE、重建或重跑玩法检查。可复用经验进入工程与个人的技能／魔法、流体特效和调试技能对应章节。
