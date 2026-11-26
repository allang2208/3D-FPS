# FPSGAME 代码清理与规则整理报告

初始盘点：2026-11-16；最新更新：2026-11-18（Asia/Shanghai）。工程：`D:/FPS3D/FPSGAME/FPSGAME.uproject`。

本轮第 23–31 批已逐项完成源码清理与保留判定：新增拆分 33 个原长文件，连同第 21 批共 35 个；另 13 个有明确行为、复杂度或连续生成数据的保留理由。必要 Editor 构建已成功（退出码 0），DLL 已重新链接，未测试。最新完整清单见第 33 节及[剩余批次清理记录](code-cleanup-20261116/all-batches-20261117.md)。

以下为第 1–22 批历史摘要，所述范围限制以对应批次为准。

初始盘点及第 1–12 批源码整理已完成。本轮按用户要求将后续第 13–15 批连续实施完毕：Skills 内八处连锁状态、四处法杖专精查询、九处组件模型选择和两处表现清理共用既有入口，修改 21 个已有文件、未新增源码文件。截至第 15 批的实施清单均已落实，详见第 20–23 节。随后按用户选择对 Skills 保留项及 C04 调用链进行定向检查，新增两组优先去重候选，修正三组局部重复的保留理由；两组优先候选已在第 16 批完成源码去重，等待共享构建及项目编辑器退出后，Editor 构建返回 Succeeded、退出码 0，82 个动作完成并重新链接 DLL；检查证据见第 25 节，实施与构建状态见第 26 节。源码与统一汇报已落盘；第 12–15 批的 Editor 构建收尾现已完成：等待共享构建和模块占用退出后独立调用 UBT，返回 Succeeded、退出码 0，目标已是最新，0 个编译/链接动作，详见第 24 节。第 24 节的构建收尾未改源码。火球独立经验缩放、超过 800 行文件、疑似死代码和有效诊断逻辑未动。未新增功能、未测试。

第 17 批继续按用户范围处理 H01–H03：H01 经验公式、H02 回执冷却追时已完成源码去重，仅修改四个已有 Skills 文件；训练提交、完整回执主体及 H03 保留，避免增加私有状态转发。等待共享构建退出后，本批 Editor 构建成功，33 个动作完成、退出码 0，详见第 27 节。

第 18 批继续完成三组局部去重：冰墙命中反馈复用既有通知，火球组件仅复用模型读取并清理重复 include，冰甲/雷迅共用保留 float 运算顺序的冷却倍率公式。共修改五个 Skills 文件，未新增源码文件；Editor 构建成功，14 个动作完成、退出码 0，详见第 28 节。火球独立经验缩放与此前保留状态流程未动。

第 19 批仅把箭雨资源回执的冷却追时接入已有 RemainingCooldown，修改一个 Skills 文件；同型弓系冷却一行公式及冰墙/暴风雪输入判断登记为 R10/R11 保留，不新增包装层。等待共享 Game 构建退出后，本批 Editor 构建成功，4 个动作完成、退出码 0，详见第 29 节。

第 20 批仅将技能树 SpecRank 的手写查找/缺省分支改为已有 FindRef，修改一个 Skills 文件，不新增 helper；技能等级、存档规则与条件文案继续保留。等待后台 UE 进程退出后，Editor 构建成功，6 个动作完成、退出码 0，详见第 30 节。

第 21 批按最新授权纳入两个超长文件、火球独立奖励路径及已列疑似死代码链。两个超长实现已按职责拆成六个小于 800 行的 cpp，火球共用反馈、暴击训练与升级封顶，独立经验缩放和魂奖励不变；C04 因仍有反射入口和状态写入保留。源码与必要 Editor 构建收尾均已完成。此前地编阻塞对应的工作区更新到位后，等待共享 Editor/Game 构建退出，22:36:16–22:36:28 本批收尾返回 Succeeded、退出码 0，目标已是最新，0 个编译/链接动作。本次未新增源码修改，失败历史及最终回执见第 31 节。

第 22 批继续限定 Skills，合并拆分后战斗结算文件中三处相同的影子档案/GI 模型读取，仅修改一个 cpp；既有 NPC/控制权路由差异另行保留。源码与必要 Editor 构建均已完成；等待已有后台 UE 进程退出后，构建返回 Succeeded、退出码 0，4 个动作完成并重新链接 DLL，详见第 32 节。

## 1. 范围与依据

- 工程描述符只声明一个 `FPSGAME` Runtime 模块；下面的八大模块是逻辑职责划分，不代表已新增八个 UE 编译模块。
- `Source/FPSGAME` 共 2,770 个 `.cpp/.h/.inl/.cs` 文件、427,317 行，其中 48 个超过 800 行。统计包括生成动作数据、声明、注释、空行及开发工具，不等同于业务逻辑规模。其下有 22 个直接子目录，另有根层文件。
- 只对上述源码目录作路径和行数统计；语义阅读限定于模块入口、构建声明、任务追踪、旧地牢兼容层、生存计时、法术奖励、技能准备、联机接口及 ColdSteelNet 插件。没有逐文件通读全仓。
- `Tools`、`SourceAssets`、项目插件、配置与着色器按职责列入模块图；除报告明确列出的入口外，未逐个审计其脚本。第三方、历史制作宿主、`unreal`、`trash`、二进制与 Content 资产未作死代码判断。
- 本轮规则正文治理范围是根 `AGENTS.md`、`WORKFLOW.md` 和仓库内 18 个 `skills/*/SKILL.md`。其链接目标做存在性核对；引用文档、`LOCAL-HISTORY.md`、另外四份领域 WORKFLOW 和个人目录维护源没有递归改写，不能称为所有历史规则都已清空。
- 工作区原本存在大量未提交和已暂存修改。以操作前工作文件为基线，逐文件比较后写入，没有使用 HEAD 覆盖、暂存、提交或推送。

## 2. 最多三级的功能模块图

第一级是大模块，第二级是子模块，第三级是职责叶节点。路径用于定位，不要求本轮物理搬目录。

```text
01 玩家与动作
   身体与装备 → 身体呈现 / 穿戴适配 / 第一与第三人称交接
   移动与交互动作 → CMC 预测 / 闪避与翻越 / 推门与接触
02 武器与战斗
   武器执行 → 枪械 / 弓与近战 / 法杖与副手书
   战斗合同 → 伤害与状态 / 资源费用 / 命中查询
   技能魔法 → 目录与成长 / 施法执行 / 资产后台准备
03 敌人与 NPC
   敌人家族 → 人形 / 非人形 / 环境动物
   共用能力 → 行为战术 / 命中韧性 / 动画音画与尸体
   NPC → 角色交互 / 服务入口
04 世界与建造
   地牢 → 布局生成 / 区域遭遇 / 首领与通行目标
   开放世界 → 高度场流送 / 植被与天气接入 / 地貌破坏
   建造与环境 → 构件和工作台实体 / 门窗与道具 / 水体与地表
05 物品与生产生存
   物品 → 掉落与拾取 / 目录实例 / 装备数据
   生产 → 采集工具 / 锻造木工冶炼 / 工作站交易
   生存 → 食物效果 / 饥渴与 SAN / 天气时钟消费
06 界面与任务显示
   UI 基础 → 样式布局 / 输入与焦点 / HUD
   功能页面 → 背包与浮窗 / 工作台与技能树 / 地图与图鉴
   任务显示 → 来源注册 / 稳定 ID 快照 / 追踪反馈
07 联机与持久化
   权威协议 → 命中和施法 / 库存事务 / 回执与序号
   会话与档案 → 登录换图 / 分块传输 / 影子档与恢复
   兼容层 → 旧地牢存档结构 / 击杀奖励去重
08 平台与开发工具
   工程宿主 → 模块启动与 Build.cs / 角色控制门面 / 项目配置
   开发设施 → Commandlet / 诊断采集 / 渲染准备共用工具
   制作管线 → Tools 与 SourceAssets / 规则与交付文档 / 插件适配和第三方依赖
```

路径与源码规模的逐模块归属见 [模块统计](code-cleanup-20261116/module-map.md)。根层角色和天气文件仍是历史门面，后续按行为归入对应功能；计数时统一落在“平台与开发工具”，避免重复计数。

`Plugins/ColdSteelNet` 属联机接入适配；`FPSDeformationResidency` 属渲染基础设施；`AutoFootstep` 属动作音频依赖。`CitySamplePCG`、`Traffic` 是资源适配；已禁用的 `VoxelFree` 保留第三方/历史依赖身份，禁用不等于允许删除。`Source/ThirdParty`、引擎插件及许可文件单列外部依赖，不能按项目业务死代码处理。

依赖方向建议维持“输入/UI → 玩法拥有者 → 共用公式与数据”，联机层包裹权威事务，表现层消费结果。该方向是后续拆分目标，不是本轮已证明无环的依赖图。涉及 UObject 类型、序列化或跨模块导出时，先保留类名、模块名及资源路径，避免仅搬文件导致 Blueprint 或存档失联。

## 3. 先列清理清单

以下清单保留初始范围并更新处置结果。C01 的五个入口已分两批整理，火球分支保留；C02/C03/C05 源码整理与后台构建收尾已完成；C04/C06 及 K01–K03 按边界保留。第 5 批 C07 和第 6 批 C08 共将七个模型入口的暴击修炼公式收拢至同一 helper。第 7 批 C09 统一五个四项训练入口，第 8 批 C10 收拢三项公共计算，第 9 批 C11 收拢八处进度读取，第 10 批 C12 收拢五处玩家命中批次计数，第 11 批 C13/C14 收拢六处命中反馈与三处奖励表合并；以上第 5–11 批源码及 Editor 构建均已完成，第七批另有此前的 Game 构建。第 12 批 C15/C16 的法杖公共词条读取去重及 Game 构建已完成；第 12–15 批待办的 Editor 构建现已统一收尾，第 13–15 批 C17–C19 源码与构建均已完成，详见第 20–24 节。P1 为合同重复或兼容风险优先级，P2 为局部整理。证据行号取各批修改前快照；后续修改可能使行号变化。

| ID | 范围及证据 | 判定与建议 | 边界 |
| --- | --- | --- | --- |
| C01 / P1 / 五个入口完成、火球保留 | `Skills/ColdSteelHolyLightModel.cpp`、`ColdSteelIceSpikeModel.cpp`、`ColdSteelLightningModel.cpp`、`ColdSteelElectricMagicModel.cpp`、`ColdSteelIceWallModel.cpp` | 第 1 批提取公共 helper，第 2 批复用；击杀去重、经验累加、等级循环、点数封顶由 `Skills/ColdSteelSpellRewards.h` 统一计算，训练公式与 StageTraining 提交仍由各法术拥有。两批已完成后台 Editor 构建，未测试。 | 不合并技能奖励系数；不提前写 RewardedVictims；超过 800 行的 `UI/ColdSteelProfileRuntime.cpp` 不动。火球独立等级经验缩放按用户要求保留，未套用 helper。 |
| C02 / P2 / 已完成 | `Source/FPSGAME/FPSGAME.Build.cs`；`Dungeons/FacilityHallSpawnSubsystem.h`、`UI/GameResourcePreparation.h` 直接使用 FRenderCommandFence | 第 3 批保留 Public RenderCore，仅删除 Private 的重复项；RHI 私有依赖保留。 | 不收窄已有公开依赖，不改变模块导出或公开头文件；后续 Editor 增量构建成功，目标已是最新。 |
| C03 / P2 / 已完成 | Build.cs 的旧 Source/Shaders 注册解释与 `FPSGAME.cpp:29–44` 不符 | 第 3 批改为说明现有头文件的 RenderCore 依赖，不再把依赖归因于已移除的模块启动注册。 | 未修改 FPSGAME.cpp、着色器文件、虚拟目录或水体材质；构建状态同 C02。 |
| C04 / P1 / 保留，已定向检查 | `Multiplayer/ColdSteelPlayerState.h:248`、`.cpp:2267`、`Characters/FPSPlayerBodyActions.cpp:742` | 疑似闲置兼容链：手写源码未发现发起调用；当前主要路径是 ServerBodyTransition / ServerBodySnapshot，但原 RPC 仍有生成包装、跳板及注册，并有复制状态副作用。证据见第 25 节。 | 未证明可删；未做资产引用解析或运行覆盖。PlayerState 头/实现均超 800 行，只读目标片段，不删除或拆分。 |
| C05 / P2 / 已完成 | `Survival/FPSSurvivalComponent.cpp/.h` | 第 4 批将两种食品的死亡冻结/剩余时间夹取提取为私有非反射方法 `FoodRecoveryRemaining`，复用原 `ServerTime()`；两个公开入口保留。 | 两个 OnRep 继续分别通知 StatusEffects，反射回调、字段、时长常量和存档语义未变；Editor 增量构建成功，目标已是最新。 |
| C06 / P2 / 保留 | `Plugins/ColdSteelNet/.../FPSNetGameMode.cpp:27–55` | 有效诊断代码，不是死代码：位置采样每两秒运行，且位于 `bAutoWalkDemo` 判断之前。若后续要求减少常驻诊断，可另列有界清理。 | 删除或移动到演示开关后会改变诊断行为，不符合本轮保持行为的清理边界；不能把“测试用途”直接等同于“永远不执行”。 |
| C07 / P2 / 已完成 | `Skills/ColdSteelHolyLightModel.cpp:127`、`ColdSteelIceSpikeModel.cpp:130`、`ColdSteelLightningModel.cpp:138`、`ColdSteelElectricMagicModel.cpp:90` | 四个法术入口改用已有内部头文件中的 `AccumulateCriticalTraining`，重复公式仍调用 `ColdSteelSkills::AddExperience`。 | 仅上述四个入口及 helper；不合并法术专属训练、不更改提交顺序；冰墙与火球不接入，超长 `ColdSteelSkillRules.cpp` 不修改；后台 Editor 构建成功。 |
| C08 / P2 / 已完成 | `Skills/ColdSteelFireMagicModel.cpp:143`、`ColdSteelBlizzardModel.cpp:120`、`ColdSteelMagicArrowRainModel.cpp:111` | 三处相同暴击修炼公式已改用第五批的 `AccumulateCriticalTraining`，后台 Editor 构建成功。 | 只改三个结算入口对应的一行公式及 include；helper 实现、即时击杀经验、训练提交时点和早退条件不改；火球、超长文件与疑似死代码保留。 |
| C09 / P2 / 已完成 | `Skills/ColdSteelIceSpikeModel.cpp:129`、`ColdSteelLightningModel.cpp:137`、`ColdSteelFireMagicModel.cpp:143`、`ColdSteelBlizzardModel.cpp:120`、`ColdSteelElectricMagicModel.cpp:89` | 五处命中、击杀、多目标和多杀修炼计算已提取到 `ColdSteelSpellRewards.h` 的 `AccumulateHitKillTraining`；Game 构建成功，随后由第八批成功构建补齐 Editor DLL。 | 冰锥/雷击继续按 Hits>=2 判定多目标，其余三个入口继续读取 Batch.bMultiHit；系数保留原技能配置，多杀仍要求 Kills>=2；火球与不同奖励结构不接入。 |
| C10 / P2 / 已完成 | `Skills/ColdSteelElementalArrowModel.cpp:54`、`ColdSteelMagicArrowRainModel.cpp:111`、`ColdSteelIceWallModel.cpp:123` 及 `ColdSteelSpellRewards.h` | 三处命中、击杀、多目标命中经验已改用纯计算函数 `HitTrainingExperience`；第七批四项计算也复用这三项，再加原多杀项；后台 Editor 构建成功。 | 保留原 int32 运算顺序、各自系数与 Hits>=2 条件；不为三处补多杀奖励，不改变提交或角色经验路径；圣光、火球、超长文件与疑似死代码不动。 |
| C11 / P2 / 已完成 | Skills 内 IceSpike、Lightning、HolyLight、IceWall、ElectricMagic、FireMagic、Blizzard、QuickCombat 的八个 Progress 查询入口 | 原“Find 后返回记录副本，否则默认构造”的重复分支已改用现有 TMap::FindRef 单参数接口，后台 Editor 构建成功。 | 保留原查询键及缺省 Level=1、Experience=0；不改用有额外习得判断的 MasteryProgress；不新增 helper，不改火球、超长文件或疑似死代码。 |
| C12 / P2 / 第 10 批已完成 | `Skills/ColdSteelHolyLightModel.cpp:117`、`ColdSteelIceSpikeModel.cpp:119`、`ColdSteelLightningModel.cpp:127`、`ColdSteelFireMagicModel.cpp:132`、`ColdSteelBlizzardModel.cpp:110` | 五个玩家命中路径重复累计 Hits、Kills、CriticalHits、CriticalKills；已提取到已有 `ColdSteelSpellRewards.h` 的 `RecordTrainingHit`，后台 Editor 编译及链接成功。 | 保留原训练资格门禁、反馈之后的调用位置、死亡查询次数和顺序；敌人施法分支及不同计数结构不接入；不改变伤害、奖励公式或提交。 |
| C13 / P2 / 第 11 批已完成 | `Skills/ColdSteelHolyLightModel.cpp:108`、`ColdSteelIceSpikeModel.cpp:111`、`ColdSteelLightningModel.cpp:118`、`ColdSteelFireMagicModel.cpp:123`、`ColdSteelBlizzardModel.cpp:101`、`ColdSteelMagicArrowRainModel.cpp:104` | 六个玩家命中入口重复构造反馈结果、赋值三项标志并通知角色；已收拢至 Skills 内的 `ColdSteelSpellFeedback.h`，后台编译及链接成功。 | 原伤害及附加状态之后、训练计数之前调用；先查询死亡状态，再执行角色 Cast 与通知；不接入敌人分支，不改变反馈参数。 |
| C14 / P2 / 第 11 批已完成 | `Skills/ColdSteelHolyLightModel.cpp:106`、`ColdSteelIceSpikeModel.cpp:108`、`ColdSteelLightningModel.cpp:111` | 三处逐键复制击杀奖励表的循环已改用现有 `TMap::Append` const 重载，后台编译及链接成功。 | 保留原位置、原键值、来源表和同键后值覆盖；不累加金额、不转移来源表、不修改角色经验或训练提交。 |
| C15 / P2 / 第 12 批源码与 Game/Editor 构建完成 | `Skills/ColdSteelHolyLightModel.cpp:49`、`ColdSteelIceSpikeModel.cpp:51`、`ColdSteelLightningModel.cpp:53`、`ColdSteelFireMagicModel.cpp:56`、`ColdSteelBlizzardModel.cpp:45` | 五个法术重复读取法杖暴击率与魔法穿透词条，已收拢至 `ColdSteelSpellCrafting.h::ApplyCriticalStats`；Editor 构建已于第 24 节统一收尾。 | 原法杖/强化系统门禁、原调用位置、键名、默认值、double 运算及 float 字段赋值保留；不改基础暴击、伤害或冷却。 |
| C16 / P2 / 第 12 批源码与 Game/Editor 构建完成 | `Skills/ColdSteelHolyLightModel.cpp:54`、`ColdSteelIceSpikeModel.cpp:56`、`ColdSteelLightningModel.cpp:60`、`ColdSteelFireMagicModel.cpp:61`、`ColdSteelBlizzardModel.cpp:50`、`ColdSteelIceWallModel.cpp:52` | 六个法术重复读取连锁标志、施法加速层数和时长，已收拢至同一头文件的 `ApplyChainAndCastHaste`；Editor 构建已于第 24 节统一收尾。 | 连锁字段仍按非零判断，层数沿原 int32 转换，时长缺省 5000 再除以 1000；冰墙只接入此组，不接入暴击/穿透。 |
| C17 / P2 / 第 13 批源码与 Editor 构建完成 | 八个连锁状态查询、四个法杖专精判断；精确路径见第 20、21 节。 | 复用现有 `ColdSteelSpellCrafting.h`，保留当前 Pawn/Item、原缺省值和原调用位置。 | 不合并不同的冷却/伤害/魔耗算法；不改火球独立经验缩放。 |
| C18 / P2 / 第 14 批源码与 Editor 构建完成 | 九个施法组件的 Model()；精确路径见第 20、22 节。 | 共用 `NetCast::LocalModel`，保持敌人模型与 GI 单例两分支。 | 不换用影子权威模型，不改相位、支付、退款或服务器结算。 |
| C19 / P2 / 第 15 批源码与 Editor 构建完成 | `LightningHastePresentation.cpp` 两处循环及组件私有声明；见第 23 节。 | 共用 `ClearLimbTickPrerequisites`。 | 保留调用位置、弱指针判断及 Mesh/Leader 移除顺序，不动表现效果。 |
| C20 / P2 / 第 16 批完成 | Skills/ColdSteelDashAttackModel.cpp、ColdSteelWhirlwindModel.cpp、ColdSteelSpellRewards.h | 两处 XP 表达式共用 MartialHitTrainingExperience；Editor 构建成功，见第 26 节。 | 原加法次序、Hits>=2、早退和训练提交保留，不修改支付/冷却事务。 |
| C21 / P2 / 第 16 批完成 | Skills/ColdSteelHolyLightModel.cpp、ColdSteelIceSpikeModel.cpp、ColdSteelLightningModel.cpp、ColdSteelIceWallModel.cpp、ColdSteelSpellCrafting.h | 四处冷却倍率共用 ApplyCooldownMultipliers；Editor 构建成功，见第 26 节。 | 保留 double 计算和两次 float 赋值，不纳入 FireMagic/Blizzard/ElectricMagic 或火球独立经验缩放。 |
| C22 / P2 / 第 17 批完成 | Skills/ColdSteelChainSlashModel.cpp、ColdSteelLeapStrikeModel.cpp、ColdSteelSpellRewards.h | H01 两处经验公式共用 MartialKillTrainingExperience；Editor 构建成功，见第 27 节。 | 原使用/击杀/多杀顺序、资格判断和训练提交保留。 |
| C23 / P2 / 第 17 批完成 | Skills/ColdSteelChainSlashModel.cpp、ColdSteelLeapStrikeModel.cpp、NetCastUtils.h | H02 两处冷却追时公式共用 RemainingCooldown；Editor 构建成功，见第 27 节。 | 读时、版本判断、float 转换点与回执其他副作用保留；H03 不为去重新增状态结构。 |
| C24 / P2 / 第 18 批完成 | Skills/ColdSteelIceWallModel.cpp | 玩家命中反馈复用现有 ColdSteelSpellFeedback::NotifyHit，Editor 构建成功。 | 保持默认非暴击、死亡查询/通知/训练顺序，不改变物理伤害、冰缓或奖励。 |
| C25 / P2 / 第 18 批完成 | Skills/FPSFireballComponent.cpp | Model() 复用现有 NetCast::LocalModel，删除重复 include 及本次替换后不再直接使用的两个 include，Editor 构建成功。 | 仅模型读取和 include；火球独立经验缩放、支付及网络相位不动。 |
| C26 / P2 / 第 18 批完成 | Skills/ColdSteelIceArmorModel.cpp、ColdSteelLightningHasteModel.cpp、ColdSteelSpellCrafting.h | 两处相同冷却倍率使用 AuraCooldownMultiplier，Editor 构建成功。 | float 减法/乘法/下限、左结合 double 符文乘法及最终一次 float 赋值保留；不套用两次赋值或 Clamp 版本。 |
| C27 / P2 / 第 19 批完成 | Skills/MagicArrowRainResources.cpp | 箭雨回执的冷却追时直接复用现有 NetCast::RemainingCooldown，Editor 构建成功。 | 保留资源版本判断、原读时及本地时间回退、转换/归零顺序和所有状态写入；不新增 helper。 |
| C28 / P2 / 第 20 批完成 | Skills/ColdSteelSkillTree.cpp 的 SpecRank | int32 专精等级查找与缺省 0 分支复用 TMap::FindRef，Editor 构建成功。 | 外层专精缺失判断保留，不插入记录、不限幅或改等级；SkillLevel、存档校正与条件文案不动。 |
| K01 / 保留 | `Dungeon/DungeonLayout.cpp:6`、`DungeonTypes.h`；UI 与六类法术仍调用 `DungeonLayout::RecordKill` | 旧地牢生成已退役，但存档结构和奖励去重仍活跃。 | 保留整个 102 行兼容目录；不因为它与 Dungeons 名称近似而合并或删除。 |
| K02 / 保留 | `Tasks/TaskTrackingSubsystem.cpp:52`、`UI/ColdSteelDungeonTracker.cpp:66` | `InitialStrike` 被 UI 实际调用；NormalizeTasks 与来源注册也在正常路径内。 | Commandlet 引用并非唯一消费者，不属于“只被测试使用”的死代码。 |
| K03 / 保留 | `Rendering/FPSFXAssetPreparation.h`，Skills 与两个地牢准备头文件使用 | 已有共用 Niagara/PSO 准备工具。 | 不再建立平行 helper；资产持有、超时和 GPU 准入仍由各拥有者管理。 |

