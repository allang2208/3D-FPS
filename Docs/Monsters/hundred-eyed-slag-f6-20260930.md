# 百目炉渣：F6 怪物生成接入

当前 F6 默认引用已升级为 `/Game/Monsters/HundredEyedSlag/PolishV2` 网格和 Run/Move/Death 动作，使用修复后的皮肤和专门拟合的物理资产。下面为初版接入记录；修订完成记录见 [V2 修订](hundred-eyed-slag-polish-20260930.md)。

用户指定的 Meshy V2 模型、专用四肢骨架和原创动作沿用既有制作结果。资产已通过正在运行的编辑器桥实际导入并保存；没有启动新编辑器、修改关卡、运行游戏或验收渲染。

## F6 入口

交互开发工具 → 怪物生成 → 百目炉渣。稳定 ID 为 `HundredEyedSlag`，角色类型为 `/Script/FPSGAME.HundredEyedSlagMonster`，生成落脚半径 100 cm。沿用面板现有数量、距离、导航落脚检测、面向玩家与清理功能。

角色胶囊半径 70 cm、半高 70 cm，使用现有 PoisonMaggot SupportedAgent（70/140/40 cm），不更改原有导航掩码或新增重复规格。模型实际长约 1.42 m、宽约 1.25 m、高约 1.2 m，模型组件朝 +X，根落在地面。

## 实际保存的资产

`/Game/Monsters/HundredEyedSlag/V1` 包含骨骼模型、Skeleton、自动生成的 PhysicsAsset、Substrate PBR 材质、四张 Meshy 原始纹理和 16 条 AnimSequence。制作回执位于 `SourceAssets/HundredEyedSlagMeshy20260930/ue_installation.json`。

贴图保留原始分辨率与流送；原法线贴图按 OpenGL 来源翻转绿色通道。保留原始 2,896,776 三角面的拓扑，未主动减面或生成 LOD。这一版本尚未测量多只怪物的运行成本。

角色直接引用已保存资产并复用 `BP_MonsterAIController` 的行为树，通过 `UMonsterCombatComponent` 接入血条名称、索敌、追击、归巢回血、攻击、技能眩晕、弹反、破韧与防御/经验/金币公式。不存在依赖新角色类型的已保存蓝图或关卡。

## 动作与战斗

| 行为 | 动作与时序 |
|---|---|
| 待机/归巢/追击 | Idle / Move / Run；归巢 39 cm/s，追击 91 cm/s，移动速率驱动动作播放速率 |
| 右臂横扫 | AttackSweep_R；0.54–0.73 s，手掌骨扫掠，每目标一次物理伤害 |
| 右臂重砸 | AttackSlam_R；0.84–1.00 s，手掌骨扫掠，1.4 倍物理伤害 |
| 灰烬爆发 | SpecialAshBurst；1.00 s 释放，300 cm 范围魔法伤害，逐目标遮挡检测，8 s 冷却 |
| 冲撞 | SpecialCharge；0.55–1.25 s 以 210 cm/s 向锁定方向移动，0.56–1.24 s 命中，碰墙停止，10 s 冷却 |
| 受击/破韧 | HitFront / HitLeft / HitRight / Stagger；沿用共享韧性闸门，未破韧命中不自行打断 |
| 眩晕 | StunEnter → StunLoop → StunExit；使用共享技能控制期限，冻结/石化保持姿态 |
| 死亡 | Death；片段 60% 交接已保存物理资产，死亡后取消攻击、奖励一次，15 s 回收 |

SpecialCharge_RM 根运动变体已作为第 16 条动作导入，当前角色使用原地冲撞动作与角色移动，避免双重位移。灰烬爆发已接动画与伤害，未新增 Niagara 灰烬特效或音效。

初始值：8 级精英，生命 1800、物理攻击 42、魔法攻击 35、防御 55、魔防 40。韧性使用项目当前 Heavy × Elite 基准；经验基础 300，奖励由共享品阶/等级规则结算。可在类默认值或派生蓝图中调整。

## 构建与未测试范围

接入源码位于 `Source/FPSGAME/Monsters/HundredEyedSlagMonster.*`，共享注册位于 `MonsterCombatComponent.cpp`、`MonsterParryReaction.cpp`、`MonsterMeleeKnockback.cpp`、`MonsterCoreStats.cpp`，F6 条目位于 `Development/DevelopmentSpawnComponent.cpp`。

`SourceAssets/HundredEyedSlagMeshy20260930/Build-Background.ps1` 等待本工程二进制占用结束后调用项目常规 Editor 构建；不会关闭其他进程或启动 UE。只有生成 `build_receipt.json` 并完成常规链接后，新角色类型才能随下次启动持久加载。本次常规 FPSGAMEEditor Win64 Development 构建已成功，日志为 `Saved/BuildEditor/build-20260930-153554.log`；阶段见 `production_status.json`。编辑器保持关闭，没有使用热补丁代替常规构建。

本次没有进行运行测试、动画验收、碰撞验收、导航验收或性能测量，交由用户测试。
