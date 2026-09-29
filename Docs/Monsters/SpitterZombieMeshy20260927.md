# 毒液僵尸迁移：Meshy 绿色皮肤版

**最新变更 MeleePoisonV15（2026-09-29）：** 三种现有近战动作每次有效命中叠一层共用中毒；保留 V13 随机攻击、V14 距离与死亡布娃娃。仅实际掉血且存活的目标叠毒，闪避/招架/无敌与状态免疫沿用现有规则。源码与正式 DLL 已落盘，常规 Editor 后台构建成功，无需重导动画或蓝图；未启动编辑器或运行测试。详情见 `SourceAssets/SpitterZombieMeshy20260927/MeleePoisonV15/README.md`。以下为历史制作记录。

**最新变更 LibraryAttackV9（2026-09-28）：** 用户确认换成源预览第一种完整 Attack_A，约 3.97 秒原速，后仰→前扑落地→起身；已通过现有编辑器互斥桥导入保存，物理近战窗口改为 0.65–0.78 秒，仍不发射毒液。移动代码改为生成时抽一次、终生固定片段和步幅速度；当前编辑器尚未关闭，这项原生 DLL 更新仍待完成。保存回执与交付边界见 `SourceAssets/SpitterZombieMeshy20260927/LibraryAttackV9/README.md`。下文 BiteV8 为上一版历史记录。

**BiteV8 已接入：** 2026-09-28 用户随后关闭编辑器，常规 Editor 构建返回成功，后台 commandlet 已保存撕咬动画和蓝图近战配置。原生类已移除毒液发射；共享洗牌移动抽取修订也包含在当前构建中。未打开编辑器界面或游戏，未运行测试。

2026-09-27 制作。目标项目 `D:\FPS3D\FPSGAME`。

初版已完成原生角色与毒液弹代码、Editor 构建、Meshy 模型与原生蒙皮、UE 动作重定向、材质制作及资产保存。入口继续为 **F6 → 毒液僵尸 → 召唤**。

**2026-09-28 当前变更：BiteV8 近战撕咬。** 按用户要求取消毒液投射攻击，制作 1.45 秒踏步咬下、侧向撕扯与收势，在 0.53–0.64 秒结算一次物理近战，基础伤害 30。保留四种移动、绿色外观和既有受击控制，接入普通僵尸的近战距离/冷却/命中流程。本轮实际加载新原生类，无需旧 DLL 的吐毒时间兼容措施。保存结果见 `SourceAssets/SpitterZombieMeshy20260927/BiteV8/installation.json`；构建日志为同目录 `build-editor-resume.log`。下文的吐毒合同和 V1–V7 攻击均为历史记录。完整边界见同目录 `README.md`。

**没有运行游戏、PIE、渲染预览或测试；外观、动作、碰撞与战斗效果由用户自行测试。** 保存回执代表资产已落盘，不代表运行验收通过。

## 来源与费用

- 原项目：`E:\无尽轮回\长期备份\2026-7-13-1\game-dev`。读取 `SKILL.md`、`data/enemy-config.json`、`src/entities/enemy-types/spitter-zombie.js` 与 `src/combat/projectile.js`；保留原项目内容。
- 造型参考：用户截图及原项目 `assets/enemies/spitter_zombie/idle-v2.png`。瘦长、驼背、长臂、破布衣；绿色皮肤参考当前突变体。
- 单体制作参考图：`SourceAssets/SpitterZombieMeshy20260927/Inputs/spitter_green_reference.png`，用于 Meshy 输入，不是最终游戏截图。
- Meshy 模型任务：`01a0e352-fa15-7550-98de-108232ae0239`，35 credits。
- Meshy 绑骨任务：`01a0e357-5643-725b-96ca-d38d8878ba70`，5 credits。
- 本次 Meshy 共 **40 credits**，该账户余额记录为 1868 → 1828。没有额外购买 Meshy 动作。任务请求、无密钥回执和下载散列保存在任务目录的 `Meshy` 下。
- 动作来源：项目现有 Mesh2Motion `human-base-animations.glb`、`human-addon-animations.glb`，美术资产 CC0。许可证副本位于任务目录 `Sources/LICENSE-CC0.MD`。吐毒动作与俯卧翻身段本次制作。
- 绿色皮肤使用项目现有 `Tools/MonsterStyle/author_surface.py` 的 mutant 配方和既有皮肤素材库，在新模型自己的 UV 上生成贴图；没有直接错用突变体 UV，也没有覆盖突变体资产。