当前没有充分证据支持直接删除业务函数或反射类型。C04 是死代码候选，不是已确认死代码；此次未做 Blueprint 二进制引用分析或运行覆盖。

## 4. 超过 800 行的文件

48 个文件全部留在原处。最大文件是 `Weapons/Spellbook/SpellbookAuthoredFocus.h`，14,049 行，其开头标明由 `Focus/IntegratedV30/author_motion.py` 生成；它主要是动作数据，不能用“删冗余逻辑”的方式减行。

完整路径、字节数、行数、建议责任拆分与执行顺序见 [48 项拆分方案](code-cleanup-20261116/split-plan.md)。本轮只统计行数、定向查看入口或声明，没有通读这些大文件并实施重构。方案中的目标文件名是建议，落地前需要核对现有同名职责文件，优先扩充既有拆分而非重复创建。

- 普通实现：保持现有 UCLASS 与公共头文件入口，先将现有方法定义按职责移入多个 `.cpp`；逐批处理局部静态 helper、链接和 include 依赖。
- 超长反射头：先区分公共反射合同、私有纯数据和可前置声明依赖；不能简单用 include 片段藏起行数，也不擅自改序列化字段。
- 生成动作头：先定位仍有效的作者脚本和消费者，设计按骨段/时间块生成的数据文件及采样入口，保持数值精度、时钟和骨序。只有改生成器才能避免下一次导出覆盖拆分。
- 每批建议控制一个三级职责，目标文件通常不超过 600 行，800 行作为硬边界；这些是拆分目标，不是已经测得的最终行数。

## 5. 规则清理结果

20 份规则入口共补充 333 处“为什么”。以规则段落或列表条目为单位解释保留原因；导航条目说明为什么集中读取相应合同。个人技能目录没有修改，引用资料仍保留历史证据身份。

| 旧条款 | 当前依据 | 处置 |
| --- | --- | --- |
| 模块路由表约 76% 指向不存在的技能，举例包括 save-load-replication | 仓库实际存在该 SKILL，个人维护源也有 architecture；表与两种入口不能混为同一存在性结论 | 删除过期比例与错误例子，改为按实际 SKILL 定位。 |
| 改承重数值必须跑离线探针；修改动作前默认核对运行加载 | 与用户“仅明确要求时测试/检查”的现行约定冲突 | 保留工具与资料读取入口，去掉默认执行义务。 |
| 强制使用固定 `read_image` 名称 | 会话工具名不是稳定的项目接口 | 改为使用当前会话提供的原生读图能力。 |
| E:/DSH provider/model 对、固定默认模型、探针派单规则 | 属特定旧宿主部署，不是 FPSGAME 模块或当前会话的工具合同 | 从 WORKFLOW 的现行规则删除第 11 节，恢复快照保留原文；不修改外部宿主配置。 |
| 工程技能与个人技能必须作为镜像同步 | 多数工程 SKILL 已明确改为个人维护源入口加工程专属参考 | 改成按实际归属维护，避免要求整库重复同步。 |
| 全部技能预载完毕才释放输入 | `TransitLoadingSubsystem.cpp:588–601` 在遮罩退出后的后台分支启动技能准备；PlayerSkillPreparation 的失败路径保持 entry unlocked | 删除旧阻塞放行段与被覆盖过渡方案，保留后台准备、取消、超时和真实材质准备规则。 |
| `UColdSteelSkillModel`、ShardHashes、SendProfileShard、4 KB shard 同步 | 当前声明为 UColdSteelStatusModel、MirrorBlob、ServerSubmitProfileChunk / ClientReceiveProfileChunk，块大小 1024 | 删除旧协议要求，指向当前传输入口；未修改协议代码。 |
| AOnlineGameMode、UColdSteelNetGameMode、AMultiplayerStart、AClippyPlaceholderPawn 登录链 | 当前插件实现 AFPSNetGameMode；定向模块中未见旧类 | 删除不存在的类与出生路径规则，按实际 GameMode 和 WorldSubsystem 接入。 |
| ConnectSubsystem.OnMapLoad 做 GPU 预热 | 当前实现 Initialize/定时器/TryConnect 发一次 open | 改为延迟连接辅助，不宣称实际 GPU 预热服务。 |
| ClientShotResult 与 ClientRequestCast/ServerCastBegin/ServerCastRelease | 当前头文件为 ClientConfirmHit、ServerCastSpell、ClientCastResult | 删除旧 RPC 名称及基于它们的流程要求。 |
| 符文剑 NM_Client 不 Tick，只有主机可用 | RuneSwordComponent.cpp:108–122 已有本机控制/Authority 初始化分支，后续存在 NM_Client 请求路径 | 删除主机独占断言，保留本机表现和权威结算职责。 |
| 插件全被忽略，必须 git add -f | 当前 .gitignore 对 ColdSteelNet 描述符与 Source 已设例外 | 删除默认强制加入要求，保留精确路径与二进制许可边界。 |
| RootMotionSource 必须实现旧文列举的多个重载；Duration 不可访问 | 当前派生类只声明 Clone/GetScriptStruct/PrepareRootMotion，实际代码读取 Duration | 改为保留现有区间积分实现，不从旧说明推断引擎 API。 |
| 任何新问题先启动 MPTEST/多进程取证；Live Coding 失败一概归因 Debug | 没有这种默认执行授权或通用因果依据 | 删除自动测试和单一原因断言，要求按本次问题与构建输出判断。 |

联机技能收敛为 20 条当前合同，详细机制继续由已有专项参考承载。删除的是失效或越界的现行指令；历史原文仍可追溯。后台开发、不跨对话协调、不默认测试、保护并行工作、资产许可与恢复规则属于用户工作约定，不能因为它们没有对应 C++ 类而删除。

## 6. 交付与恢复

- 主报告：本文件。
- 模块归属：[module-map.md](code-cleanup-20261116/module-map.md)。
- 大文件方案：[split-plan.md](code-cleanup-20261116/split-plan.md)。
- 行数清单：[code-cleanup-20261116-inventory.json](code-cleanup-20261116-inventory.json)，每条含路径、目录、行数和字节数，仅覆盖 Source/FPSGAME。
- 规则改前清单：[rule-manifest-before.json](code-cleanup-20261116/rule-manifest-before.json)，20 份原件共 131,546 字节；逐份快照保存在同目录 `before/` 下，以 `.txt` 后缀区分现行规则。
- 规则改后清单：[rule-manifest-after.json](code-cleanup-20261116/rule-manifest-after.json)，含精确路径、字节数、SHA-256 和原因条数。

保留清单：第 1–15 批精确范围以外的业务源码、构建脚本、配置、Content、SourceAssets、第三方插件、旧地牢兼容数据以及原有未提交/暂存改动。前两批的必要构建更新常规中间产物、Editor DLL 及构建日志；第 3、4 批最终收尾调用 UBT 成功，目标已是最新，未执行新的编译/链接动作。第 5、6 批各有编译/链接成功日志；第 7 批先完成 Game 构建，第 8 批完成共同的 Editor 构建收尾；第 9–11 批各有成功 Editor 构建；第 12 批 Game 构建成功，第 12–15 批 Editor 构建已在共享占用结束后统一收尾，独立 UBT 调用成功、目标已是最新，详见第 12–24 节。没有删除生产文件或进行磁盘空间回收。恢复须从对应批次快照提取所需片段，不整文件覆盖之后的并行修改。

第 1、2 批共处理 C01 中五个法术结算入口，火球的独立奖励口径继续保留；第 3 批限定 Build.cs，处理 C02/C03；第 4 批限定 Survival 组件，处理 C05 的重复计时。C04、大文件拆分以及会改变诊断行为的 C06 继续搁置，保持玩法、数值、网络协议和资产路径不变。

初始盘点没有运行编译、lint、单元测试、Commandlet、UE 编辑器、PIE、预览或运行验收。第 1、2 批于 2026-11-17 完成一次必要后台 Editor 构建，第 3、4 批随后完成增量构建收尾，没有执行测试。模块行数清单保留初始快照，不代表整个共享工作区被冻结或所有模块已经语义审计完毕。

第 3、4 批最初因活动编辑器而未能启动 UBT；最终状态以 2026-11-17 09:37 独立调用所得的[构建收尾回执](code-cleanup-20261116/build-completion-20261117.json)为准，没有沿用前两批成功日志。该次共享工程被 UBT 判定为最新，没有重新编译或链接 DLL；第 5 批后续重新编译和链接的结果单列于第 12 节。构建成功不代表运行效果通过。

## 7. 第 1 批：法术奖励结算去重（已完成）

源码整理：2026-11-16；后台构建收尾：2026-11-17。用户要求按报告开始第一批，严格限于法术奖励模块，超过 800 行文件和疑似死代码不动，不新增功能、不测试。

### 实际修改

路径均相对于 `Source/FPSGAME/Skills/`：

| 文件 | 修改前行数 | 修改后行数 | 本批改动 |
| --- | ---: | ---: | --- |
| `ColdSteelHolyLightModel.cpp` | 143 | 141 | 原公共计算段替换为 helper 调用，调整对应 include。 |
| `ColdSteelIceSpikeModel.cpp` | 135 | 133 | 同上；预留状态与元素箭训练分支保留。 |
| `ColdSteelLightningModel.cpp` | 143 | 141 | 同上；元素箭和多目标训练规则保留。 |
| `ColdSteelSpellRewards.h` | 新增 | 32 | 模块内部 inline helper，承接三处原有公共计算。 |

`ColdSteelSpellRewards::AccumulateKillExperience` 只修改调用者传入的档案快照。它沿用原奖励遍历顺序，先调用 `DungeonLayout::RecordKill` 去重，随后累加击杀计数和取整后的经验；全部奖励累加后再执行原等级循环与上限夹取。

### 保留的行为合同

- 每个有效击杀仍在去重之后读取 `TributeEffect("expPercent")`，没有提前求值或改成整批缓存。
- 角色升级门槛仍为 `(20 + Level*20 + Level*Level*12)*8`，等级上限 10,000，每级加 3 点，属性点上限 1,000,000；经验与击杀计数的夹取和取整方式不变。
- 三个入口先执行原技能与暴击训练，再累加角色奖励，最后调用原 `StageTraining(MoveTemp(P))`；仅其返回接受后才写 `RewardedVictims`。
- 冰锥未预留时的提前返回、预留清除、元素箭训练以及冰锥/雷击多目标训练原样保留。命中、伤害、魔法费用、冷却、动画、网络协议和存档字段均未改动。
- 第 1 批本身不接入 ElectricMagic、IceWall 或 Fireball；前两者随后由第 2 批接入。火球已有 `MonsterCoreStats::ScaleKillExperience`，不能把它视为与前三者完全相同的奖励公式。`UI/ColdSteelProfileRuntime.cpp`、疑似闲置 RPC、其他清理项及规则文件均未改动。

### 交付状态与恢复

源码已落盘，必要后台构建已完成。2026-11-16 因已有 UBT 作业未另起构建；2026-11-17 用户要求完整收尾时，共享构建和编辑器均未占用，执行现有 `Tools/Build/Build-Editor.ps1`，`FPSGAMEEditor Win64 Development` 返回 `Succeeded`（退出码 0，24 个动作，67.31 秒），完成 `UnrealEditor-FPSGAME.lib`、`UnrealEditor-FPSGAME.dll` 链接与目标元数据写入。

本次构建同时包含第 2 批已落盘修改；这是当前共享工程的 Editor 目标构建结果，不是隔离只编译三个文件的结论。第 1 批源码接入与必要构建已收尾，未运行测试、lint、审计工具、UE 编辑器、PIE 或 Commandlet，也未另构建 Game/打包目标。构建中的 UI/Weapons 数值转换和 API 弃用警告属于本批范围之外，未为处理它们修改其他模块。

构建日志：[build-20261117-000403.log](../../Saved/BuildEditor/build-20261117-000403.log)；结果记录：[build-receipt.json](code-cleanup-20261116/batch-01-spell-rewards/build-receipt.json)。编译成功不代表运行验收，运行效果由用户测试。

三个已有文件均以本批开始时的工作区内容为基线，保留已有未提交修改及文件换行格式；没有改动暂存区、提交或推送。精确路径、前后行数、字节数和 SHA-256 见 [第 1 批源码清单](code-cleanup-20261116/batch-01-spell-rewards/source-manifest.json)。原件存放在同目录的三个 `*.before.txt`，仅用于按片段恢复本批修改。

## 8. 第 2 批：ElectricMagic 与 IceWall 奖励结算去重（已完成）

日期：2026-11-17。源码修改只涉及 `Source/FPSGAME/Skills/` 下两个文件；复用上一批 helper，没有改动其实现。

| 文件 | 修改前行数 | 修改后行数 | 本批改动 |
| --- | ---: | ---: | --- |
| `ColdSteelElectricMagicModel.cpp` | 95 | 93 | 将 `FinishElectricMagicCast` 的公共奖励段替换为 `AccumulateKillExperience(P,R.KillRewards,*this)`，调整对应 include。 |
| `ColdSteelIceWallModel.cpp` | 145 | 143 | 将 `ApplyIceWallSpawn` 的公共奖励段替换为 `AccumulateKillExperience(P,Rewards.Kills,*this)`，调整对应 include。 |

