# M66 焚骸：当前恢复入口

本目录是制作与接入记录，V01～V23 的各阶段 README 保留当时状态；**当前组合以下表为准**，不能按历史文件中的“尚未制作”判断现在缺项，也不能将旧通过记录视为新修订验收。

原角色路径始终为 `/Game/Monsters/IncineratorBossM66/BP_M66RigPreview`，沿用 F6 的 M66 入口，焚化区第三间房以首领身份生成。玩法、联机和归档范围见 [发布说明](../../Docs/Publication/M66Incineration20261015/README.md)。

| 部分 | 活动版本与入口 |
| --- | --- |
| 用户模型与基础绑定 | [MeshyRigV01](MeshyRigV01/README.md)，保留用户原件、背囊/背孔骨链；原件 SHA-256 在该记录中 |
| 待机、移动与转向 | [LocomotionV02](LocomotionV02/README.md)，原生导航及动画时钟；V05 眼珠与背囊细动 |
| 受击、眩晕、击飞、死亡 | [ReactionsV03](ReactionsV03/README.md)，后续地面恢复采用 V21，尸体采用 V07/V19 |
| 双手权重与下垂组织 | V08 大手连续性 → V09 小手分离 → [ThumbDrapeV10](ThumbDrapeV10/README.md) 拇指与下垂组织；V17 网格继承该绑定 |
| 第一攻击横扫 | [HandContinuityV08](HandContinuityV08/README.md) 动作，V11 战斗数值；不是旧 V04/V06 动作 |
| 握拳砸地 | V13 → V14 握拳 → V15 范围冲击波/2 秒眩晕 → [SlamImpactRhythmV16](SlamImpactRhythmV16/README.md) 快落拳与 0.5 秒停顿 |
| 炉息喷吐及当前网格 | [FurnaceBreathV17](FurnaceBreathV17/README.md)，`FurnaceBreathV17/SK_M66_Furnace_V17`，慢蓄势、快喷吐、停顿收势 |
| 背孔黑烟、声音、权威尸体 | V12 是重建输入；当前使用 [NetworkAudioV19](NetworkAudioV19/README.md) 的烟团历史与事件音效 |
| 裂口弱点 | [CleftWeakpointV20](CleftWeakpointV20/README.md)，本地命中与服务器规则共用 |
| 倒地/起身动画 | [KnockdownGroundV21](KnockdownGroundV21/README.md)，Land 0.9 秒、GetUp 3.2 秒 |
| 网络交接与楼梯支撑 | [RecoveryNetworkV22](RecoveryNetworkV22/README.md) 与 [StairRecoveryV23](StairRecoveryV23/README.md)；V23 最后画面/主客机复查中断，用户已叫停 |
| 死亡物理 | `DeathGroundV07/PA_M66_Surface_V07`，V19 服务器模拟/复制，V23 支撑检测与阻尼修正 |

## 恢复顺序与依赖

先恢复有许可的用户 `Meshy_AI_Character_output (3).glb`（本机副本 `MeshyRigV01/Inputs/M66_user_rig.glb`）、UE/Fab 依赖、既有 M 系列音效与魔法龙息 VolumeV8 R5 供体。模型、声音、纹理、UE 包及密集蒙皮/采样数据不进入公开 Git。

基础读取/绑骨 → V02 移动 → V03 反应 → V04～V10 修形与手部权重 → V11 数值 → V12 黑烟 → V13～V16 砸地 → V17 炉息 → V19 声音/烟团 → V20 弱点 → V21 地面恢复。各阶段脚本会读取前序 `.blend`、导出及元数据，旧版本号不等于废案。按目标阶段 README 的依赖恢复；不要批量重跑所有历史安装脚本，以免旧阶段覆盖当前角色。

M66 原生实现位于 `Source/FPSGAME/Monsters/M66*`。常规构建、脚本导出和 UE 包保存是不同步骤；只保存脚本不表示资产已导入。使用现有工程批次互斥，等待正在运行的编辑器/构建释放，不自动关闭别人的进程或启动交互编辑器。

## 整理与检查边界

废弃 V01/V02 参考图、自动备份、被替换的安装前快照、旧测试用户目录、缓存、DLL 临时宿主和一次性恢复脚本已移入工程 `trash/m66-incineration-retired-20261015/`；[归档摘要](../../Docs/Publication/M66Incineration20261015/archive-manifest.json) 记录数量、路径和散列。实际 Content 资源、活动作者输入及失败日志保留。

V19 的真实主机/在线客机/晚加入状态检查通过，使用 NullRHI/nosound；V22 平地网络交接检查通过。V23 修正前楼梯状态同步通过但姿态不合格；修正后的渲染轮次因系统重启中断，尚未完成画面及主客机复查。源码整理与发布没有重新运行这些检查，后续由用户测试。