## 游戏资产

| 内容 | UE 资源路径 |
| --- | --- |
| 角色蓝图 | `/Game/Monsters/SpitterZombie/BP_SpitterZombie` |
| 骨骼网格 | `/Game/Monsters/SpitterZombie/SK_SpitterZombie` |
| 骨架 | `/Game/Monsters/SpitterZombie/SK_SpitterZombie_Skeleton` |
| 物理资产 | `/Game/Monsters/SpitterZombie/SK_SpitterZombie_PhysicsAsset` |
| 绿色材质实例 | `/Game/Monsters/SpitterZombie/Materials/MI_Spitter_MutantGreen` |
| 公共材质父级 | `/Game/Monsters/Shared/InfectedSurfaceV1/M_InfectedSurface_V1` |
| 动作 | `/Game/Monsters/SpitterZombie/Animations/A_Spitter_*` |
| LOD 设置 | `/Game/Monsters/SpitterZombie/LOD_SpitterZombie` |

Meshy 身高设为 1.85 m，保留其 24 根骨骼、原始绑姿与蒙皮；UE 的 FBX 容器另保留 `SpitterRoot`。近景模型约 4.17 万三角面，三个 LOD 档位为原始、45%、16%。皮肤 BaseColor/Normal 上限 2048，ORM/TissueMasks 上限 1024，启用常规纹理流送。

材质与当前突变体 SurfacePolish 共用父级与参数：NormalStrength 0.9、WoundWetness 0.8、DrySpecular 0.25、WetSpecular 0.34、ScabRoughnessBias 0.02，SkinTint `(1,0.985,0.97)`。衣物仍使用衣物区域处理；法线已为 DirectX，UE 不再翻绿通道。

九个动作：Idle 4 s、Walk 1.333 s、Attack 1 s、Death 2 s、Stagger 0.4 s、Dizzy 2.367 s、Hit_Knockback 0.833 s、LayToIdle 1.5 s、ProneToIdle 2.3 s。动作经 UE IK 重定向、原始骨长适配及皮肤接地制作，以 60 fps 导出。原始 Meshy 骨架没有独立手指或下颌骨；本次吐毒表现由脊柱、颈部和头部驱动。

## 行为迁移与三维适配

| 原项目 | UE 接入 |
| --- | --- |
| 5 级、普通、基础生命 120 | 保留；运行时继续应用项目共用的生命成长倍率 |
| 力22 / 敏38 / 体20 / 智10 / 感6 / 运5 | 注册到 `MonsterCoreStats`；伤害与经验使用共用公式 |
| 1500 ms 冷却 | 1.5 s，从攻击开始计时 |
| 24 帧攻击，第8帧发射 | 1 s 动作，0.333 s 发射一次；低帧率跨过发射点也仅发一枚 |
| 嘴部喷射，预测目标位置 | `headfront` 骨骼位置发射，按目标速度求拦截点 |
| 100 px/s 行走，270 px/s 弹速，930 px 射程 | 三维初始调参为 130 cm/s、350 cm/s、1200 cm；不是逐像素映射 |
| 法术伤害，命中中毒 | 法术伤害类型；造成伤害且目标存活时追加一层共用中毒 |
| 攻击停步、受击中断 | 沿用共用行为树和战斗占用；不执行护士近战伤害 |
| 死亡清除攻击 | 取消未发射攻击并销毁本角色飞行中的毒液弹 |

接入现有生命条名称、F6 开发召唤、伤害属性、受击/眩晕、击飞倒地、仰卧与俯卧起身、死亡布娃娃与尸体预算。复用现有毒液材质、拖尾、命中特效和吐液音效。弹体扫掠、最大距离与存活期独立于视觉效果。

原项目的二维环绕逻辑、无限追踪距离和地图入侵配置未直接照搬；此版本使用 UE 共用寻路/追踪，警戒半径 1600 cm。未修改墓碑召唤、矿洞敌群或世界随机生成表；本次提供的可用入口为 F6 独立角色。