- ElectricMagic 保留技能 ID 与 `Batch.Hit.Hits<=0` 的提前返回、按实际电系技能定义取数、`Batch.bMultiHit` 多目标训练、击杀训练和暴击训练。
- IceWall 保留原生敌人分支、权威门禁、落地伤害、训练目标排除、命中/击杀计数、多目标训练和冰缓处理；没有补入其他法术的暴击或多杀训练规则。
- 两处仍先 `SyncRuntime` / `Snapshot`，执行各自训练公式，再通过 helper 累加角色奖励，最后 `StageTraining(MoveTemp(P))`；仅提交接受后才添加 `RewardedVictims`。奖励遍历、去重、逐击杀经验倍率求值、取整和升级封顶均沿用原流程。
- 火球文件及 `MonsterCoreStats::ScaleKillExperience` 未改，超过 800 行文件、疑似死代码和 Skills 以外业务源码未改；未新增功能。

两个文件已由第 7 节同一次成功后台构建编译并链接进 Editor DLL，未运行测试或游戏。原件与前后行数、字节数、SHA-256 见 [第 2 批源码清单](code-cleanup-20261116/batch-02-spell-rewards/source-manifest.json) 及同目录 `*.before.txt`。没有暂存、提交或推送。

## 9. 第 3 批：RenderCore 依赖与说明清理（已完成）

日期：2026-11-17。按报告顺序处理 C02/C03；仅修改 `Source/FPSGAME/FPSGAME.Build.cs`，从 73 行变为 71 行。

### 实际修改与依据

- 保留 `PublicDependencyModuleNames` 的 `RenderCore`，从 `PrivateDependencyModuleNames` 移除重复声明；原同组的 `RHI` 改为单独 `Add("RHI")`，依然是私有依赖。
- 将旧“FPSGAME.cpp 注册 Source/Shaders 所以必须 Public”的注释，替换为实际头文件依赖说明。`Dungeons/FacilityHallSpawnSubsystem.h:4` 与 `UI/GameResourcePreparation.h:4` 包含 `RenderCommandFence.h`，前者的导出 UCLASS 直接持有 FRenderCommandFence 成员；`WorldGeneration/TemperateVegetationRenderAudit.h:4` 包含 `RenderingThread.h`。这两个引擎头文件属于本机 `Runtime/RenderCore/Public/`。
- 原有 Public 依赖已经向当前模块及消费者提供 RenderCore，因此去掉额外 Private 登记不收窄公开依赖。没有改动其他模块依赖或任何 C++ 实现；没有恢复旧着色器目录注册。
- 火球、前两批法术文件、超过 800 行文件、疑似死代码、资源和规则文件均未修改，未新增功能。

### 构建状态与恢复

首次调用现有 `Tools/Build/Build-Editor.ps1` 时，脚本在第 19 行因活动 FPSGAME 编辑器中止，退出码 1；当时匹配工程的 `UnrealEditor.exe` 为 PID 1992，UBT 尚未启动。该次记录只表示构建前置阻塞。本批未关闭、重启或终止该进程，未发送跨对话协调消息，也未绕过脚本门禁。

2026-11-17 09:37 续办时，编辑器和已有构建进程已退出，执行同一脚本完成后台 `FPSGAMEEditor Win64 Development` 构建，退出码 0、Result: Succeeded。UBT 返回 Target is up to date，0 个动作，总耗时 8.77 秒。本批构建收尾已完成，但本次没有重新链接或生成 DLL。未运行测试、lint、审计工具、PIE 或 Commandlet，未启动编辑器或游戏。

精确前后尺寸、行数、SHA-256 与原件路径见 [第 3 批源码清单](code-cleanup-20261116/batch-03-rendercore/source-manifest.json)。[原构建门禁回执](code-cleanup-20261116/batch-03-rendercore/build-receipt.json)保留历史尝试；最终状态见[构建收尾回执](code-cleanup-20261116/build-completion-20261117.json)和[本次构建日志](../../Saved/BuildEditor/build-20261117-093750.log)。改前文件来自当时工作区，已有未提交内容和换行格式保留；没有暂存、提交或推送。

## 10. 第 4 批：食品恢复计时去重（已完成）

日期：2026-11-17。继续第三批时，FPSGAME 编辑器 PID 1992 仍在运行，因此先推进报告 C05 的独立源码清理。仅修改 `Source/FPSGAME/Survival/FPSSurvivalComponent.cpp/.h`。

| 文件 | 修改前行数 | 修改后行数 | 本批改动 |
| --- | ---: | ---: | --- |
| `FPSSurvivalComponent.cpp` | 306 | 307 | 提取公共死亡冻结和剩余时间夹取，两种食品原有入口转调同一个方法。 |
| `FPSSurvivalComponent.h` | 51 | 52 | 增加一条私有非反射方法声明，没有增加状态字段或公开入口。 |

### 保留的行为合同

- `FoodRecoveryRemaining(SavedSeconds,EndsAt,Duration)` 仍先取得拥有者的 Health 组件；死亡时直接返回对应食品保存的剩余秒数，不读取服务器时钟。
- 非死亡分支仍通过原 `ServerTime()` 使用 GameState 服务器时间，无 GameState 时回退世界时间，无 World 时返回 0；结果仍按 double 夹取到 `[0, Duration]` 后转为 float。
- `SausageRecoveryRemaining` 与 `LargeLambMealRemaining` 分别传入各自的剩余秒数、截止时间和时长常量，没有把两种食品的状态合并或硬编码为同一时长。
- 保留两个 OnRep 函数及各自的 `UStatusEffectsComponent::Notify` 调用；没有修改 UPROPERTY、复制条件、存档结构、恢复入口、死亡期间截止时间维护、Tick 周期、饥渴/SAN 公式或食品效果数值。
- 原计划中的局部 helper 落为组件私有方法，以直接复用既有私有 `ServerTime()`，避免额外时钟实现或回调模板。复用现有逻辑，没有增加玩法能力；火球、超长文件、疑似死代码和其他模块未修改。

### 构建状态与恢复

源码落盘后的首次 `Tools/Build/Build-Editor.ps1` 调用被第 19 行的活动编辑器门禁中止，退出码 1，UBT 未启动。2026-11-17 09:37 占用释放后，第 3、4 批共用一次后台 Editor 构建收尾：退出码 0、Succeeded、Target is up to date，0 个编译/链接动作，总耗时 8.77 秒。未关闭、重启或终止编辑器，未执行 Live Coding，也未运行测试、lint、审计工具、PIE 或 Commandlet。

源码前后行数、尺寸、SHA-256 和工作区原件位置见 [第 4 批源码清单](code-cleanup-20261116/batch-04-survival/source-manifest.json)；首次门禁结果保留于[历史构建回执](code-cleanup-20261116/batch-04-survival/build-receipt.json)，最终结果见[构建收尾回执](code-cleanup-20261116/build-completion-20261117.json)和[本次日志](../../Saved/BuildEditor/build-20261117-093750.log)。已有未提交修改和文件换行格式保留，没有暂存、提交或推送。

此前续办时曾观察到 FPSGAME 编辑器 PID 1992 和另一项 Game 目标构建；当时保持现场。最终收尾是在这些进程退出后执行原 Editor 构建脚本，没有借用另一项构建结果，也未另行构建 Game 目标。

## 11. 前四批清单收尾与保留边界

2026-11-17 完成第 3、4 批必要构建及报告状态更新，该次收尾没有新增源码修改。初始清单 C01–C06 中可在“不加功能、保持行为、不动超长文件与疑似死代码”的边界内直接实施的项目均已收尾。随后新增的第 5–12 批分别独立记于第 12–19 节；第 13–15 批按用户要求连续实施，清单及源码记录见第 20–23 节。第 12–15 批统一的 Editor 构建状态见第 24 节。

| 项目 | 最终处置 | 原因与范围 |
| --- | --- | --- |
| C01：五个法术奖励入口 | 已完成，见第 7、8 节 | 复用同一奖励计算，原技能训练与提交顺序保留。 |
| C02/C03：RenderCore 依赖及旧解释 | 已完成，见第 9 节 | 删除重复依赖，注释对应现有头文件用途。 |
| C05：食品剩余时间 | 已完成，见第 10 节 | 复用死亡冻结与夹取方法，独立字段和回调保留。 |
| 火球奖励 | 按要求保留 | 独立经验缩放未并入公共公式。 |
| C04：疑似闲置 RPC | 保留 | 未证明可删，且相关 PlayerState 文件超过 800 行。 |
| C06：常驻位置诊断 | 保留 | 代码正在执行；删去或缩小执行条件会改变诊断行为。 |
| 48 个超长文件 | 拆分方案已交付，源码未改 | 本轮只提供职责拆分方案，不实施拆分。 |
| K01–K03 | 保留 | 分别是活跃兼容数据与去重、任务显示路径、已有共用资产准备工具。 |
| 模块图与规则入口 | 初始交付保留 | 最多三级模块图、20 份规则入口整理及保留原因已交付；不扩展为全仓逐文件扫描或引用文档递归重写。 |

前四批必要构建已收尾。上述保留项不列为已删除、已合并或待自动执行；后续若调整范围，应沿原模块边界单独开展。未新增功能、未测试，运行效果由用户测试。

## 12. 第 5 批：法术暴击修炼公式去重（已完成）

日期：2026-11-17。用户继续下一步；范围为“武器与战斗 → 技能魔法 → 法术暴击修炼结算”，仅限 Skills，最多三级。本批在前四批完成后的清单上追加 C07，不重新扫描整个仓库。

### 先列清单，再实施的修改

| 文件 | 修改前行数 | 修改后行数 | 实际修改 |
| --- | ---: | ---: | --- |
| `Skills/ColdSteelHolyLightModel.cpp` | 141 | 141 | 原暴击修炼公式改为 helper 调用。 |
| `Skills/ColdSteelIceSpikeModel.cpp` | 133 | 133 | 同上，保留元素箭训练与预留状态处理。 |
| `Skills/ColdSteelLightningModel.cpp` | 141 | 141 | 同上，保留元素箭训练。 |
| `Skills/ColdSteelElectricMagicModel.cpp` | 93 | 93 | 同上，计数仍读取 `Batch.Hit`。 |
| `Skills/ColdSteelSpellRewards.h` | 32 | 40 | 在已有内部 helper 中收拢一条重复公式，直接包含 `ColdSteelSkillRules.h`；更新注释说明边界。 |

四处原式均为 `CriticalHits * CriticalStrikeSkill.CriticalHitExperience + CriticalKills * CriticalStrikeSkill.CriticalKillExperience`，参数和系数均为 int32。helper 继续调用原 `ColdSteelSkills::AddExperience`，保持未学技能、零经验及等级上限处理由原函数负责；不另增早退、封顶、倍率或训练字段。

调用位置仍为法术专属训练之后、角色击杀经验之前，`StageTraining` 和接受后写入 `RewardedVictims` 留在原入口。冰墙无此训练分支，因此不接入；火球、持续法术、公共状态模型、大文件、疑似死代码和资产均不在本批修改范围。既有 `AccumulateKillExperience` 函数体未改，没有增加反射类型、成员字段或公开状态模型方法。

### 构建与恢复

源码已落盘，执行原 `Tools/Build/Build-Editor.ps1` 进行必要后台构建。脚本先等待已有 Build.bat 释放，随后 `FPSGAMEEditor Win64 Development` 返回 Succeeded，退出码 0，共 8 个动作，UBT 耗时 17.78 秒。四个修改入口均重新编译；未改源码的 IceWall 因包含同一公共头文件也重新编译，随后完成 `UnrealEditor-FPSGAME.lib`、`UnrealEditor-FPSGAME.dll` 链接和目标元数据写入。这是共享工程的增量构建，没有为清理额外复制工程或改动其他模块。

本次日志：[build-20261117-094719.log](../../Saved/BuildEditor/build-20261117-094719.log)；结果记录：[第 5 批构建回执](code-cleanup-20261116/batch-05-critical-training/build-receipt.json)。没有终止占用进程，没有启动编辑器或游戏；未运行测试、lint、审计工具、PIE 或 Commandlet。运行效果交由用户测试。

修改前原件、逐文件行数、字节数与 SHA-256 见[第 5 批源码清单](code-cleanup-20261116/batch-05-critical-training/source-manifest.json)，恢复快照为同目录五个 `*.before.txt`。操作保留原文件换行和已有工作区内容，没有暂存、提交或推送。

## 13. 第 6 批：剩余法术暴击修炼入口去重（已完成）

日期：2026-11-17。按用户要求先列清单再清理。范围为“武器与战斗 → 技能魔法 → 法术暴击修炼结算”，仍只限 Skills，不超过三级；语义阅读聚焦模型结算入口和相关奖励计数字段，没有逐文件通读全仓。

### 先列清单，再实施的修改

| 文件 | 修改前行数 | 修改后行数 | 原重复位置与实际处理 |
| --- | ---: | ---: | --- |
| `Skills/ColdSteelFireMagicModel.cpp` | 146 | 147 | `FinishFireMagicCast` 增加已有 helper 的 include，公式改为 `AccumulateCriticalTraining(P,CriticalStrikeSkill,Batch.CriticalHits,Batch.CriticalKills)`。 |
| `Skills/ColdSteelBlizzardModel.cpp` | 122 | 123 | `FinishBlizzardCast` 作同样替换，保留自身无命中早退与批次结算。 |
| `Skills/ColdSteelMagicArrowRainModel.cpp` | 113 | 114 | `ApplyMagicArrowRain` 末尾改用 helper，传入既有局部 `CriticalHits`、`CriticalKills`，保持伤害遍历完成后统一训练。 |

三处计数和系数均为 int32，原式与第五批 helper 完全一致，继续由原 `ColdSteelSkills::AddExperience` 处理未学技能、非正经验与等级上限。仅复用已有实现，不新增 helper、状态字段、反射入口或功能。

### 保留项与行为边界

- FireMagic 指 `meteor`、`flameArmor`、`dragonBreath`，不涉及 `ColdSteelFireballModel.cpp`；保留非法技能 ID 或 `Hits<=0` 的早退、`bMultiHit`/多杀训练和原 `StageTraining` 位置。
- Blizzard 保留 `Hits<=0` 早退、原多目标/多杀训练、预留释放与冷却逻辑。
- MagicArrowRain 保留权威与怪物分支、命中去重、遮挡、训练目标排除、局部计数、`Hits==0` 早退和技能自身多目标训练；不增加其他法术的多杀训练项。
- 三个入口的角色击杀经验仍走原有即时路径；不调用 `AccumulateKillExperience`，不引入奖励地图或 `RewardedVictims` 批次登记。修炼仍先写入原快照，再调用原 `StageTraining`。
- `ColdSteelSpellRewards.h`、前五批其他源码、火球独立经验缩放、超过 800 行的文件、疑似死代码、其他模块及资产均不修改。
- 其他模型中的通用快照/提交语句，以及按单次命中累积的 `Train(CriticalStrikeSkill,...)`，与本批批次计数公式并非同一结算流程，保留各拥有者的门禁和事务顺序，不借本批扩大合并范围。

### 构建与恢复

清单先写入本节，随后按上述三个路径保存原件并修改，保留已有工作区内容和换行。原件及逐文件前后行数、字节数、SHA-256 见[第 6 批源码清单](code-cleanup-20261116/batch-06-critical-training/source-manifest.json)和同目录三个 `*.before.txt`。本批没有暂存、提交或推送。

执行现有 `Tools/Build/Build-Editor.ps1`，`FPSGAMEEditor Win64 Development` 返回 Succeeded，退出码 0，共 6 个动作，UBT 耗时 17.86 秒。三个修改文件均编译完成，随后链接 `UnrealEditor-FPSGAME.lib`、`UnrealEditor-FPSGAME.dll` 并写入目标元数据。结果为共享工程的增量构建，未修改其他模块源码来完成本批。

本次日志：[build-20261117-095310.log](../../Saved/BuildEditor/build-20261117-095310.log)；结果记录：[第 6 批构建回执](code-cleanup-20261116/batch-06-critical-training/build-receipt.json)。未新增功能，未启动编辑器或游戏，未运行测试、lint、审计工具、PIE 或 Commandlet，运行效果交由用户测试。

## 14. 第 7 批：命中与多目标修炼公式去重（已完成）

日期：2026-11-17。按用户要求先列清单，再实施重复逻辑清理。三级范围为“武器与战斗 → 技能魔法 → 法术批次修炼结算”，源码只涉及 Skills。阅读限定于结算入口和对应 tuning 字段，不通读全仓，不运行测试。

### 先列清单，再实施的修改

| 文件 | 修改前行数 | 修改后行数 | 实际修改与保留差异 |
| --- | ---: | ---: | --- |
| `Skills/ColdSteelIceSpikeModel.cpp` | 133 | 133 | 提取四项修炼计算；多目标参数仍为 `Batch.Hits>=2`，元素箭训练及预留清除保留。 |
| `Skills/ColdSteelLightningModel.cpp` | 141 | 141 | 提取同一计算；仍用 `Batch.Hits>=2`，保留元素箭训练。 |
| `Skills/ColdSteelFireMagicModel.cpp` | 147 | 146 | 提取同一计算并去掉不再直接使用的规则头 include；继续读取 `Batch.bMultiHit`。 |
| `Skills/ColdSteelBlizzardModel.cpp` | 123 | 122 | 同上，保留无命中早退。 |
| `Skills/ColdSteelElectricMagicModel.cpp` | 93 | 92 | 提取同一计算并去掉不再直接使用的规则头 include；计数仍取 `Batch.Hit`，多目标仍取 `Batch.bMultiHit`，保留技能 ID 门禁。 |
| `Skills/ColdSteelSpellRewards.h` | 40 | 51 | 增加内部 `AccumulateHitKillTraining`，仅收拢既有四项公式，更新边界注释；其他 helper 函数体不改。 |

五处均计算 `Hits * HitExperience + Kills * KillExperience + (bMultiHit ? MultiHitExperience : 0) + (Kills>=2 ? MultiKillExperience : 0)`。四个系数与计数均为 int32，系数继续读取原技能的 tuning。现有 tuning 是五种不同结构，因此 helper 用一个函数模板接收原结构的 const 引用，不新增数据结构、默认系数或配置；多目标布尔值由各原入口按原条件传入。

FireMagic、Blizzard、ElectricMagic 在转移最后一个直接 `ColdSteelSkills::AddExperience` 调用后，移除由本次修改造成冗余的 `ColdSteelSkillRules.h` 直接 include；该依赖已由 `ColdSteelSpellRewards.h` 自身包含。冰锥和雷击仍直接调用 `ColdSteelSkills::IsCriticalHit`，保留各自的直接 include。

### 本批保留边界

- helper 仍只修改传入的原快照，并调用既有 `ColdSteelSkills::AddExperience`；不自行同步、提交、保存、增加早退或变更技能学习与等级上限规则。
- 每个入口仍先执行原门禁、同步和快照；冰锥/雷击的元素箭训练保持在本技能训练之前；暴击训练仍在本技能训练之后。
- 角色经验的批次/即时路径、`StageTraining`、提交接受后登记 `RewardedVictims` 的顺序全部保留。
- 圣光只有命中和击杀项；冰墙、元素箭、魔法箭雨没有本批相同的多杀奖励项，均不为套用 helper 补入奖励，也不修改这些文件。
- 火球文件及独立经验缩放、超过 800 行的文件、疑似死代码、其他模块、公开状态模型声明和资产均不动。

### 构建与恢复

清单先落盘，随后仅修改上述六个文件；原件、逐文件前后行数、字节数和 SHA-256 见[第 7 批源码清单](code-cleanup-20261116/batch-07-hit-kill-training/source-manifest.json)，同目录六个 `*.before.txt` 用于按片段恢复。保留已有工作区内容及换行，没有暂存、提交或推送。

首次调用原 `Tools/Build/Build-Editor.ps1`，第 19 行因正在运行的 `UnrealEditor-Cmd.exe`（PID 33108）中止，退出码 1，UBT 尚未启动。该进程使用另一个制作宿主，未关闭或干预；[Editor 构建尝试回执](code-cleanup-20261116/batch-07-hit-kill-training/editor-build-attempt.json)保留此次阻塞事实。

本批随后执行独立的 `FPSGAME Win64 Development` 后台编译，返回 Succeeded，退出码 0，10 个动作，UBT 耗时 55.51 秒。五个修改入口及同头文件的三个未修改消费者（HolyLight、IceWall、MagicArrowRain）均重新编译，随后链接 `Binaries/Win64/FPSGAME.exe` 并写入 Game 目标元数据。该次使用共享工程和现有 Game 目标，没有修改构建配置或复制工程。

Game 日志：[cleanup-batch07-20261117-103707.log](../../Saved/BuildGame/cleanup-batch07-20261117-103707.log)；结果记录：[第 7 批 Game 构建回执](code-cleanup-20261116/batch-07-hit-kill-training/build-receipt.json)。该次结束时无界面 UE 进程仍运行，因此当时仅交付 Game 构建结果，未干预占用进程。

2026-11-17 10:52 第八批收尾时占用已释放，原 `Tools/Build/Build-Editor.ps1` 成功执行，包含本批五个模型入口的重新编译和 Editor DLL 链接；原 Editor 待执行项现已完成。以[第八批 Editor 构建回执](code-cleanup-20261116/batch-08-hit-training-calculation/build-receipt.json)和[日志](../../Saved/BuildEditor/build-20261117-105258.log)作为新增证据，原阻塞记录及 Game 回执保留历史状态。

源码及 Game/Editor 必要构建均已收尾。未终止进程、未发送跨对话协调消息、未启动编辑器或游戏，未新增功能、未运行测试、lint、审计工具、PIE 或 Commandlet，运行效果交由用户测试。

## 15. 第 8 批：三项命中修炼计算去重（已完成）

日期：2026-11-17。按用户要求先列清单，再清理剩余重复逻辑。三级范围为“武器与战斗 → 技能魔法 → 命中修炼计算”，仅限 Skills 中四个源码文件，所有待改文件均不超过 800 行。语义读取限定于对应模型结算入口、现有 helper 与系数字段，没有通读全仓。

### 先列清单，再实施的修改

| 文件 | 修改前行数 | 修改后行数 | 实际修改 |
| --- | ---: | ---: | --- |
| `Skills/ColdSteelElementalArrowModel.cpp` | 81 | 82 | 增加现有奖励 helper 头文件的 include；`StageElementalArrowTraining` 的原 AddExperience 调用改为接收公共计算结果。 |
| `Skills/ColdSteelMagicArrowRainModel.cpp` | 114 | 114 | 原 AddExperience 调用接收同一计算结果，保留后续暴击训练和提交。 |
| `Skills/ColdSteelIceWallModel.cpp` | 143 | 143 | 原 AddExperience 调用接收同一计算结果，保留后续角色经验和提交成功登记。 |
| `Skills/ColdSteelSpellRewards.h` | 51 | 59 | 提取只返回 int32 的 `HitTrainingExperience`；原四项训练 helper 复用它并保留最后的多杀加项，更新计算边界注释。 |

重复三项式为 `Hits * HitExperience + Kills * KillExperience + (Hits>=2 ? MultiHitExperience : 0)`。元素箭和箭雨的系数来自原技能定义，冰墙来自原 `IceWall` tuning；计数、系数及结果均保持 int32。公共计算接收原结构 const 引用与调用者提供的多目标条件，不新增配置、状态或通用提交接口。

### 保留项与差异

- 三个入口继续自己调用一次 `ColdSteelSkills::AddExperience`，原学习状态、非正经验和等级上限处理不动；`SyncRuntime`、`Snapshot` 和 `StageTraining` 仍由原拥有者控制。
- 元素箭方法只修改传入的档案快照，不新增独立提交；火、冰、雷的调用时点及专精继承不变，火球角色经验的独立缩放不改。
- 箭雨保留零命中早退、权威伤害遍历、暴击计数与提交顺序；冰墙保留权威及敌人分支、原命中计数、角色奖励和 `RewardedVictims` 接受后登记。
- 三个入口不新增多杀修炼项。第七批四项公式保留原 `bMultiHit` 来源和 `Kills>=2` 多杀条件，只将前三项委托给同一纯计算函数；算术分组和系数来源不变。
- 圣光只有两项修炼且没有多目标系数字段，本批不接入；火球文件、超过 800 行的文件、疑似死代码、其他模块和资产不动。
- 原暴击训练与角色击杀经验 helper 函数体不修改；三个模型仍直接调用技能规则，因此保留 `ColdSteelSkillRules.h` 的直接 include。

### 构建与恢复

清单先写入本节，再保存四个源码原件并实施。前后行数、字节数与 SHA-256 见[第 8 批源码清单](code-cleanup-20261116/batch-08-hit-training-calculation/source-manifest.json)，同目录四个 `*.before.txt` 为恢复快照。仅按片段恢复本批改动，保留后续并行修改；没有暂存、提交或推送。

执行原 `Tools/Build/Build-Editor.ps1`，`FPSGAMEEditor Win64 Development` 返回 Succeeded，退出码 0，12 个动作，UBT 耗时 17.44 秒。三个本批模型和六个共用头文件的其他消费者均重新编译，随后完成 `UnrealEditor-FPSGAME.lib`、`UnrealEditor-FPSGAME.dll` 链接与目标元数据写入。此次共享工程增量构建也完成第七批此前待执行的 Editor 构建；本批没有另行构建 Game 目标。

本次日志：[build-20261117-105258.log](../../Saved/BuildEditor/build-20261117-105258.log)；结果记录：[第 8 批构建回执](code-cleanup-20261116/batch-08-hit-training-calculation/build-receipt.json)。本批未修改 Skills 以外业务源码、配置或资产，未新增功能、未终止占用进程、未启动编辑器或游戏，未运行测试、lint、审计工具、PIE 或 Commandlet，运行效果交由用户测试。

## 16. 第 9 批：技能进度读取去重（已完成）

日期：2026-11-17。先列清单再清理，三级范围为“武器与战斗 → 技能魔法 → 技能进度读取”。源码修改只限 Skills 中八个文件；最大文件 `ColdSteelSkillModel.cpp` 当前为 743 行，仍低于 800 行边界，本批仅改其中 `QuickCombatProgress` 的一行函数体。

### 先列清单，再实施的修改

| 文件 | 修改前行数 | 修改后行数 | 函数与原查询键 | 实际修改 |
| --- | ---: | ---: | --- | --- |
| `Skills/ColdSteelIceSpikeModel.cpp` | 133 | 133 | `IceSpikeProgress` / `IceSpikeSkill.Id` | 返回 `Current.Skills.FindRef` 的结果。 |
| `Skills/ColdSteelLightningModel.cpp` | 141 | 141 | `LightningProgress` / `LightningSkill.Id` | 同上。 |
| `Skills/ColdSteelHolyLightModel.cpp` | 141 | 141 | `HolyLightProgress` / `HolyLightSkill.Id` | 同上。 |
| `Skills/ColdSteelIceWallModel.cpp` | 143 | 143 | `IceWallProgress` / `IceWallSkill.Id` | 同上。 |
| `Skills/ColdSteelElectricMagicModel.cpp` | 92 | 92 | `ElectricMagicProgress` / 原传入 `Id` | 同上，不改成技能定义的回退 ID。 |
| `Skills/ColdSteelFireMagicModel.cpp` | 146 | 146 | `FireMagicProgress` / 原传入 `Id` | 同上，不新增技能 ID 过滤。 |
| `Skills/ColdSteelBlizzardModel.cpp` | 122 | 122 | `BlizzardProgress` / `TEXT("blizzard")` | 同上，保留原字符串键。 |
| `Skills/ColdSteelSkillModel.cpp` | 743 | 743 | `QuickCombatProgress` / `QuickCombatSkill.Id` | 仅替换该查询函数体，其余训练及伤害代码不动。 |

### 等价依据与保留边界

- 八处原式均为 `Find(Key)` 后返回 `*P`，查无记录时返回 `FColdSteelSkillProgress()`。本机引擎 `Core/Public/Containers/Map.h.inl:661–669` 的单参数 `FindRef` 同样只读查找，存在时返回值副本，缺失时返回 `ValueType()`，不会插入记录。
- `FColdSteelSkillProgress` 原默认值为 Level=1、Experience=0，本批保持这些值、返回类型、const 方法、查询键和返回副本语义，不改公开声明或存档数据。
- `Skills/ColdSteelAdditionalMasteries.cpp` 中的 `MasteryProgress` 会额外判断 `IsLearned` 并在不满足时返回 Level=0，因此它与本批八个入口语义不同，保留原实现与既有调用者，本批不复用它。
- FireMagic/ElectricMagic 仍按实际传入的任意 Id 读取原表；Blizzard 仍用原字面量；不借清理改为定义回退、技能白名单、同步运行时或刷新缓存。
- 修炼同步/提交及施法释放通知由各拥有者控制，本批不合并这些存在门禁和事务差异的流程；奖励公式、角色经验、火球独立缩放、超过 800 行文件和疑似死代码全部保留。
- 为确定复用入口，定向定位了 MasteryProgress 声明/实现及引擎 FindRef 实现；UI 与引擎文件仅作依赖读取，不修改。未逐文件通读全仓，未新增 helper、缓存、功能或测试。

### 构建与恢复

清单先写入本节，再保存八个源码原件并各替换一行函数体；前后行数、字节数、SHA-256 和原件路径见[第 9 批源码清单](code-cleanup-20261116/batch-09-progress-lookup/source-manifest.json)，同目录八个 `*.before.txt` 供按片段恢复。保留原文件换行及已有工作区内容，没有暂存、提交或推送。

执行原 `Tools/Build/Build-Editor.ps1`，`FPSGAMEEditor Win64 Development` 返回 Succeeded，退出码 0，11 个动作，UBT 耗时 20.39 秒。八个修改文件均编译完成，随后链接 `UnrealEditor-FPSGAME.lib`、`UnrealEditor-FPSGAME.dll` 并写入目标元数据。本次为共享工程增量构建，没有另行构建 Game 目标。

本次日志：[build-20261117-122414.log](../../Saved/BuildEditor/build-20261117-122414.log)；结果记录：[第 9 批构建回执](code-cleanup-20261116/batch-09-progress-lookup/build-receipt.json)。源码修改均位于 Skills，未新增 helper、功能、缓存或公开接口；火球独立经验缩放、超长文件、疑似死代码、其他模块和资产未动。未启动编辑器或游戏，未运行测试、lint、审计工具、PIE 或 Commandlet，运行效果交由用户测试。

## 17. 第 10 批：命中批次计数去重（已完成）

日期：2026-11-17。按用户要求先列清单再清理。三级范围为“武器与战斗 → 技能魔法 → 命中批次计数”，源码只限 Skills 内六个文件，全部不超过 800 行。本批读取聚焦玩家命中确认后的计数段、奖励结构及 `IsDead` 声明/实现依赖，不通读全仓。

### 先列清单，再实施的修改

| 文件 | 修改前行数 | 修改后行数 | 实际修改与保留门禁 |
| --- | ---: | ---: | --- |
| `Skills/ColdSteelHolyLightModel.cpp` | 141 | 140 | 两行计数改为同一 helper 调用；保留 `bTrain`、Summoned 和 NoSkillTraining 条件。 |
| `Skills/ColdSteelIceSpikeModel.cpp` | 133 | 132 | 同上，调用仍位于训练目标排除的早退之后。 |
| `Skills/ColdSteelLightningModel.cpp` | 141 | 140 | 同上，保留 `bTrain` 与目标标签判断。 |
| `Skills/ColdSteelFireMagicModel.cpp` | 146 | 145 | 同上，保留两类不训练目标的排除；不影响原即时角色奖励。 |
| `Skills/ColdSteelBlizzardModel.cpp` | 122 | 121 | 同上，保留原命中与训练目标门禁。 |
| `Skills/ColdSteelSpellRewards.h` | 59 | 73 | 增加 `RecordTrainingHit`，接收原批次、原战斗组件 const 引用及暴击标志；显式包含既有 `MonsterCombatComponent.h`。 |

五处原段都是先 `++Hits`，再查询死亡状态决定 `++Kills`；暴击时 `++CriticalHits`，随后再次查询死亡状态决定 `++CriticalKills`。helper 按原顺序执行这些语句，正常命中仍查询一次死亡状态、暴击命中仍查询两次；不缓存为单个死亡布尔值，也不复用命中反馈之前读取的 `HitResult.bKilled`。

### 本批保留边界

- 五种奖励结构已有四个 int32 计数字段，因此用一个内部函数模板接收原批次；不新增奖励结构、状态字段、反射接口或玩法能力。
- 调用仍在原伤害、附加状态、命中反馈及训练资格判断之后；玩家/权威/友军、无伤害早退、训练目标排除等都留在原函数。
- UnknownSpell 敌人施法分支仍保留原 `if(Applied)++Batch.Hits`，不接入玩家的击杀/暴击计数规则；冰墙与箭雨的不同计数入口也不改。
- helper 不修改 KillRewards、bMultiHit 或角色档案，不提交训练、不登记 RewardedVictims；前八批的计算函数体保持原样。
- 圣光治疗、冰锥击墙、雷击眩晕、火系燃烧和暴风雪寒冷逻辑不动。其他修炼提交、冷却预留、释放通知也仍由各自入口维护。
- 火球及独立经验缩放、超过 800 行的文件、疑似死代码、Skills 以外业务源码和资产不动。怪物战斗组件仅作为已有依赖读取，不修改其实现。

### 构建与恢复

清单先写入本节，再保存六个源码原件并实施。五个调用点各减少一行，公共头文件由 59 行增至 73 行，修改后最大文件为 145 行。前后行数、字节数、SHA-256 和原件路径见[第 10 批源码清单](code-cleanup-20261116/batch-10-hit-counters/source-manifest.json)，同目录六个 `*.before.txt` 供按片段恢复。保留原文件换行及已有工作区内容，没有暂存、提交或推送。

执行原 `Tools/Build/Build-Editor.ps1`，`FPSGAMEEditor Win64 Development` 返回 Succeeded，退出码 0，12 个动作，UBT 耗时 20.26 秒。五个本批模型和四个共用头文件的其他消费者均重新编译，随后完成 `UnrealEditor-FPSGAME.lib`、`UnrealEditor-FPSGAME.dll` 链接与目标元数据写入。本次为共享工程增量构建，没有另行构建 Game 目标。

本次日志：[build-20261117-135808.log](../../Saved/BuildEditor/build-20261117-135808.log)；结果记录：[第 10 批构建回执](code-cleanup-20261116/batch-10-hit-counters/build-receipt.json)。本批源码只修改 Skills 内六个文件，没有新增功能、公开接口或状态。火球独立经验缩放、超过 800 行文件、疑似死代码、其他模块和资产未动。未终止占用进程，未启动编辑器或游戏，未运行测试、lint、审计工具、PIE 或 Commandlet；构建结果不代表运行效果，交由用户测试。

## 18. 第 11 批：命中反馈与奖励表合并去重（已完成）

日期：2026-11-17。沿用用户上一批边界，先列清单再清理。三级范围为“武器与战斗 → 技能魔法 → 命中反馈与奖励收集”，仅修改 Skills 内六个模型并新增一个内部公共头文件。原有待改文件均不超过 800 行；不逐文件通读仓库。

### 先列清单，再实施的修改

| 文件 | 修改前行数 | 修改后行数 | 实际修改 |
| --- | ---: | ---: | --- |
| `Skills/ColdSteelHolyLightModel.cpp` | 140 | 135 | 命中反馈改为公共调用；奖励表逐键复制改为 `Append`。 |
| `Skills/ColdSteelIceSpikeModel.cpp` | 132 | 127 | 同上；保留冰墙分支、寒冷处理与训练目标早退。 |
| `Skills/ColdSteelLightningModel.cpp` | 140 | 135 | 同上；反馈仍在雷锤确认、眩晕处理之后。 |
| `Skills/ColdSteelFireMagicModel.cpp` | 145 | 140 | 仅提取命中反馈段；保留即时角色奖励与燃烧处理。 |
| `Skills/ColdSteelBlizzardModel.cpp` | 121 | 116 | 仅提取命中反馈段；保留寒冷处理和原计数。 |
| `Skills/ColdSteelMagicArrowRainModel.cpp` | 114 | 114 | 仅提取命中反馈段；保留范围遍历、遮挡判断及局部计数。 |
| `Skills/ColdSteelSpellFeedback.h` | 新增 | 21 | 一个内部 `NotifyHit` 函数，复用原 `FWeaponDamageResult` 和 `NotifyConfirmedWeaponHit`，不新增玩法或公开反射接口。 |

### 合并依据与保留边界

- 六处反馈都默认构造 `FWeaponDamageResult`，依次设置 `bResolved=true`、原暴击标志和 `Combat->IsDead()`，再 Cast 为 `AFPSGAMECharacter` 并传入原 Target、Applied 和结果地址。公共函数原样执行；即使 Cast 不成功，死亡查询仍在它之前发生，不能提前返回或复用训练阶段的死亡值。
- 每个反馈调用仍在原伤害及该法术附加状态之后、训练资格与计数之前。角色通知的默认参数不改，训练反馈后的再次死亡查询、敌人施法分支和原事务顺序保持原样。
- 三处奖励表源、目标均为 `TMap<TWeakObjectPtr<AActor>,int64>`。本机引擎 `Core/Public/Containers/Map.h.inl:1365–1373` 的 const `Append` 重载复制来源键值，同键使用来源值；来源表不清空、不移动，符合原 `FindOrAdd(K.Key)=K.Value` 的结果。它会按两表数量预留容量，这是容器实现差异，不改变奖励规则。
- 三处合并位置仍在 `CrystalRecovery.Finish(Applied)` 之后、`Applied<=0` 早退之前，不改变收集器作用域、角色经验缩放、去重登记、训练提交或弱指针处理。
- 箭雨的局部计数与前批批次计数结构不同，保留其原实现。冰甲、雷迅的训练提交及不同施法门禁不合并；本批不增加新的状态管理层。
- 火球独立经验缩放、超过 800 行文件、疑似死代码、其他模块源码、规则文件和资产不动。引擎容器及角色/战斗类型只作必要依赖读取，不修改。保留工作区原内容和换行，不暂存、提交或推送。

### 构建与恢复

清单先写入本节，再保存六个源码原件并实施。本批修改六个模型、新增一个 21 行公共头文件，修改后最大文件 140 行。前后行数、字节数、SHA-256 及原件路径见[第 11 批源码清单](code-cleanup-20261116/batch-11-hit-feedback/source-manifest.json)，同目录六个 `*.before.txt` 用于按片段恢复。新头文件在清单中记录为此前不存在；恢复时须同时处理其调用点，不能直接删除仍被引用的文件，也不能整文件覆盖后续并行修改。保留原换行及已有工作区内容，没有暂存、提交或推送。