## 源码与制作记录

- 新增：`Monsters/SpitterZombie.h/.cpp`、`Monsters/SpitterVenomProjectile.h/.cpp`、`Monsters/SpitterPhysics.cpp`。
- 共用接点：`MonsterCombatComponent.cpp`、`MonsterCoreStats.cpp`、`HumanoidKnockdownComponent.cpp`、`DevelopmentSpawnComponent.cpp`。
- 常规构建遇到既有 LMG include 插入顺序冲突，对 `FPSGAMECharacter.cpp`、`M4TacticalSprintComponent.cpp`、`PKMBipodComponent.cpp` 只将各自头文件移回首位。
- `SourceAssets/SpitterZombieMeshy20260927` 保存 Meshy 原始文件、制作参考、Blender 工程、UE IK 交换文件、导入脚本及动作/资产回执。
- `build-editor.log`：正式 `FPSGAMEEditor Win64 Development` 构建 Succeeded。
- `ue_installation.json`、`production_status.json`：蓝图、网格、物理、贴图和九个动画已保存。
- 最终保存通过已运行编辑器的互斥桥执行；本任务没有打开新编辑器、关闭他人进程或发送跨会话消息。

需要继续制作时先读取这些回执；Meshy 脚本可恢复已有任务，不应重复付费提交。原生类首次保存蓝图前必须完成常规 DLL 构建；无编辑器时可用 `SPITTER_HEADLESS=1` 加 Python commandlet 执行 `install_final.py`。

## 攻击 V2 修订

根据用户反馈重做僵硬攻击与静止手臂。按实际配置引用的 `v2/attacking.png` 逐帧阅读：4–7 帧挺胸抬手，8 帧吐毒，9 帧前倾伸手，10–15 帧双臂滞后下摆，随后收势。源图真实排布为 6×4；没有使用目录上层旧版大后仰跨步动作替代。

新增 `/Game/Monsters/SpitterZombie/Animations/A_Spitter_AttackV2` 并通过局部导入脚本绑定蓝图。重做骨盆升降、脊柱舒展/前压、头部朝向、双肩、双肘和手腕轨迹；双脚通过离线双骨求解保持支撑，左右手稍作错峰，连续曲线以 120 fps 烘焙。保留 1 秒动作、0.333 秒发射以及原伤害/冷却。没有更改网格、蒙皮或其他八个动作，没有原生代码改动。

源文件、脚本与保存回执在 `SourceAssets/SpitterZombieMeshy20260927/AttackV2`。该目录的原精灵图阅读联系表不是新模型预览。本次未运行游戏或渲染验收，手部调整范围为现有手骨与手腕，不含原骨架没有的独立指骨。

## 攻击 V3：用户要求的大后仰与前扑

V2 被用户反馈为仍然僵硬、缺少后仰再前扑。当时攻击引用更新为 `/Game/Monsters/SpitterZombie/Animations/A_Spitter_AttackV3`，随后手臂部分由下述 V4 替代。此次按用户明确的动作特征使用原目录 `attacking.png` 的后仰与弓步意图，不受 V2 小幅挺胸参考限制。

后仰阶段胸肩和头部退到髋后，双臂后摆；吐毒阶段前脚跨出、骨盆下沉前送、身体前压、双臂向前甩出。使用绝对骨段方向、离线双骨求解和独立手腕跟随，保留 1 秒与 0.333 秒发射的战斗时序。后台导入及蓝图保存已完成；制作记录位于 `SourceAssets/SpitterZombieMeshy20260927/AttackV3`。未启动游戏或做渲染测试。

## 攻击 V4：手臂随身体甩动

用户进一步明确手臂应跟随身体甩动。保留 V3 身体、腿部和头部关键帧，移除前方手部目标，仅重做双肩、双臂和双腕。肩部跟随躯干，悬垂上臂按肩部加速度滞后摆动，小臂与手腕分别延迟约 45 ms、90 ms，肘部保持微屈；收势逐渐回到待机姿态。