提交构建前读取当前构建进程占用，没有占用才执行原 `Tools/Build/Build-Editor.ps1`。`FPSGAMEEditor Win64 Development` 返回 Succeeded，退出码 0，9 个动作，UBT 耗时 17.35 秒。六个模型均重新编译，随后完成 `UnrealEditor-FPSGAME.lib`、`UnrealEditor-FPSGAME.dll` 链接与目标元数据写入。本次为共享工程增量构建，没有另行构建 Game 目标。

本次日志：[build-20261117-140401.log](../../Saved/BuildEditor/build-20261117-140401.log)；结果记录：[第 11 批构建回执](code-cleanup-20261116/batch-11-hit-feedback/build-receipt.json)。源码改动全部位于 Skills，没有新增功能、反射接口或状态。火球独立经验缩放、超过 800 行文件、疑似死代码、其他模块和资产未动。未终止进程，未启动编辑器或游戏，未运行测试、lint、审计工具、PIE 或 Commandlet；构建成功不代表运行效果，交由用户测试。

## 19. 第 12 批：法杖公共词条读取去重（源码与 Game/Editor 构建完成）

日期：2026-11-17。先列清单再清理，三级范围为“武器与战斗 → 技能魔法 → 法杖词条读取”。源码只限 Skills 内六个模型和一个新增内部头文件，原有待改文件均不超过 800 行。语义读取聚焦施法数值中的法杖分支、字段类型和词条查询声明，没有通读全仓。

### 先列清单，再实施的修改

| 文件 | 修改前行数 | 修改后行数 | 实际修改 |
| --- | ---: | ---: | --- |
| `Skills/ColdSteelHolyLightModel.cpp` | 135 | 134 | 两处调用替代暴击/穿透、连锁/施法加速的重复表达式。 |
| `Skills/ColdSteelIceSpikeModel.cpp` | 127 | 126 | 同上；保留原投射物数量、伤害与寒冷词条。 |
| `Skills/ColdSteelLightningModel.cpp` | 135 | 134 | 同上；保留连锁目标数、眩晕及电系专精。 |
| `Skills/ColdSteelFireMagicModel.cpp` | 140 | 139 | 同上；保留火系伤害、燃烧与独立冷却算法。 |
| `Skills/ColdSteelBlizzardModel.cpp` | 116 | 115 | 同上；保留寒冷词条、伤害与冷却 Clamp。 |
| `Skills/ColdSteelIceWallModel.cpp` | 143 | 143 | 只替换连锁/施法加速读取；保留物理伤害语义。 |
| `Skills/ColdSteelSpellCrafting.h` | 新增 | 27 | 两个内部模板函数，接收现有施法结构、强化系统和物品 const 引用，只写入对应字段。 |

### 等价依据与保留边界

- 五处暴击表达式相同：原 CriticalChance 加上 `100*(Effect(critRate)+CraftEffect(critChancePercent)+CraftEffect(magicCritPercent))`；穿透仍直接赋值 `Effect(magicPenetrationPercent)+CraftEffect(magicPenetrationPercent)`。两个查询接口返回 double，目标字段均为 float；不改变括号、赋值方式、百分比单位或默认参数。
- 六处连锁/加速表达式相同，依次写入 `bGrantChain`、`CastHasteStacks`、`CastHasteDuration`。保留非零判断、double 到 int32 的原转换、时长缺省 5000 与除数 1000；不缓存、不新增上下限、不改为累计叠加。
- 每处新调用都留在原位置，使用当前原 Item 与 E；法杖类型判断、子系统获取、技能基础值、已有 lambda 的其他用途及字段读取次数均保留。不将不同位置的读取前移为统一预计算。
- 冰墙只有连锁/加速这组公共字段，本批不赋予魔法暴击或穿透。ElectricMagic 继续通过原 `LightningStats` 获取基础数据，不增加第二次词条应用；火球文件及其独立经验缩放不动。
- 冷却、范围、伤害系数、元素专精和施法速度取值存在精度、顺序或限幅差异，本批不合并。冰甲/雷迅的施法门禁及训练提交保留；奖励、命中反馈和训练计数函数不动。
- 超过 800 行文件、疑似死代码、Skills 以外业务源码、规则及资产不修改。强化系统声明与性能约束仅作依赖读取，继续沿现有查询入口；不增加缓存、磁盘读取或运行时调度。

### 构建与恢复

清单先写入本节，再保存六个源码原件并实施。本批修改六个模型、新增一个 27 行公共头文件，修改后最大文件 143 行。前后行数、字节数、SHA-256 及原件路径见[第 12 批源码清单](code-cleanup-20261116/batch-12-staff-crafting/source-manifest.json)，同目录六个 `*.before.txt` 用于按片段恢复。新头文件记录为此前不存在；恢复须连同调用点处理，不能直接删除仍被引用的文件，也不能整文件覆盖后续并行修改。保留原换行和工作区内容，没有暂存、提交或推送。

提交构建前未发现现有 UBT/编译/链接进程，随后原 `Tools/Build/Build-Editor.ps1` 因已运行的项目 `UnrealEditor.exe`（PID 52092）在调用 UBT 前阻止构建。本批没有关闭、重启或接入该编辑器，也没有绕过 DLL 占用保护。[Editor 构建尝试记录](code-cleanup-20261116/batch-12-staff-crafting/editor-build-attempt.json) 保留该次返回和原因。

确认当时没有运行 FPSGAME 可执行文件后，改为独立 `FPSGAME Win64 Development` 后台构建，返回 Succeeded、退出码 0，8 个动作，UBT 耗时 52.81 秒。六个修改模型均编译，随后链接 `Binaries/Win64/FPSGAME.exe` 并写入目标元数据。该 Game 构建不替换已加载的 Editor DLL，也没有启动游戏。当时 Game 构建结束后，项目编辑器 PID 52092 仍在运行，因此未再次提交 Editor 构建。2026-11-17 17:17 共享构建和项目模块占用退出后，本批与第 13–15 批统一完成 Editor 构建收尾，独立 UBT 调用返回 Succeeded、目标已是最新，0 个动作；最终回执见第 24 节，原占用与 Game 记录保留。

本次日志：[cleanup-batch12-20261117-151403.log](../../Saved/BuildGame/cleanup-batch12-20261117-151403.log)；结果记录：[第 12 批构建回执](code-cleanup-20261116/batch-12-staff-crafting/build-receipt.json)。源码改动全部位于 Skills，没有新增功能、反射接口、缓存或状态。火球独立经验缩放、超过 800 行文件、疑似死代码、其他模块和资产未动。未终止进程，未启动编辑器或游戏，未运行测试、lint、审计工具、PIE 或 Commandlet；Game 与后续 Editor 构建分别留存证据，均不代表运行效果已验证，交由用户测试。

## 20. 后续批次统一清单（源码与 Editor 构建已完成）

日期：2026-11-17。用户要求后续批次连续做完后统一汇报，继续沿用 Skills、800 行上限、不碰疑似死代码、不改火球独立经验缩放、不加功能、不测试的范围。本次先按功能定位剩余重复，不把每个单行 getter、配置常量或类型声明机械包装成函数，也不逐文件通读仓库。

| 批次 / 候选 | 最多三级职责 | 实施清单 | 保留条件 |
| --- | --- | --- | --- |
| 13 / C17 | 武器与战斗 → 技能魔法 → 数值读取 | 八处连锁层数读取共用 `ColdSteelSpellCrafting::ChainSpellStacks`；四处法杖专精 JSON 判断共用 `HasStaffSpecialty`；移除本批替换后不再直接使用的 include。 | 当前 Pawn/装备、原空值回退、原读取位置、原专精文本比较不变；魔耗与伤害公式不改。 |
| 14 / C18 | 武器与战斗 → 技能魔法 → 施法模型选择 | 九个组件的相同 Model() 分支复用现有 `NetCastUtils.h` 中的 `LocalModel`。 | 敌人模型优先，普通分支仍取 GameInstance 单例；不改为影子权威模型、不改变空 World/GI 回退，不移动退款/提交。 |
| 15 / C19 | 武器与战斗 → 技能魔法 → 表现生命周期 | 雷迅表现的两处解除骨骼 tick 前置依赖循环共用私有 `ClearLimbTickPrerequisites`。 | 保留弱指针有效性判断、Mesh 后 Leader 的移除顺序，以及清理/重新解析各自原调用位置。 |

### 精确源码范围（修改前行数）

- 第 13 批：`ColdSteelSpellCrafting.h` 27；HolyLightModel 134、IceSpikeModel 126、LightningModel 134、FireMagicModel 139、BlizzardModel 115、IceWallModel 143、ElectricMagicModel 92（模型文件均带 `ColdSteel` 前缀及 `.cpp` 后缀）；`ColdSteelSpellMana.cpp` 69。共九个已有文件，不新增文件。
- 第 14 批：`NetCastUtils.h` 46；`FPSHolyLightComponent.cpp` 258、`FPSLightningComponent.cpp` 299、`FPSIceSpikeComponent.cpp` 256、`FPSIceWallComponent.cpp` 339、`FPSBlizzardComponent.cpp` 390、`FPSElectricMagicComponent.cpp` 681、`FPSFireMagicComponent.cpp` 714、`FPSIceArmorComponent.cpp` 225、`FPSLightningHasteComponent.cpp` 216。共十个已有文件。
- 第 15 批：`LightningHastePresentation.cpp` 177、`FPSLightningHasteComponent.h` 79。共两个已有文件，不增加反射声明、字段或布局。
- 超长保留：Skills 当前 `ColdSteelSkillRules.cpp` 973 行、`FPSQuickCombatComponent.cpp` 813 行，只保留初始拆分方案，不修改；火球专属文件、诊断工具和疑似死代码不参与本次替换。

### 同批明确保留的相似实现

| 功能组 / 定向入口 | 处置原因 |
| --- | --- |
| 武技：DashAttack、Whirlwind、ChainSlash、LeapStrike、HeavyStrike 的训练/提交 | 支付事务与重击经验档位确有差异；第 25 节检查发现 DashAttack/Whirlwind 训练重复，以及 ChainSlash/LeapStrike 的局部训练和回执重复。前者列 P01，后者列 H01/H02；不再把整个组一概归为行为不同，原事务本轮均未改。 |
| 施法状态：准备、取消、退款、释放与网络应答 | 冰锥分相位、冰墙预留、火甲/领域持有奖励模型等时点不同，不统一完整状态机；圣光/雷击回执的重复已在第 25 节列 H03，保留理由是抽取成本，不能称其回执本身不同。 |
| 目标与地面：HolyLight、Lightning、MagicOcclusion、MeteorGround、MagicArrowRainGround、FireMagicArea | 圣光友疗和单射线、雷击多点暴露、玻璃及开放栏杆、落点验证和箭雨飞行净空不同；现有共享 Trace/Validate 已在用，保留各自筛选和边界。 |
| 数值：冷却、元素伤害/专精、技能树/专精等级 | 四个法术同型的冷却倍率尾段已在第 25 节列 P02；其余 float/double 转换、Clamp、取整和基础冷却差异保留。未学习等级 0 与缺省等级 1 不互换，树学习与训练持久化不合并。 |
| 表现/资源：IceArmorPresentation、LightningHastePresentation、PlayerSkillRenderPreparation 及投射物支持 | 冰甲部位隐藏与雷迅骨骼来源、实例销毁与共享准备宿主职责不同；只合并第 15 批完全相同的循环，其余资源生命周期和既有诊断保留。 |
| 一行访问器、常量、类型与伤害标识 | 相似语法不是独立可删除业务逻辑；为它们增加参数化包装会扩大依赖，保留原表达和身份。 |

清单先写入，再逐批保存原件、实施等价替换；全部源码落盘后统一作必要后台构建，避免每个小批反复构建。构建结果不作为运行验收，未授权测试不执行。

## 21. 第 13 批：连锁状态与法杖专精查询（已完成）

日期：2026-11-17。清单已先记于第 20 节，之后保存原件并实施。八处连锁层数读取和四处法杖专精判断已合并到现有 `ColdSteelSpellCrafting.h`。所有调用保留原 RuntimePawn/Item 与调用位置；空 Pawn 或无状态组件仍返回 0，专精判断沿原只读 JSON、原键名及字符串比较。共享魔耗文件只替换连锁状态查询，原技能分支、焦点/装备倍率及火球相关魔耗公式全部保留；火球独立经验缩放不涉及。四个专精调用文件中仅移除了本批替换后失去直接用途的 CombatItemFormula/JsonObject include；ElectricMagic 和 SpellMana 移除同样失去直接用途的 CombatStatusFormula include。没有删除疑似死代码。

| Skills 内文件 | 修改前行数 | 修改后行数 |
| --- | ---: | ---: |
| `ColdSteelHolyLightModel.cpp` | 134 | 129 |
| `ColdSteelIceSpikeModel.cpp` | 126 | 121 |
| `ColdSteelLightningModel.cpp` | 134 | 129 |
| `ColdSteelFireMagicModel.cpp` | 139 | 137 |
| `ColdSteelBlizzardModel.cpp` | 115 | 113 |
| `ColdSteelIceWallModel.cpp` | 143 | 141 |
| `ColdSteelElectricMagicModel.cpp` | 92 | 87 |
| `ColdSteelSpellMana.cpp` | 69 | 67 |
| `ColdSteelSpellCrafting.h` | 27 | 45 |

[第 13 批源码清单](code-cleanup-20261116/batch-13-spell-lookups/source-manifest.json) 包含前后字节数、SHA-256 和原件路径；同目录 `*.before.txt` 按片段恢复，保留后续并行修改。原换行保留，没有暂存、提交或推送。三批统一构建，结果记于第 24 节。

## 22. 第 14 批：组件模型选择（已完成）

日期：2026-11-17。清单已先记于第 20 节，之后保存原件并实施。九个 Model() 入口共用 `NetCast::LocalModel(const UActorComponent&)`。它按原短路顺序先处理 UnknownSpell，再判断 World 和 GameInstance；没有把 World/GI 查询提前到敌人分支，没有增加影子档案选择。`AuthorityModel`、`ColdSteelAuthority::ForPawn` 及弓系组件仍保持原样，发送请求、网络相位、支付/退款和奖励模型生命周期全部保留。原九个 .cpp 已包含 NetCastUtils，不新增反射接口或组件字段。

| Skills 内文件 | 修改前行数 | 修改后行数 |
| --- | ---: | ---: |
| `FPSHolyLightComponent.cpp` | 258 | 257 |
| `FPSLightningComponent.cpp` | 299 | 298 |
| `FPSIceSpikeComponent.cpp` | 256 | 255 |
| `FPSIceWallComponent.cpp` | 339 | 338 |
| `FPSBlizzardComponent.cpp` | 390 | 389 |
| `FPSElectricMagicComponent.cpp` | 681 | 680 |
| `FPSFireMagicComponent.cpp` | 714 | 713 |
| `FPSIceArmorComponent.cpp` | 225 | 224 |
| `FPSLightningHasteComponent.cpp` | 216 | 215 |
| `NetCastUtils.h` | 46 | 58 |

[第 14 批源码清单](code-cleanup-20261116/batch-14-component-models/source-manifest.json) 包含前后字节数、SHA-256 和原件路径；同目录 `*.before.txt` 按片段恢复，保留后续并行修改。原换行保留，没有暂存、提交或推送。三批统一构建，结果记于第 24 节。

## 23. 第 15 批：雷迅表现依赖解除（已完成）

日期：2026-11-17。清单已先记于第 20 节，之后保存原件并实施。两处相同的 LimbMeshes 遍历提取为现有组件的私有非反射方法 `ClearLimbTickPrerequisites`。ClearVisuals 与 ResolveLimbSources 都在原位置调用，仍逐项判断弱指针，先移除 Mesh 前置依赖，再移除 Leader 前置依赖。没有改变数组清空/重建、骨骼选择、Tick 组、Niagara、声音或时序。头文件只新增一个私有方法声明，不新增字段或对象布局。

| Skills 内文件 | 修改前行数 | 修改后行数 |
| --- | ---: | ---: |
| `LightningHastePresentation.cpp` | 177 | 178 |
| `FPSLightningHasteComponent.h` | 79 | 80 |

[第 15 批源码清单](code-cleanup-20261116/batch-15-limb-prerequisites/source-manifest.json) 包含前后字节数、SHA-256 和原件路径；同目录 `*.before.txt` 按片段恢复，保留后续并行修改。原换行保留，没有暂存、提交或推送。三批统一构建，结果记于第 24 节。

## 24. 统一收尾（源码与 Editor 构建均已完成）

第 20 节先列的 C17–C19 均已实施，后续第 13–15 批无待实施源码项，不再把单行访问器或有合同差异的流程拆成新的清理批次。本轮修改 21 个已有 Skills 文件，最大修改后文件 713 行；没有新增源码文件、公开反射接口、字段、缓存或功能。其他模块、资产、规则文件、火球独立经验缩放、两个超长 Skills 源文件与疑似死代码均保留。上述完成范围是本轮功能清单，不是“整个仓库已没有重复”的声明。

三批源码原件、行数/字节数及散列已分别记录于第 21–23 节链接。所有编辑基于修改时的工作区内容，保留原换行与并行修改，没有暂存、提交、推送、清理中间产物或删除生产文件。

此前一次统一构建开始时未发现其他编译器或项目编辑器，原 `Tools/Build/Build-Editor.ps1` 启动 Editor 构建。日志为 [build-20261117-152948.log](../../Saved/BuildEditor/build-20261117-152948.log)，计划 48 个动作；UHT 没有写入生成文件，返回输出完成到 21/48 后长时间没有新进度。本会话仅对自己的 exec 会话发送 Ctrl+C，中止这一轮构建，未报告成功。之后观察到另一轮共享 Editor 构建（日志 `build-20261117-153534.log`）已取得引擎锁，因此等待，不抢锁、不终止其他构建、不向其他对话协调。一次对原残留编译器的身份保护判断未匹配，没有执行强制终止。[本轮构建尝试记录](code-cleanup-20261116/remaining-batches-build-attempt-20261117.json) 保留具体状态。

上一次续办结束时，后续源码批次已完成，但 Editor 构建尚未收尾；当时没有在另一轮共享构建期间重试，只结束了本会话的被动等待进程，原残留编译器随后已不存在，没有强制停止进程。上述为历史状态，原尝试记录保留；最终结果以下述本次收尾为准。其余保留项已按第 20 节列明原因，不是遗漏的待清理批次。

### 本次 Editor 构建收尾（2026-11-17 17:17）

按本次用户要求，持续等待已有共享 Game/Editor 构建和项目后台模块使用者正常退出，没有抢锁、终止进程或向其他对话发送协调消息。等待期间两项共享 Editor 构建分别返回 Succeeded（826 个动作、1716.71 秒；4 个动作、22.76 秒），之后两项共享 Game 构建也结束；项目后台操作使用 Editor 模块时，前置门禁继续阻止本轮启动。

17:17:16 确认没有构建或项目 Editor 模块占用后，直接调用同一引擎的 `Build.bat FPSGAMEEditor Win64 Development`，使用 `-NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=2`，未修改构建脚本或共享配置。17:17:28 返回 **Succeeded，退出码 0，UBT 耗时 11.29 秒**。UBT 明确返回 **Target is up to date，0 个动作**：本次没有重新编译、链接 DLL 或写入目标元数据；这是占用结束后的独立 Editor 目标调用结果，并非沿用第 12 批 Game 构建作为完成依据。

第 12–15 批的 Editor 待办现已全部收尾。本次续办只执行必要后台构建并更新文档回执，没有新增源码修改、功能或测试，没有启动编辑器、游戏、PIE 或 Commandlet，也未运行 lint、静态检查或审计工具。运行效果仍由用户测试。

本次日志：[cleanup-finalization-20261117-171716.log（本机归档位置）](../Publication/CodeSkillCleanup20261118/archive-manifest.json)；最终回执：[Editor 构建收尾回执](code-cleanup-20261116/editor-finalization-20261117.json)。第 12 批 Game 记录和此前失败/占用记录保留历史状态，第 13–15 批回执及统一状态已指向本次成功结果。

统一状态记录：[后续批次收尾记录](code-cleanup-20261116/remaining-batches-completion-20261117.json)。

## 25. Skills 保留项与 C04 定向检查（仅检查，未改源码）

日期：2026-11-17。用户明确选择“本批 Skills 保留项，以及报告中明确列出的疑似死代码调用链”。先列 R01–R09 清单，再按功能入口检查；未扩大到其余 46 个超长文件，未检查/清理插件 C06，火球独立经验缩放继续排除。

| 类别 | 结果 | 处置 |
| --- | --- | --- |
| 两个超长文件 | ColdSteelSkillRules.cpp 仍为 973 行；FPSQuickCombatComponent.cpp 仍为 813 行。每个给出三个实现单元的具体方法边界、依赖与预计规模。 | 只更新拆分方案，不移动方法或改反射类型。 |
| C04 兼容 RPC | 未找到手写发起调用；主要同步已用身体快照 RPC，但原入口仍生成并注册，且有复制状态副作用。 | 保留“疑似”，未证明可以删除。 |
| 两组优先候选 | P01：DashAttack/Whirlwind 训练重复；P02：HolyLight/IceSpike/Lightning/IceWall 四处同型冷却倍率尾段。 | 检查后由用户授权第 16 批实施，源码及 Editor 构建已完成，见第 26 节；保留整数加法次序、两次 float 赋值舍入和原调用位置。 |
| 三组确认重复但暂保留 | H01：ChainSlash/LeapStrike 训练骨架；H02：两者回执主体；H03：HolyLight/Lightning 回执。 | 修正旧“整组行为不同”的笼统理由；避免为局部重复增加私有状态转发或通用状态机。 |
| 必须保留的差异 | 支付与取消时点、目标友敌/治疗、遮挡采样、坡度及箭雨净空、等级缺省、数值精度/限幅、表现与后台准备所有权。 | 逐项证据见详细检查文档，不因相似语法合并。 |

另记录 ColdSteelSkillRules.cpp 的一处重复 include，以及迁移分支一条过时注释（“only <11 reaches here”）；均未修改，尤其不能凭该注释删除旧档兼容逻辑。

详细结果：[Skills 保留项定向检查](code-cleanup-20261116/remaining-skills-review-20261117.md)。该文包含先列清单、函数/行号证据、两个拆分方案、候选优先级和未覆盖边界；[超长文件拆分方案](code-cleanup-20261116/split-plan.md)仅细化对应两项。

第 25 节检查阶段只更新三份文档，没有修改业务源码、资产、规则或构建配置；没有编译、测试、运行 Commandlet 或启动编辑器。此前第 1–15 批及 Editor 构建完成状态保持，当时新候选尚未实施；后续授权实施结果见第 26 节。仍不宣称 C04 已证明为死代码或全部保留实现已经运行验收。

## 26. 第 16 批：两组优先去重（已完成）

日期：2026-11-17。用户明确要求实施检查报告中的 P01/P02，继续仅限 Skills、不动超过 800 行文件、疑似死代码和火球独立经验缩放，不加功能、不测试。以下清单在修改源码前写入。

| 项目 | 最多三级职责 | 精确实施清单 | 保留边界 |
| --- | --- | --- | --- |
| P01 / C20 | 武器与战斗 → 技能魔法 → 武技训练计算 | DashAttack、Whirlwind 的 XP 计算调用现有 ColdSteelSpellRewards.h 新增的 MartialHitTrainingExperience。 | 保留 int32 的“命中 + 多目标 + 击杀”顺序、Hits>=2、XP/满级早退及原 SyncRuntime/Snapshot/AddExperience/StageTraining；不新增使用或多杀奖励，不改支付和冷却事务。 |
| P02 / C21 | 武器与战斗 → 技能魔法 → 法术冷却倍率 | HolyLight、IceSpike、Lightning、IceWall 的冷却尾段调用现有 ColdSteelSpellCrafting.h 新增的 ApplyCooldownMultipliers。 | 输入沿原 double 类型，分别对 float Cooldown 作两次 *=；SetEffect 在原调用点读取一次，符文乘积沿原 double；不合成一次乘法、不新增 Clamp、不改基础冷却。 |

### 精确源码范围（修改前）

| Skills 内文件 | 行数 | 字节 |
| --- | ---: | ---: |
| `ColdSteelDashAttackModel.cpp` | 99 | 6412 |
| `ColdSteelWhirlwindModel.cpp` | 81 | 4312 |
| `ColdSteelHolyLightModel.cpp` | 129 | 8162 |
| `ColdSteelIceSpikeModel.cpp` | 121 | 7558 |
| `ColdSteelLightningModel.cpp` | 129 | 8553 |
| `ColdSteelIceWallModel.cpp` | 141 | 8430 |
| `ColdSteelSpellRewards.h` | 73 | 2879 |
| `ColdSteelSpellCrafting.h` | 45 | 1828 |

共八个已有源码文件，不新增源码文件；不修改 UI 的私有模型接口、组件字段或反射声明。FireMagic 的 float 冷却减法、Blizzard/ElectricMagic 的 Clamp、H01–H03、C04、两个超长 Skills 文件及资产继续保留。必要依赖声明只读，不作为可修改范围。

原件按当前工作区逐份保存，保留其他任务的未提交内容和各文件换行。恢复应按本批片段处理，不整文件覆盖后续并行修改。源码完成后进行一次必要后台 Editor 构建；若已有构建或项目编辑器占用则等待，不抢锁、不终止进程，不运行测试或启动 UE。

### 实施与构建结果

源码已完成，共修改八个已有文件，未新增源码文件，修改后最大 142 行。P01 的两个入口共用纯经验计算；原 XP/满级早退、SyncRuntime、Snapshot、AddExperience 和 StageTraining 原样保留。StageTraining 属模型私有接口，本批不为合并提交框架修改 UI 头文件或公开接口。

P02 共用 `ApplyCooldownMultipliers(float&,double,double,double)`：在原语句位置读取一次 SetEffect，传入原 double 符文乘积，helper 内执行原 Max 表达式及第二次 *=。两次赋值回 float 保留，不增加 Clamp，不调整基础冷却或施法加速调用位置。火球、FireMagic、Blizzard、ElectricMagic 和 H01–H03 均未接入。

| Skills 内文件 | 修改前行数 | 修改后行数 |
| --- | ---: | ---: |
| `ColdSteelDashAttackModel.cpp` | 99 | 100 |
| `ColdSteelWhirlwindModel.cpp` | 81 | 82 |
| `ColdSteelHolyLightModel.cpp` | 129 | 130 |
| `ColdSteelIceSpikeModel.cpp` | 121 | 121 |
| `ColdSteelLightningModel.cpp` | 129 | 130 |
| `ColdSteelIceWallModel.cpp` | 141 | 142 |
| `ColdSteelSpellRewards.h` | 73 | 79 |
| `ColdSteelSpellCrafting.h` | 45 | 53 |

[第 16 批源码清单](code-cleanup-20261116/batch-16-training-cooldown/source-manifest.json) 保存前后行数、字节数、SHA-256 与八份当前工作区原件路径；恢复按本批片段处理，不覆盖之后的并行修改。没有暂存、提交、推送或删除生产文件。

必要 Editor 构建先被动等待共享 Game 构建（原 cmd PID 79952 / UBT PID 67728）退出，随后因项目 UnrealEditor.exe PID 74112（18:32 启动）继续等待。用户在当前对话选择“我保存并关闭编辑器，继续后台编译”；观察到占用释放后，于 18:43:49 启动本批 FPSGAMEEditor Win64 Development 构建，使用 -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=2，未修改共享构建配置。

19:02:49 返回 **Succeeded，退出码 0，UBT 耗时 1136.17 秒**。本次 **82 个动作全部完成**：79 个编译动作、2 个链接动作（lib / DLL）和 1 个目标元数据动作；六个直接修改的实现文件均有编译记录，已重新链接 UnrealEditor-FPSGAME.dll。UHT 写入 0 个生成文件。构建包含当前共享工作区中其他已变更目标依赖，不代表本批修改了那些源码；本批业务源码修改仍严格限定前述八个 Skills 文件。

本会话未抢锁、未主动终止构建或编辑器进程、未打开编辑器或游戏；没有新增功能、测试、lint、静态检查或运行验收。源码及必要后台构建均已完成，运行效果交由用户测试。日志：[第 16 批 Editor 构建（本机归档位置）](../Publication/CodeSkillCleanup20261118/archive-manifest.json)；[本批构建回执](code-cleanup-20261116/batch-16-training-cooldown/build-receipt.json)。

## 27. 第 17 批：H01–H03 按复杂度筛选（可清理项完成，其余保留）

日期：2026-11-17。用户要求继续处理 H01–H03，只清理能保持行为不变且不增加复杂度的重复逻辑。本批仍仅修改 Skills 源码；超过 800 行文件、疑似死代码、火球独立经验缩放、支付事务和完整施法状态机不动，不加功能、不测试。以下清单在源码修改前写入。

| 编号 | 最多三级职责 | 本批清单 | 保留边界与原因 |
| --- | --- | --- | --- |
| H01 / C22 | 武器与战斗 → 技能魔法 → 武技训练计算 | 两处 XP 表达式共用现有 ColdSteelSpellRewards.h 中的 MartialKillTrainingExperience；传入各自的 MultiKillExperience。 | 保留 int32、“使用 + Max(0,Kills)×击杀 + 多杀”顺序及 Kills>=2；未学/满级判断、SyncRuntime/Snapshot/AddExperience/StageTraining 均留在模型内，不新增泛型事务或公开私有接口。 |
| H02 / C23 | 武器与战斗 → 技能魔法 → 联机冷却回执 | 两处冷却追时算式共用现有 NetCastUtils.h 中的 RemainingCooldown(float,double,double)，只输入冷却、服务器时间戳和当前服务器时间。 | 保留 Revision 门槛内的读时位置、无 GameState 时 Now=ServerAt、double 差值先 Max 再转 float、float 减法后归零；体力合并、耗竭观察、Duration/Revision、Dirty 和广播仍由原回执负责。 |
| H03 / 保留 | 武器与战斗 → 技能魔法 → 圣光与雷击回执 | 不修改 FPSHolyLightComponent / FPSLightningComponent 的 Accepted、Rejected、Cancelled。 | 完整拒绝回执涉及 bNetPaid、bCommitted、LockedTarget、NetPaidMana、bNetResultPending、Hands/Model/Feedback 和退款键；现有无可直接复用的共享入口。共享整段需要状态转发或新基类，拆两三条赋值又增加间接层；不以减少重复为由增加结构。 |

### 精确源码范围（修改前）

| Skills 内文件 | 行数 | 字节 |
| --- | ---: | ---: |
| `ColdSteelChainSlashModel.cpp` | 66 | 3594 |
| `ColdSteelLeapStrikeModel.cpp` | 73 | 3911 |
| `ColdSteelSpellRewards.h` | 79 | 3164 |
| `NetCastUtils.h` | 58 | 2545 |

共四个已有文件，不新增源码文件、反射声明、状态字段、模板或回调。H03 的两个实现文件仅按记录入口读取（257 / 298 行），未修改；未扫描整个仓库或复查疑似死代码链。UppercutStaminaReceipt.h 位于 Multiplayer，只读原有 Merge 合同，不修改。

原件保存为本批目录的四份 .before.txt；恢复应按本批片段处理，不整文件覆盖后续并行修改。前后尺寸记录见[第 17 批源码清单](code-cleanup-20261116/batch-17-h01-h03/source-manifest.json)。

### 实施与构建结果

源码已完成，修改四个已有文件，最大修改后文件 85 行，未新增源码文件。H01 的两处表达式改为 MartialKillTrainingExperience(D,Kills,各自的 MultiKillExperience)，不改未学/满级判断和私有训练提交；H02 仅把两个算式改为 NetCast::RemainingCooldown(Cooldown,ServerAt,Now)，保留原 GetWorld/GetGameState、Now 取值位置及回执全部其他操作。

| Skills 内文件 | 修改前行数 | 修改后行数 |
| --- | ---: | ---: |
| `ColdSteelChainSlashModel.cpp` | 66 | 68 |
| `ColdSteelLeapStrikeModel.cpp` | 73 | 75 |
| `ColdSteelSpellRewards.h` | 79 | 85 |
| `NetCastUtils.h` | 58 | 64 |

H03 及 H01/H02 剩余的状态处理明确保留，不记为整组去重完成。没有把本地取消转调固定 Phase 的网络回执，也没有新增状态容器、共同基类、宏、friend、反射接口或回调来访问私有成员；这些结构成本高于本轮局部收益。火球独立经验缩放、超长文件、疑似死代码、非 Skills 源码、资产与规则未修改。

源码完成后以一次被动门禁等待共享构建。准备期间观察到共享 Game 构建（cmd PID 84716 / UBT PID 44608）；提交门禁时它已退出，接续共享 Editor 构建（cmd PID 92000 / UBT PID 88356，日志 Saved/BuildVillageTree20261117Integrated/Logs/FPSGAMEEditor-build.log）正在运行；其后已有 Game 构建（cmd PID 81112，日志同目录 FPSGAME-build.log）接续，本批继续等待，没有提前启动 UBT 竞争引擎锁。

占用释放后，19:39:01 启动本批 FPSGAMEEditor Win64 Development，使用 -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=2。19:40:55 返回 **Succeeded，退出码 0，UBT 耗时 113.83 秒**。**33 个动作全部完成**：30 个编译动作、2 个链接动作和 1 个目标元数据动作；连斩/跃击实现均有本次编译记录，已重新链接 UnrealEditor-FPSGAME.dll。共享头文件依赖使圣光、雷击等消费者也重新编译，但本批未修改它们的源码；目标中其他工作区依赖的编译不扩大本批四文件修改范围。

本批按清单完成 H01/H02 的纯计算去重及必要构建，剩余状态处理与 H03 明确保留，不将“本批完成”表述为三组全部消除重复。未新增功能，未运行测试、lint、静态检查或运行验收；未抢锁、未主动终止构建/编辑器进程、未联系其他对话、未启动编辑器或游戏。运行效果交由用户测试。

日志：[第 17 批 Editor 构建（本机归档位置）](../Publication/CodeSkillCleanup20261118/archive-manifest.json)；[本批构建回执](code-cleanup-20261116/batch-17-h01-h03/build-receipt.json)。

## 28. 第 18 批：剩余局部复用（已完成）

日期：2026-11-17。用户要求“还有什么能做的继续”，沿用仅 Skills、先列清单、保持行为且不增加复杂度的边界；超过 800 行文件、疑似死代码、火球独立经验缩放不动，不加功能、不测试。本批仅沿已整理的命中反馈、模型读取及冷却公式定位，不逐文件扫描全仓。

| 编号 | 最多三级职责 | 本批清单 | 行为与复杂度边界 |
| --- | --- | --- | --- |
| C24 | 武器与战斗 → 技能魔法 → 冰墙命中反馈 | ColdSteelIceWallModel 的玩家命中反馈复用现有 ColdSteelSpellFeedback::NotifyHit，显式传 false。 | 原 FWeaponDamageResult 的 bCritical 缺省为 false，补显式 false 不增加暴击；保留先死亡查询、再角色 Cast/通知、后训练计数及后续冰缓的顺序；helper 不修改。 |
| C25 | 武器与战斗 → 技能魔法 → 火球模型读取 | FPSFireballComponent::Model 复用现有 NetCast::LocalModel；去掉同文件第二次 FPSCombatHealthComponent.h include 及本次替换后不再直接使用的 UnknownSpellCombat / GameInstance include。 | 保留敌人模型与 GI 单例分支，不改成影子权威模型；火球奖励模型、独立经验缩放、支付、取消和网络相位完全不改。NetCastUtils.h 不修改。 |
| C26 | 武器与战斗 → 技能魔法 → 冰甲与雷迅冷却 | 两处相同公式共用现有 ColdSteelSpellCrafting.h 内的 AuraCooldownMultiplier(float,float,double,double)。 | 先按原 float 做两次减法、乘法和 Max(.2f)，再依原左结合次序乘两个 double 符文倍率；返回 double，调用者仍只对 float Cooldown 做一次 *=。不套用四法术的两次赋值 helper，不预乘符文，不新增 Clamp。 |

### 精确源码范围（修改前）

| Skills 内文件 | 行数 | 字节 |
| --- | ---: | ---: |
| `ColdSteelIceWallModel.cpp` | 142 | 8447 |
| `FPSFireballComponent.cpp` | 649 | 37125 |
| `ColdSteelIceArmorModel.cpp` | 38 | 2638 |
| `ColdSteelLightningHasteModel.cpp` | 49 | 2834 |
| `ColdSteelSpellCrafting.h` | 53 | 2166 |

共五个已有源码文件，不新增源码文件、字段、反射接口、泛型状态结构或回调。Combat/WeaponDamageTypes.h 的 FWeaponDamageResult 声明只读，用于确认默认 bCritical=false；现有通知 helper 和模型 helper 只读复用。原件与尺寸见[第 18 批源码清单](code-cleanup-20261116/batch-18-local-reuse/source-manifest.json)，恢复按本批片段处理，不整文件覆盖后续并行修改。

H01/H02 的剩余私有状态处理与 H03 继续保留；火甲 float 冷却减法、暴风雪/雷暴 Clamp、箭雨冷却及施法支付/生命周期差异不合并。法杖门禁和局部赋值不为单行包装新增接口；有效诊断入口不清理。

### 实施与构建结果

清单中 C24–C26 均已实施，共修改五个已有 Skills 文件，修改后最大 646 行，未新增源码文件。冰墙把原四行反馈构造/通知换成现有 helper，明确传入 false；火球仅把原模型选择分支换成 LocalModel，保留第一次 FPSCombatHealthComponent.h include，移除重复项及本次替换后无直接用途的 UnknownSpellCombat / GameInstance include。火球奖励模型与投射物奖励代码未修改。

冰甲/雷迅在各自原调用位置调用 AuraCooldownMultiplier(Reduction,float(SetEffect(...)),Rune.SkillCooldown,Rune.MagicCooldown)，helper 返回 double；SetEffect 各读取一次，原先 Rune 读取位置未移动。两个 float 减法、float 乘积与 Max(.2f) 之后，按原次序逐个乘 double 符文倍率；调用者保留一次 *= 赋回 float。无新增限幅、条件、字段或状态流程。