离线计算后以 120 fps 烘焙，不增加游戏运行时物理，保留 1 秒攻击与 0.333 秒发射。后台 Python commandlet 已导入 `/Game/Monsters/SpitterZombie/Animations/A_Spitter_AttackV4` 并保存蓝图引用；源工程、导出与回执位于 `SourceAssets/SpitterZombieMeshy20260927/AttackV4`。未启动编辑器界面或游戏，未进行渲染或游戏测试。

## 攻击 V5：头颈保持朝向攻击正前方

V4 预览后，用户要求头部和眼睛面朝目标。复制 V4 并仅修改 `neck`、`Head` 两根骨骼的旋转曲线，以脸部 `headfront` 和头顶 `head_end` 标记确定朝向与水平视线。颈部分担反向补偿，头部补足身体后仰或前压产生的角度变化；躯干、腿部及 V4 甩臂曲线保留。

后台导入 `/Game/Monsters/SpitterZombie/Animations/A_Spitter_AttackV5` 并保存蓝图引用，仍为 1 秒、0.333 秒发射。源工程与回执在 `SourceAssets/SpitterZombieMeshy20260927/AttackV5`。此版稳定的是角色攻击正前方的视线，沿用攻击开始时朝向目标的既有逻辑；未新增移动目标或高低差的动态头部追踪。未启动游戏、未渲染 V5 或执行测试。

## 攻击 V6：全身发力、承重与余动

用户反馈机械感并授权继续优化。从 Idle 重编骨盆、三段脊柱与肩臂，腰胸的后仰和前扑转折依次错开；前脚先跨出落地、后脚围绕脚趾接地点抬跟，前膝随骨盆下降承重。上臂、小臂、手腕分别制作拖后、追上、过冲和回落，左右臂具有不同摆幅与时序，手部没有前推到达目标。

头颈改为看向制作坐标 `(0, -4, 1.60)` 米的目标点，俯仰随身体位置变化，保留轻微侧倾。此为动画烘焙目标，不是新的运行时目标追踪功能。攻击仍为 1 秒、120 fps，0.333 秒吐毒；其余动作、网格、蒙皮、材质和战斗数值保持。

`/Game/Monsters/SpitterZombie/Animations/A_Spitter_AttackV6` 和角色蓝图引用当时已通过后台 Python commandlet 保存，记录位于 `SourceAssets/SpitterZombieMeshy20260927/AttackV6`。执行导入时编辑器已不在运行，因此使用后台 commandlet；本任务未主动关闭或打开编辑器界面。后续由下述 V7 替代，旧版制作源保留。未制作 V6 预览、未运行游戏或执行测试；用户随后反馈移动及攻击仍不达标。

## LibraryMotionV7：四种随机移动与动作库攻击适配

2026-09-28，用户认可源动作筛选方向，并要求 Walk A/B/C、Run A 全部加入随机移动。已完成原生 UE IK 重定向、原 Meshy 骨长适配、移动循环和接地制作，以及五个动画和蓝图引用保存。原生 Editor DLL 常规构建成功。初版每次进入移动状态独立随机，允许重复；用户随后反馈多个实例、反复停走仍看起来相同。修订为同世界同类角色共享随机洗牌池，每轮四种各抽一次，轮次交界不重复，并记录所选与实际播放片段。连续移动保持该片段，实际移动速度仍为 130 cm/s。

攻击 `A_Spitter_AttackV7` 以 Attack_A 前半段的躯干运动为基础，参考 Attack_D 的踏步与站立收势，将扑倒改为站立前送和腿部支撑。原主动挥臂改成肩部带动的离线惯性摆动，头颈保留面向制作目标的补偿。1 秒总长、1/3 秒发射、伤害与控制状态合同保持。没有新增运行时头部追踪功能。

完整制作说明与重建顺序见 `SourceAssets/SpitterZombieMeshy20260927/LibraryMotionV7/README.md`，实际保存回执为同目录 `installation.json`。后台制作及构建后，接入时发现用户已打开编辑器并运行 PIE；结束 PIE 后经现有互斥桥导入、保存，没有关闭或重启编辑器，没有重新运行游戏。本轮未生成 V7 预览，未运行游戏测试，效果交由用户自行查看。