| Skills 内文件 | 修改前行数 | 修改后行数 |
| --- | ---: | ---: |
| `ColdSteelIceWallModel.cpp` | 142 | 140 |
| `FPSFireballComponent.cpp` | 649 | 646 |
| `ColdSteelIceArmorModel.cpp` | 38 | 40 |
| `ColdSteelLightningHasteModel.cpp` | 49 | 51 |
| `ColdSteelSpellCrafting.h` | 53 | 60 |

19:46:45 前置门禁未发现已有构建或项目编辑器占用，启动一次 FPSGAMEEditor Win64 Development，参数沿用 -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=2。19:48:00 返回 **Succeeded，退出码 0，UBT 耗时 73.39 秒**；**14 个动作完成**（11 个编译、2 个链接、1 个目标元数据），本批四个直接修改的实现文件均有编译记录，已重新链接 UnrealEditor-FPSGAME.dll。依赖共享头文件的其他消费者重编译不代表本批修改其源码。

本批定位入口中的可清理项已完成，H01/H02 剩余状态处理、H03、不同精度/Clamp/支付/生命周期及其他明确保留项不继续强行包装；不据此宣称整个 Skills 已不存在重复。没有新增功能、测试、lint、静态检查或运行验收；未主动启动编辑器/游戏、未终止进程、未抢锁或跨对话协调，也未暂存、提交、推送或删除生产文件。运行效果由用户测试。

日志：[第 18 批 Editor 构建（本机归档位置）](../Publication/CodeSkillCleanup20261118/archive-manifest.json)；[本批构建回执](code-cleanup-20261116/batch-18-local-reuse/build-receipt.json)。

## 29. 第 19 批：箭雨回执复用与保留项（已完成）

日期：2026-11-17。本批沿用仅 Skills、先列清单、保持行为且不增加复杂度的边界；超过 800 行文件、疑似死代码、火球独立经验缩放不动，不加功能、不测试。仅沿回执冷却、弓系冷却和已有输入入口定位，不逐文件扫描全仓。

| 编号 | 最多三级职责 | 本批清单 | 保留边界与原因 |
| --- | --- | --- | --- |
| C27 / 实施 | 武器与战斗 → 技能魔法 → 箭雨资源回执 | MagicArrowRainResources::Apply 的冷却追时算式直接调用已有 NetCast::RemainingCooldown(R.Cooldown,R.CapturedAt,Now)。 | 只改表达式及加入所需 include；helper 不改。保留 Revision 门槛、服务器时间读取位置与无 GameState 时的本地时间回退，以及 double 差值归零、转 float、float 减法再归零顺序。 |
| R10 / 保留 | 武器与战斗 → 技能魔法 → 弓系冷却 | 照明箭和箭雨同型的一行冷却倍率暂保留。 | 无同合同现有入口；不为单行公式另加包装，也不传虚拟零参数套用冰甲/雷迅公式。只记录局部重复，不声称两者此公式行为不同。 |
| R11 / 保留 | 武器与战斗 → 技能魔法 → 预览输入 | 冰墙/暴风雪的 InputAvailable 分支同型，保留各自方法。 | 当前没有可直接复用的输入入口；不把输入门禁塞进轨迹绘制或网络工具，也不为两处建立新状态框架。陨星及弓系的继续输入条件另有差异，不统一。 |

### 精确源码范围（修改前）

| Skills 内文件 | 行数 | 字节 |
| --- | ---: | ---: |
| `MagicArrowRainResources.cpp` | 34 | 2250 |

只修改一个现有源码文件，不新增源码文件、helper、类型、字段、反射接口或回调。NetCastUtils.h 只读复用；体力/魔力/箭数、资源修订号、预留标志、AdoptNetMirror 和广播不动。H01/H02 剩余状态处理、H03、既有精度/Clamp/支付/生命周期差异继续保留。

原件及尺寸记录见[第 19 批源码清单](code-cleanup-20261116/batch-19-arrow-receipt/source-manifest.json)，恢复只处理本批片段，不整文件覆盖后续并行修改。此清单在源码修改前写入。

### 实施与构建结果

C27 已完成：仅在 MagicArrowRainResources.cpp 加入 NetCastUtils.h，并把冷却表达式换成 NetCast::RemainingCooldown(R.Cooldown,R.CapturedAt,Now)。修改前 34 行、修改后 35 行；现有 helper、其他源码和所有反射声明均未修改，没有新增源码文件。原 GameState / Now 读取语句保持原位，尤其保留无 GameState 时读取本地世界时间的行为，没有改成武技回执的 ServerAt 回退。

R10/R11 继续保留：只是确认局部重复，不宣称不存在重复或存在必然行为差异；本批不为它们新增一行公式包装或跨职责输入工具。H01/H02 剩余状态处理、H03、超长文件、疑似死代码及火球独立经验缩放也未修改。

准备阶段观察到共享 Editor 构建（cmd PID 82192 / UBT PID 44476）运行；源码完成提交门禁时，其接续 Game 构建（cmd PID 57512 / UBT PID 85488，日志 SourceAssets/HillsLakeLandform20261117/Logs/FPSGAME-build.log）正在链接。本批被动等待其正常退出，未抢锁或终止进程。

19:58:25 启动一次 FPSGAMEEditor Win64 Development，参数沿用 -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=2。19:59:00 返回 **Succeeded，退出码 0，UBT 耗时 34.12 秒**；**4 个动作完成**：编译 MagicArrowRainResources.cpp、链接 lib、链接 UnrealEditor-FPSGAME.dll、写入目标元数据。

本批清单中的可实施项已完成，其余按上述理由保留。没有新增功能、测试、lint、静态检查或运行验收；未主动打开编辑器/游戏、未跨对话协调、未暂存/提交/推送，运行效果交由用户测试。

日志：[第 19 批 Editor 构建（本机归档位置）](../Publication/CodeSkillCleanup20261118/archive-manifest.json)；[本批构建回执](code-cleanup-20261116/batch-19-arrow-receipt/build-receipt.json)。

## 30. 第 20 批：专精等级读取（已完成）

日期：2026-11-17。仍只限 Skills，先列清单，仅清理能保持行为不变且不增加复杂度的重复逻辑。超过 800 行文件、疑似死代码、火球独立经验缩放不动，不加功能、不测试。本批从奖励/进度读取入口延伸到技能树专精查询，未逐文件扫描全仓。

| 编号 | 最多三级职责 | 本批清单 | 行为边界 |
| --- | --- | --- | --- |
| C28 / 实施 | 武器与战斗 → 技能魔法 → 专精等级读取 | ColdSteelSkillTree::SpecRank 内部对 Ranks 的 Find + 指针判空 + 缺省 0，直接改用现有 TMap::FindRef。 | 外层不存在专精时返回 0 的门槛保留；int32 等级存在时原值返回，缺失时仍为 0，不插入记录、不限幅、不改变读入的负值。 |
| R12 / 保留 | 武器与战斗 → 技能魔法 → 技能树规则与显示 | SkillLevel、Validate/Sanitize、RequirementText/RequirementLabel 以及专精字段解析保持原实现。 | 技能记录缺省 Level=1，不能用于替换缺失等级为 0 的读取；校验/修正、技能条件/专精条件及 ID/名称文案不同，不以同形循环或分支为由合并。 |

### 精确源码范围（修改前）

| Skills 内文件 | 行数 | 字节 |
| --- | ---: | ---: |
| `ColdSteelSkillTree.cpp` | 286 | 16200 |

只修改一个已有源码文件，不新增 helper、源码文件、类型、字段、反射接口或状态框架；头文件、技能树数据、UI 和其他模块不动。其余 H01/H02 状态处理、H03、R10/R11 继续按原理由保留。

清单在源码修改前写入；当前原件与尺寸见[第 20 批源码清单](code-cleanup-20261116/batch-20-spec-rank/source-manifest.json)。恢复只处理本批片段，不以原件覆盖后续并行修改。

### 实施与构建结果

C28 已完成：仅将 `const int32* Rank = Spec->Ranks.Find(Node); return Rank ? *Rank : 0;` 替换为 `return Spec->Ranks.FindRef(Node);`。外层 `if(!Spec) return 0` 原样保留，读取为 int32 值副本，缺失仍返回 0；没有写入 Map、增加等级限幅或改变已有值。唯一修改文件 ColdSteelSkillTree.cpp 前后均为 286 行，未新增源码文件或 helper。

R12 保留：SkillLevel 的未学/缺失等级 0 与默认技能记录 Level=1 不混用；Validate 与 Sanitize 分别承担拒绝校验和修正，退休专精处理也不同；RequirementText 使用 ID，模型通知使用名称，不能合并为同一文案。没有修改解析、迁移、学习/专精条件、奖励或火球代码。其余 H01/H02 状态处理、H03、R10/R11 及受限文件不动。

构建前遇到已运行的后台 UnrealEditor-Cmd.exe（PID 76396，20:34:14 启动），本批被动等待其正常退出，没有启动、终止或干预该进程。20:37:33 启动一次 FPSGAMEEditor Win64 Development，参数沿用 -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=2。20:38:03 返回 **Succeeded，退出码 0，UBT 耗时 29.70 秒**。

**6 个动作全部完成**：3 个编译、2 个链接、1 个目标元数据；ColdSteelSkillTree.cpp 有本次编译记录，UnrealEditor-FPSGAME.dll 已重新链接。目标同时编译了当前工作区的两个地编文件，但它们不是本批修改；源码修改范围仍只有上述一个 Skills 文件。

没有新增功能、测试、lint、静态检查或运行验收；未主动打开编辑器/游戏、未抢锁、未跨对话协调，也未暂存/提交/推送。运行效果由用户测试。

日志：[第 20 批 Editor 构建（本机归档位置）](../Publication/CodeSkillCleanup20261118/archive-manifest.json)；[本批构建回执](code-cleanup-20261116/batch-20-spec-rank/build-receipt.json)。

## 31. 第 21 批：Skills 保留项纳入清理（源码与 Editor 构建收尾完成）

日期：2026-11-17。用户最新授权将超长文件、疑似死代码和火球独立经验纳入工作范围。源码仍限定 Skills；沿用先列清单、超长文件先写拆分方案、保持行为、不增加复杂度、不加功能、不测试的标准。本节清单和原件记录先于源码修改写入；以前各批的排除说明是当批历史边界，以本节为本次范围。

| 编号 | 最多三级职责 | 本批清单 | 必须保留及原因 |
| --- | --- | --- | --- |
| C29 / 实施 | 武器与战斗 → 技能魔法 → 规则与结算 | 按既有方案把 ColdSteelSkillRules.cpp 拆成定义、进度、战斗三个实现单元；清除重复 MonsterCombatComponent include，修正迁移版本过时注释。 | 只移动完整函数及依赖，不改导出声明、旧档迁移分支、NextMasteryAttack 与 NetHitForward 的唯一静态实例；这些分别承担兼容与运行身份。 |
| C30 / 实施 | 武器与战斗 → 技能魔法 → 快速近战 | FPSQuickCombatComponent.cpp 保留生命周期/动作时钟，配置与镜头表现移至 QuickCombatPresentation.cpp，ContactHit 移至 QuickCombatContact.cpp。 | 同一组件/字段/函数签名原样保留；各武器时钟、预测/权威门槛、空手资源路径不同，不合并状态机。WarhammerQuickCombat.cpp 继续拥有其专属实现。 |
| C31 / 实施 | 武器与战斗 → 技能魔法 → 火球奖励 | 命中反馈、暴击训练复用现有 helper；从通用奖励函数抽出最终升级/经验封顶段，供通用法术和火球在原位置调用。 | 火球独立 ScaleKillExperience、当前模型 Level、TributeEffect、CreditCombatSouls 失败早退、记录/升级/提交次序及奖励去重不变。四项训练来自不同定义字段，保留原公式。 |
| C04 / 保留 | 联机与持久化 → 动作同步 → 兼容入口 | 只读刷新报告已列 ServerReportBodyAction → ServerRecordAction 调用链，不修改 Skills 外源码。 | 当前仍有 UHT RPC 包装、注册及状态写入；无手写发起者不等于不可达，不能在保持行为的要求下删除。 |

### 超长文件实施方案（先于修改）

- ColdSteelSkillRules.cpp（973 行）：原文件仅保留 LoadDefinition（原 54–446）；新 ColdSteelSkillProgression.cpp 承接 Migrate/Validate（447–586）和 Effect/ExperienceRequired/AddExperience/EffectSummary（610–658）；新 ColdSteelSkillCombat.cpp 承接 IsRifle/IsPistol/IsCriticalHit（587–609）以及 Snapshot 至 IsMasteryTrainingTarget（659–973）。静态对象仍位于唯一的原函数体，不迁入头文件；迁移注释改为不虚构版本门槛的说明。
- FPSQuickCombatComponent.cpp（813 行）：原文件保留构造、生命周期、启动/结束/取消、动作计时与 AdvanceAction；新 QuickCombatPresentation.cpp 承接 Configure/GetBowRecoilCM/GetBowSourcePlaybackRate（48–144）及 PhaseFraction/LayerWeight/GetCameraFOV/GetCameraMotion（259–469）；新 QuickCombatContact.cpp 仅承接 ContactHit（647–791）。不新增类、状态、回调或反射接口，四个新 cpp 自动归入原 UE 模块。
- 两组各成三个自然职责文件，预计均低于 450 行；不借 include 片段规避行数，也不触及其余 46 个超长文件。

### 精确源码范围（修改前）

| Skills 内文件 | 行数 | 字节 | 操作 |
| --- | ---: | ---: | --- |
| ColdSteelSkillRules.cpp | 973 | 82301 | 拆分及重复 include/过时注释整理 |
| FPSQuickCombatComponent.cpp | 813 | 42143 | 拆分 |
| ColdSteelFireballModel.cpp | 259 | 16275 | 共享反馈、暴击训练与升级尾段 |
| ColdSteelSpellRewards.h | 85 | 3475 | 提取最终等级结算 |
| ColdSteelSkillProgression.cpp / ColdSteelSkillCombat.cpp | — | — | 新建，承接既有函数 |
| QuickCombatPresentation.cpp / QuickCombatContact.cpp | — | — | 新建，承接既有函数 |

清单共四个现有源码、四个新实现文件；头文件反射声明、模块依赖、资产和其他模块不动。源码原件及哈希见[第 21 批源码清单](code-cleanup-20261116/batch-21-retained-skills/source-manifest.json)。恢复应只撤销本批片段，不能用原件覆盖后续并行修改。完成后只进行必要后台 Editor 构建，等待已有构建和项目模块使用者退出，不抢锁、不终止进程；不增加测试、lint、静态检查或运行验收。

### 源码实施结果

C29/C30 已完成。按上述边界把完整函数移动到四个新 cpp，现有两个实现各保留其核心职责；未改函数签名、导出、UCLASS、成员字段、Build.cs、动作数值或控制流。拆分时按职责归置 include，清除了 MonsterCombatComponent 的重复 include；Migrate 中“只有 <11 会走到这里”的旧注释改为“为走到共享迁移段的旧版本补齐 quickCombat”，没有删除旧档分支。

C31 已完成：火球直接调用既有 NotifyHit / AccumulateCriticalTraining；ColdSteelSpellRewards.h 新增 ApplyExperienceLevels，承接原通用奖励尾段的升级循环、加点与满级经验封顶，通用法术和火球分别在原位置调用。没有把火球接入通用击杀经验累加：ScaleKillExperience(K.Key.Get(),Level,K.Value)、TributeEffect、FloorToInt64、CreditCombatSouls 失败早退均留在火球拥有者，StageTraining 成功后才登记 RewardedVictims 的顺序不变。独立四项训练公式及元素箭训练顺序原样保留，避免混用 FireballSkill.KillExperience 与 FireballSkill.Fireball 中的系数。

| Skills 内文件 | 修改前行数 | 修改后行数 |
| --- | ---: | ---: |
| ColdSteelSkillRules.cpp | 973 | 401 |
| FPSQuickCombatComponent.cpp | 813 | 345 |
| ColdSteelFireballModel.cpp | 259 | 254 |
| ColdSteelSpellRewards.h | 85 | 91 |
| ColdSteelSkillProgression.cpp | 0 | 194 |
| ColdSteelSkillCombat.cpp | 0 | 385 |
| QuickCombatPresentation.cpp | 0 | 320 |
| QuickCombatContact.cpp | 0 | 170 |

两个原超长文件拆出的六个实现单元分别为 401/194/385 行和 345/320/170 行，均低于 800 行；这些尺寸是本批落盘时的记录，不作为其他会话后续编辑的限制。

C04 已刷新：精确符号检索仍只有 Multiplayer/ColdSteelPlayerState.h:248 的 RPC 声明、ColdSteelPlayerState.cpp:2267–2274 的实现及 Characters/FPSPlayerBodyActions.cpp:742–754 的状态写入，未发现手写发起调用；但当前生成代码仍有包装（5743）、分发（5802）及注册（7376、7460），调用后会更新 ReplicatedState 并 ForceNetUpdate。仅凭手写调用缺失不足以证明反射/动态入口不可达，继续保留，未修改这些模块或生成代码。这里没有把“疑似”当作已证实死代码，也没有扩大为全仓删除排查。

源码落盘后，构建门禁先等待既有 UnrealEditor-Cmd.exe（PID 86784，20:45:03 启动）。读取实际模块位置发现其使用隔离 Host 内的 DLL 副本，与项目 DLL 文件 ID 不同；本批未启动、终止或控制该进程，它随后自然退出。构建实际结果见下节。

### 必要后台构建与最终边界

首次门禁于 20:50:23 自动进入本批构建（日志 cleanup-batch21-20261117-205023.log）。调整等待命令时，命令已转入编译，本批仅中断了自己的命令（退出码 1），没有终止其他进程；已产出的对象文件保留。随后发现另一项共享 Editor 构建（cmd PID 95912 / UBT PID 27116），等待其正常退出后续编，没有向其他对话发送协调消息。

20:51:40–20:54:09 完成本批续编调用，参数沿用 -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=2。结果为 **Failed (OtherCompilationError)，退出码 6，UBT 耗时 148.76 秒**。74 个计划动作中记录了 71 个编译动作；编译存在失败，未执行最终链接/目标元数据步骤，不能记为 Editor 构建成功或本批 DLL 已交付。

明确阻塞位于 **Source/FPSGAME/WorldGeneration/HillsBlacksmith.cpp:45–52**：访问 Building/BronzeTorch.h 中受保护的 LightLumens、LightRadiusCm、bLightCastsShadows、TorchLight、TorchBody、TorchFlame，产生 C2248。它们均在 Skills 外，本批未修改，也未为解决构建扩大清理范围。

拆分后的六个实现文件在已存在的共享构建日志中有编译记录，本批首次编译也记录了 ColdSteelFireballModel.cpp；未见这些文件的编译报错，但这不能替代完整目标链接成功或运行验收。共享构建同样被 HillsBlacksmith 的访问错误阻塞。本报告仅引用已有日志，没有发起该共享构建或其相关场景操作。

C29–C31 源码清单已落实，C04 因可达性证据不足保留；完整 Editor 构建仍待上述外部错误解决。未新增功能、测试、lint、静态检查或运行验收；未启动编辑器/游戏、未终止他人进程、未抢占已观察到的共享构建，也未暂存、提交或推送。运行效果由用户测试。

日志：[本批续编日志（本机归档位置）](../Publication/CodeSkillCleanup20261118/archive-manifest.json)；[首次中断日志（本机归档位置）](../Publication/CodeSkillCleanup20261118/archive-manifest.json)；[第 21 批构建回执](code-cleanup-20261116/batch-21-retained-skills/build-receipt.json)。

### 第 21 批续办：构建收尾清单（先列清单）

用户继续后，先处理上次明确未完成的必要 Editor 构建。本次读取原 C2248 位置发现，当前 HillsBlacksmith.cpp 已改为 ConfigureSceneLight 和组件接口，BronzeTorch.h 也已有对应公开声明；这些是工作区既有更新，不是本批修改。此处只确认原阻塞的源码状态，不作该模块的额外审计或测试。

| 项目 | 本次操作 | 范围 |
| --- | --- | --- |
| 原 C2248 构建阻塞 | 读取原报错位置后，使用当前工作区重新完成必要后台 Editor 构建 | 不修改 Skills 外源码，不代领其他工作的修复 |
| 共享占用 | 等待已运行构建和项目模块使用者正常退出 | 不终止进程、不抢锁、不跨对话协调 |
| 汇报与回执 | 记录本次实际结果，并保留上次失败/中断记录 | 本次没有新增源码清理项，不新开功能或测试 |

本次收尾没有新增源码修改。进入门禁时，FPSGAME 编辑器（PID 99196，21:31:08 启动）正在运行，并有其 Turnkey 子命令；用户确认保存并关闭后，已观察到两者退出。随后被动等待既有共享 Editor 编译（cmd PID 102852 / UBT PID 74520，21:49:27 启动）及其剩余编译器进程退出，于 22:05:09 启动本批续编。没有关闭编辑器、终止其他进程或抢占已观察到的占用，完整结果如下。

### 第 21 批续办结果（2026-11-17 22:26）

本次使用同一等待命令持续收尾，没有重启或中断本批构建。**22:05:09–22:26:16，FPSGAMEEditor Win64 Development 返回 Failed (OtherCompilationError)，退出码 6；UBT 耗时 1242.13 秒，编译执行阶段 1155.27 秒。** 计划 150 个动作，记录 147 个编译动作（包含失败），未执行最终链接及目标元数据步骤，不能记为 DLL 已更新。

本次原 HillsBlacksmith.cpp 对 BronzeTorch 受保护成员的 C2248 未再出现；对应接口调整是开始续办前已有的工作区更新，不是本批修改。以下为本次构建直接报告的阻塞位置，仅记录编译证据，不宣称已完成这些模块的审计或根因修复。

| Skills 外文件/位置（相对于 Source/FPSGAME） | 本次构建错误 | 本批处理 |
| --- | --- | --- |
| WorldGeneration/TemperateHillsWorld.h:449、450、452 | UCLASS / 类声明 / GENERATED_BODY 附近 C2143、C4430；相应 UHT 生成 cpp 另有构造/析构声明连带错误 C2600、C2511、C2550 | 保留源码及生成文件，不跨范围修改 |
| WorldGeneration/VillagePlantingDisplay.h:4 | C1083，缺少 VillagePlantingDisplay.generated.h | 未手工伪造或修改生成头 |
| WorldGeneration/TemperateHillsLandscapeCapture.cpp:224、227 | TObjectPtr<UStaticMesh> 的 auto* 推导失败 C3535/C2440，以及 SetStringField 参数 C2661 | 保留，未扩大为地编功能修复 |
| WorldGeneration/VillageDefenseDebris.cpp:54 | TObjectPtr<UStaticMeshComponent> 的 auto* 推导失败 C3535/C2440 | 保留 |
| WorldGeneration/VillageDefenseGate.cpp:18、22 | Role 遮蔽成员 C4458、OutLifetimeProps 未声明 C2065 | 保留 |
| WorldGeneration/VillageDefenseSection.cpp:38–42 | OutLifetimeProps 未声明 C2065 | 保留 |

UBT 还在 5 个现有 cpp 的第 1 行输出“对应头文件应首先 include”的诊断：Monsters/MonsterAIController.cpp、Monsters/MonsterCombatComponent.cpp、Monsters/NurseZombie.cpp、Movement/FPSDoorPushComponent.cpp、WorldGeneration/HillsNightRaidSubsystem.cpp。它随后继续执行编译动作；这些诊断与上表实际编译失败分开记录，没有当作 Skills 源码变更。

本次仅完成必要构建尝试及文档收尾；第 21 批 C29–C31 源码完成状态不变，完整 Editor 构建仍受上述范围外错误阻塞。本次没有修改任何业务源码、添加功能、运行测试/lint/静态检查/游戏或打开编辑器；编译日志中带 Audit/Tests 名称的实现属于目标编译依赖，不表示执行了这些测试。未跨对话协调、未终止其他进程、未暂存/提交/推送。没有在错误未解决时重复构建。

[本次续编日志（本机归档位置）](../Publication/CodeSkillCleanup20261118/archive-manifest.json)；[本次构建回执](code-cleanup-20261116/batch-21-retained-skills/build-resume-receipt-20261117.json)。上次失败和自有命令中断记录继续保留在原 build-receipt.json，未覆盖为成功。

### 第 21 批再次续办：先行清单（2026-11-17）

用户继续后，只接续未完成的 Editor 构建，不新增源码清理项。读取上次六个报错文件的当前相关片段：LandscapeCapture 已显式取得 UStaticMesh*；VillageDefenseDebris 已使用 TObjectPtr::Get()；VillageDefenseGate 已改用 MeshRole 和 OutLifetimeProps；VillageDefenseSection 已使用 OutLifetimeProps。这些对应修正均为当前工作区已有更新，本批只读，不计为本批修复。两个反射头文件保留当前声明，生成文件交由正常 UHT 流程处理，不手工改写。

| 项目 | 本次操作 | 边界 |
| --- | --- | --- |
| 构建前置 | 等待既有 Editor 构建（cmd PID 105940 / UBT PID 91932）及链接进程退出 | 不抢锁、不终止进程、不跨对话协调 |
| 必要构建 | 使用当前工作区执行 FPSGAMEEditor Win64 Development | 不新增源码修改，不启动编辑器/游戏或测试 |
| 汇报 | 保留此前失败回执，按本次实际结果更新当前状态 | 区分目标已最新、实际编译动作及实际链接 |

准备时已观察到共享 Editor 构建处于链接阶段，其后返回 Succeeded，并接续 Game 构建；本批等待后者及相关编译/链接进程退出，再执行独立收尾调用。本次只读输入快照及完整状态见 batch-21-retained-skills/build-resume2-status.json，最终结果如下。

### 第 21 批最终构建收尾（2026-11-17 22:36，已完成）

**22:36:16–22:36:28，本批 FPSGAMEEditor Win64 Development 返回 Succeeded，退出码 0，UBT 耗时 11.89 秒。** 输出明确为 **Target is up to date**，执行 **0 个编译、0 个链接、0 个元数据动作**；本次没有重新链接 DLL，不能把前序共享构建的链接动作记为本批执行。

本次启动前，共享 Editor 构建已成功，接续的 Game 构建也在退出后释放占用；本批沿用后台门禁被动等待，没有并发抢锁、终止其他进程或发送协调消息。前序共享构建由已有工作发起，本批只读取其构建日志；此前范围外修正也不是本批源码改动。

第 21 批 C29–C31 源码及必要 Editor 构建收尾现已完成；原先因外部错误受阻的描述和失败回执保留为历史，不再代表当前构建状态。C04 仍按反射入口和状态写入证据保留，H01/H02 剩余状态处理、H03、R10–R12 的行为/复杂度保留理由不变。

本次续办只更新清理文档与回执，没有新增源码修改、功能或测试；未启动编辑器/游戏，未做 lint、额外静态检查或运行验收，也未暂存、提交或推送。构建成功不代表运行效果已经测试，运行效果由用户测试。

[最终 Editor 构建日志（本机归档位置）](../Publication/CodeSkillCleanup20261118/archive-manifest.json)；[最终构建回执](code-cleanup-20261116/batch-21-retained-skills/build-resume2-receipt-20261117.json)。此前两份失败回执继续保留，源码原件及前后尺寸不改写。

## 32. 第 22 批：战斗模型读取去重（已完成）

日期：2026-11-17。延续仅 Skills 的明确源码范围；第 21 批拆分后，ColdSteelSkillCombat.cpp 已低于 800 行，本批只沿其 Snapshot、GrantBerserkOnWeaponHit、ApplyHit 三个已有入口处理局部重复。继续保持行为、不增加状态框架、不加功能、不测试；不因“继续”自动扩大到报告中的其他 46 个超长文件。

| 编号 | 最多三级职责 | 本批清单 | 保留原因与边界 |
| --- | --- | --- | --- |
| C32 / 实施 | 武器与战斗 → 技能魔法 → 战斗模型读取 | 把三处“角色影子档案优先、否则 GameInstance 子系统”的相同读取提为本 cpp 匿名命名空间的 SkillCombatModel(AActor*)，各入口在原位置调用。 | 单参数、无状态、无缓存，不改公开 API、反射布局、返回对象或读取顺序；保持普通 Actor 的 GI 回退与空指针结果。狂暴入口原非空/权威/技能门槛先执行，不移动查询时点。 |
| R13 / 保留 | 武器与战斗 → 技能魔法 → 归属路由差异 | 不用 NetCast::AuthorityModel 或 ColdSteelAuthority::ForPawn 替代这三处；原 AwardKillByOwner / NotifyKillByOwner 继续使用 ForPawn。 | 前者额外解析 UnknownSpell 施法者，后者按 NPC、权威和本机控制分流，并可能直接返回空影子模型；与本批三个入口的回退合同不同，不能为共用名字改变归属。 |

### 精确源码清单（修改前）

| Skills 内文件 | 行数 | 字节 | 修改 |
| --- | ---: | ---: | --- |
| ColdSteelSkillCombat.cpp | 385 | 27354 | 新增文件内读取函数，并替换三处重复代码 |

只修改一个已有 Skills cpp，不新增源码文件、共享头、类、字段、回调或模板；其他模块仅按所需具体 helper 读取以判定语义，不修改。C04、此前因行为/复杂度保留的状态处理及火球独立缩放不动。以上清单先于源码修改写入，原件和哈希见[第 22 批源码清单](code-cleanup-20261116/batch-22-combat-model/source-manifest.json)。恢复只撤销本批片段，不用原件覆盖并行更新。源码完成后进行必要后台 Editor 构建，等待已有共享占用退出，不启动编辑器、不测试。

### 源码实施结果

C32 已完成：本 cpp 的匿名命名空间新增 SkillCombatModel(AActor*)，保留原先先 Cast 到 AFPSGAMECharacter 并读取 GetNetShadowProfile、为空时再读取 GameInstance 子系统的语句顺序。Snapshot 和 ApplyHit 在原查询位置各调用一次；GrantBerserkOnWeaponHit 仍先完成非空、权威、近战、来源实例和参数门槛，再调用该函数。

只修改 ColdSteelSkillCombat.cpp，385→391 行；无新增源码文件或公开接口。普通非角色 Actor 的 GI 回退、空输入结果、无影子档案时的回退均保留。没有引入 UnknownSpell 的 NPC 模型、线程局部 ActingModel 或 ForPawn 的控制权判断；击杀归属入口继续使用原 ForPawn。武器快照、伤害转发、狂暴资格/叠层、静态攻击序号和 NetHitForward 不变。

源码落盘后，门禁观察到既有 UnrealEditor-Cmd.exe（PID 106840，23:47:23 启动），被动等待其退出后才启动本批 Editor 构建；本批未启动、终止或控制该后台实例。

### 必要构建与交付

23:49:52–23:50:24 完成一次后台 FPSGAMEEditor Win64 Development，沿用 -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=2。返回 **Succeeded，退出码 0，UBT 耗时 32.44 秒**；**4 个动作完成**：编译 ColdSteelSkillCombat.cpp、链接 lib、链接 UnrealEditor-FPSGAME.dll、写入目标元数据。

C32 源码与构建均完成，R13 保留差异不变。本批只有一个 Skills 源码文件变更，没有新增功能、测试、lint、额外静态检查或运行验收；未启动编辑器/游戏、未终止其他进程、未跨对话协调，也未暂存、提交或推送。运行效果由用户测试。

[第 22 批 Editor 构建日志](../../Saved/BuildEditor/cleanup-batch22-20261117-234952.log)；[构建回执](code-cleanup-20261116/batch-22-combat-model/build-receipt.json)。此前 Skills 外长文件、C04 及行为/复杂度保留项没有因此计为完成。


## 33. 剩余批次统一清理（用户追加全部批次）

用户要求逐个优化全部批次，范围扩展到原报告剩余模块。前 22 批保留历史结果；第 23–31 批先列清单后修改，源码清理、逐项结论与必要 Editor 构建现均已完成。

- UI / 档案、建造 / 生产、地牢元数据 / 怪物、角色 / 联机、武器、丘陵 / 植被、身体弯刀动作数据依次完成；本轮拆分 33 个原长文件，所有新承接文件均小于 800 行。档案的两处升级奖励尾段复用现有 helper；相同 include 清理随对应文件完成。
- 原清单共 48 项：35 项已拆分（含第 21 批的 2 项），13 项保留（10 个连续动作数据头、Character 反射头、BodyAnimInstance 和 AuthoredDungeonGenerator）。保留原因逐项写明，不计作已拆分或删除。
- C04 / C06、K01–K03、H / R 剩余行为差异均给出保留结论；未将无手写调用、旧作者版本或诊断用途直接判为死代码。火球独立经验倍率、舍入与魂奖励不改。
- 本轮写入回执覆盖 126 个源码/作者脚本路径：34 个已有文件、92 个新文件。既有文件的首次字节快照及逐次写入收据已保存；未重置、暂存、提交或推送工作区。

逐项计划、源码结果、构建历史与保留理由见[第 23–32 批完整记录](code-cleanup-20261116/all-batches-20261117.md)。处理前与本轮落盘文件清单见[manifest.json](code-cleanup-20261116/all-batches-20261117/manifest.json)，写入记录见[edits.jsonl](code-cleanup-20261116/all-batches-20261117/edits.jsonl)。不新增功能，不运行测试、lint、额外静态检查或运行验收，运行效果由用户测试。


第 23–31 批最终 Editor 收尾已完成：等待共享构建退出后，最终回执为 **Succeeded、退出码 0，UBT 16.46 秒、4 个动作**，包含 DLL 链接与目标元数据写入。前序失败和生成头随共享工作区更新的经过完整保留在统一记录；本轮未终止其他进程，未启动编辑器/游戏，也未运行测试。所有可按本轮标准实施的批次已完成，保留项均有具体理由，运行效果由用户自行测试。

[最终构建回执](code-cleanup-20261116/all-batches-20261117/build-final-resume3-20261118-101539.json)；[最终构建日志](../../Saved/BuildEditor/cleanup-all-final-resume3-20261118-101539.log)。

## 34. 个人技能维护源、引用与领域规则收尾（已完成）

日期：2026-11-18。本批承接剩余规则文档整理，先登记精确路径与原尺寸，再逐项处理；不扩大为新的源码清理或功能开发。

| 范围 | 数量 | 结果 |
| --- | ---: | --- |
| 个人 SKILL 维护入口 | 19 | 删除失效默认步骤，保留规则补具体原因 |
| 工程/个人引用与路由资料 | 843 | 清理冲突规则，其中 323 份相同工程正文改为个人维护源入口 |
| LOCAL-HISTORY.md | 16 | 改为历史索引，原始事实及快照留存 |
| 领域 WORKFLOW | 4 | 武器、近战武器、UI、任务全部完成 |
| 被引用的规则/标准/流程页 | 53 | 同步现行合同与原因，资产台账保留原顺序 |
| 合计 | 935 | 工程内 483 份，个人目录 452 份 |

删除或改写了默认启动 UE/Live Coding/重启/测试、固定旧工具与版本保证、强制独立模块路由、双份镜像维护、旧手型与近战阶段表述、默认提交推送及外部视觉旧要求。保留规则按对象补充原因，已有具体因果说明沿用；参数表和历史执行事实没有被提升为新指令。

18 份工程 SKILL 本批只作为入口读取；1162 份传递引用的历史证据仍按历史保留，不计入 935 份文档整理完成数。323 份入口标明个人目录的本机依赖，跨机器交付需要导出实际使用的维护源。未删除业务实现、资产、历史作者输入或原始失败记录。

完整删除项、四份 WORKFLOW 结果和恢复边界见[本批整理汇报](skill-rules-20261118/result.md)；[先行清单](skill-rules-20261118/plan.md)、[逐文件前后清单](skill-rules-20261118/final-manifest.json)和[逐次修改回执摘要](skill-rules-20261118/edits-summary.json)均已保存。原字节保存在本批 before/project 与 before/personal，恢复只撤销对应片段，保留后来并行修改。

本批只有规则与汇报文档改动，没有新增功能、业务源码、运行时配置或资产改动。未测试、未运行 lint/规则验证器/额外静态检查，未构建、启动 UE/游戏或渲染；未终止进程、跨对话协调、暂存、提交或推送。文档已落盘，游戏效果由用户测试。

## 35. 本次产物归档与 Git 发布（2026-11-18）

用户授权本次冗余归档、经验沉淀和推送到指定 3D-FPS 仓库。先读取 AGENTS、WORKFLOW 第 4/6/7/8 节及发布参考，再列精确归档和发布清单。

- 1156 份一次性编辑/拆分/构建工具、草稿、原件快照和重复中间输出，合计 37,147,292 字节，已移入 trash/code-skill-cleanup-20261118；移动后散列与清单一致。本批没有生成截图、GIF 或视频。最终说明、清单、构建摘要及最终成功日志保留。
- 有用经验已归入技能维护、架构清理、法术奖励训练和 Git 发布参考。459 份维护源及支持文本作为仓库只读发布快照，工程相对引用，个人源保持唯一维护位置；16 份历史原文保留可发布索引。
- 公共主线与完整本机宿主不同。16 个源码路径以完整独立组直接合入；152 个路径以带清理前/后散列的 Integration 补丁保存，尚不代表公共源码已完成对应拆分。3 个密集动作数据路径留在本机，不公开数据正文。所有本机清理成果保持，不为发布回退工作文件。
- 当前共享索引已有其他工作的暂存，且本地主线落后远端，本批使用临时发布工作区；共享工作区、索引和分支不重置。提交基于当前远端，不夹带他人未发布提交。

[发布说明](../Publication/CodeSkillCleanup20261118/README.md)、[归档清单](../Publication/CodeSkillCleanup20261118/archive-manifest.json)、[源码发布处置](../Publication/CodeSkillCleanup20261118/source-publication-manifest.json)及[技能导出清单](../Publication/CodeSkillCleanup20261118/skill-export-manifest.json)明确区分本地成果、直接合入和待前置恢复的接入包。只执行本次授权的归档与推送检查，没有启动 UE/游戏、运行测试或重新构建。
