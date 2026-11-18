# 剩余批次统一清理（本轮已完成）

最终状态（2026-11-18）：第 23–31 批已逐项完成可实施清理；本轮拆分 33 个原长文件，累计 35 / 48 项已拆分，13 项有明确保留结论。Editor 构建最终成功、退出码 0，DLL 已链接。未新增功能、未测试；运行效果交由用户测试。最终回执见本文末尾，前面的失败记录保留为历史。

## 范围与执行标准

用户要求“把所有批次逐个优化，全部做完再汇报”，本轮按原报告各模块继续，包含超长文件、疑似死代码与原先保留的重复逻辑。前 22 批保留历史结果，不重复实施。

只清理能够保持行为且不增加维护复杂度的项目；不增加功能、不测试。超过 800 行的文件逐项列出实际方法边界后再修改。保留并行修改、反射身份、存档和网络合同、采样数值、运算顺序、唯一缓存与静态状态。必要构建等待共享构建与编辑器，不抢锁、不终止其他进程。

## 模块清单（最多三级）

| 大模块 | 子模块 | 本轮职责 |
| --- | --- | --- |
| UI 与档案 | 档案 / 库存 | 生命周期、加载、运行时同步、奖励与物品事务 |
| UI 与档案 | 页面 / HUD / 加载 | 构造、数据、交互与后台生命周期 |
| 角色与联机 | Character / PlayerState | 原类实现按职责迁移，反射声明保留 |
| 角色与联机 | 身体表现 | 装备、动画与运动采样 |
| 建造与生产 | 体素建造 / 工具 | 放置事务、世界登记、界面与装备 |
| 地牢与世界 | 地牢 / 丘陵 / 植被形变 | 布局、流程、流送与提交 |
| 战斗 | 怪物 / 武器 | 状态执行、装备、接触、表现 |
| 动作数据 | Spellbook / Staff / Unarmed / 身体 | 先定位作者源与消费者，保留逐项数据 |

原始 48 项中 Skills 两项已在第 21 批拆分；剩余 46 项逐项记录在本轮 manifest.json。C04、C06 及 H/R 保留项同样给出结论，不能将未证明无效的入口计为已删除。

## 第 23 批：档案与库存

先列清单（修改前）：

- `UI/ColdSteelProfileRuntime.cpp`：保留初始化、影子模型与事务提交；将 `ReloadProfile` / `SaveNow` 迁至 `ColdSteelProfileLoading.cpp`，`MaxExperience` / `GainExperience` / `AwardKill` 迁至 `ColdSteelProfileRewards.cpp`，`FindItem` 至 `DefaultAction` 迁至 `ColdSteelProfileItems.cpp`，`SyncRuntime` 至文件末迁至 `ColdSteelProfilePawn.cpp`。存档读取和退役物品迁移通过仅内部使用的声明共享原实现；自动存档 CVar 和转轮弹壳写入 helper 随运行时同步移动，保持唯一实例。
- `GainExperience` 与 `AwardKill` 的升级、点数和满级经验封顶尾段改用已有 `ColdSteelSpellRewards::ApplyExperienceLevels`。各自经验倍率、整数舍入、奖励提交与技能训练顺序保持原位，火球独立倍率不改。
- `UI/ColdSteelInventoryRules.cpp`：物品只读属性、目录固有值、占格与朝向（`ReadOnlyObject` 至 `ApplyOrientation`）迁至 `ColdSteelItemProperties.cpp`；可变 JSON 读取、背包目录缓存、布局迁移仍留原文件，避免复制缓存。

状态：已按清单实施并完成必要后台构建，最终回执见本文末尾。

第 23 批源码已落盘：档案主文件 491 行，加载 526 行、奖励 101 行、物品事务 413 行、角色同步 370 行；库存规则 734 行、只读物品属性 102 行。必要编译统一在 UI 批次完成后进行，未测试。

## 第 24 批：UI 页面、HUD 与加载职责

先列清单：

- 图鉴：`Categories` 至 `Entries` 归目录数据；`WeaponDetailRows` 至文件末归详情及状态/祭品/附魔卡片；主文件保留布局与交互。共享分类表、格式函数只有一处定义，声明移到内部头。
- HUD：`BuildInteractHint` 至 `MakeInventoryGrid` 归构造；`RefreshEventTimeline` 至天气筛选回调归时间线；`RefreshAmmo` 至末尾归读数与展示；生命周期、输入与面板路由留原文件。共享颜色和 helper 单一定义，删除原 include 区三项完全重复引用。
- 技能页：`EffectValue` / `EffectRow` / `TrainingCard` 归详情，`BuildPage` 归页面构造；其余导航与布局留原文件，既有 Additional 谓词通过内部头共用。
- 冶炼页：`NativeOnInitialized`、`UpdateScale`、布局和升级页签视觉迁到布局文件；炉子设置和事务保持原文件。升级轴标题通过内部常量共享，原颜色函数继续使用现有 Presentation。
- 工作台：仅迁 `NativeOnInitialized` 及只在它使用的轴标题到布局文件；其余事务不变。
- Transit：启动菜单构造、联机菜单回调迁至 StartupMenu；两个已有 view 状态类型移至内部头供原生命周期使用，不新增状态。场景准备和取消边界不变。
- 物品浮窗：先细化长函数内独立卡片职责，再按不增加参数耦合的边界处理。

状态：已按清单实施并完成必要后台构建，最终回执见本文末尾。

物品浮窗细化清单：将锻造、木芯、木工和枪械装配的工艺卡片段（原 119–197 行）迁至 `ColdSteelTooltipCraftQuality.cpp`，返回原有工艺摘要；原构建函数保留卡片插入位置及摘要追加顺序。只读 JSON/文案格式函数以内部头共享，Reference 静态缓存仍归原文件所有。

第 24 批源码已落盘：图鉴主文件 677 行，HUD 617 行，技能页 383 行，冶炼 771 行，工作台 645 行，Transit 745 行，物品浮窗 775 行；新实现文件均不足 800 行。首轮必要 Editor 构建（2026-11-18 00:04:54–00:06:12）因图鉴详情 static_assert 需要编译期的 TributeRarityCount 失败，退出 6；已将该既有计数移至内部头，继续从稀有度数组大小计算，待下一轮续编。无测试。

## 第 25 批：建造与生产工具

先列清单：

- VoxelBuildComponent：形状定义、初始化和生命周期留原文件；原 539–765、1660–1756 的面板内容/提示迁至 Panel；795–1228 的瞄准和构件目标迁至 Target；1229–1460 的预览及放置有效性迁至 Preview；1461–1659、1757–1821 的输入和扣料/返还迁至 Input。AimScratch、ProbeScratch 保持各一份并随目标查询移动；ClippedPlayerCells 与 NumberKeyIndex 仅内部声明共享，不复制状态。
- VoxelBuildWidget：构造和卡片生成（134–243、531–764）迁至 Layout；布局常量与既有布局 helper 放内部头，保留数值/布局算法，键盘消费状态不变。
- VoxelBuildWorld：773 行起的结构状态摘要及 solver 读数迁至 Status，世界事务和唯一 Runtime 指针留原文件。
- ProductionToolComponent：InitializeLocalTool / ApplyToolStats / RefreshHeldTool 迁至 Equipment；装备专用路径和 HarvestMotionPath 一并移动，共用普通挥击音效路径保留唯一原定义。工具动作时钟、接触和 ToolDigReach CVar 留原文件。

状态：已按清单实施并完成必要后台构建，最终回执见本文末尾。

第 25 批源码已落盘：建造组件 560 行，建造面板 544 行，世界 772 行，生产工具 629 行；新增实现按目标/预览/输入/面板、结构状态和装备分开，原数值及状态所有者不变。

## 第 26 批：地牢元数据与怪物实现

先列清单：

- DungeonRunSubsystem：ParseLayoutManifest / ParseCatalog 及仅由它们使用的模块分类和 ReadVec3 迁至 DungeonRunCatalog；流程、进度和档案写入留原文件。
- FacilityHallEncounter：FindSpawn / FindInitialSpawn 迁至 FacilityHallPlacement；槽位生成次数、精英替换、随机流与状态留原类。
- UnknownHumanoidTactics：HasFiringLane 至 CanPursueDuringAction 迁至 UnknownHumanoidFocus；路径规划预算静态 LastFrame 和掩体状态留原文件。
- WildlifeAnimal：目录解析、Find / ForActivity / Reload / Get 及唯一 GCatalog 迁至 WildlifeCatalog；PlayerThreat 至 BlockedTooLong 迁至 WildlifeSteering；伤害、死亡、复制和掉落留原文件。
- BlindSupplicantAuthoring：ReadCmVector 至 BuildContinuousGillCloth 的编辑器 cloth 制作 helper 迁至 BlindSupplicantClothAuthoring；共享非反射草稿类型及函数声明放内部头。所有 WITH_EDITOR 条件、六个 gill 的顺序、manifest 容差及回执不变。
- AuthoredDungeonGenerator 单独细化：PrepareAssembly 单函数已达 855 行，需先按装配职责而非机械截断处理，尚未修改。

状态：已按清单实施并完成必要后台构建，最终回执见本文末尾。

第 26 批源码已落盘：DungeonRun 684 行、HallEncounter 710 行、UnknownHumanoidTactics 756 行、WildlifeAnimal 793 行、BlindSupplicantAuthoring 584 行。第二轮 Editor 构建在等待共享 UE 进程结束后于 00:11:59 启动；发现 cloth 公共入口也读取 ManifestMatchToleranceCm，已将原 1.0 cm 常量放入内部头，待续编。本轮没有修改容差或执行制作/测试命令。

## 第 27 批：角色与联机门面

先列清单：

- FPSGAMECharacter.cpp 按完整原方法迁移：InitializeWeaponVisuals → Initialization；输入绑定/移动输入/Inspect/技能输入/滑步 → Input；ReloadPressed → ReloadInput；快速近战/武器状态/装备收尾 → WeaponState；镜头 → Camera；视模与 ADS 姿态 → Viewmodel；射击/反馈/散布 → Firing；动画与音效加载/播放 → AssetsAudio；ReloadSourceTime 至 UpdateActionPose → ActionPose；左右手动作可用性 → ActionAvailability。构造、BeginPlay、Tick、原诊断与弹簧推进留门面。已有 Ammo/Reload/OffhandReload/ActionPriority 的事务实现保持其原职责；本轮移动的是门面中的不同方法，不另写第二套事务。
- 角色现有 CVar 保持唯一原定义，只以内部声明共享；AKM/M1911 纯常量移至内部头，PKM 音效加载原实现随 AssetsAudio 迁移。
- ColdSteelPlayerState.h 的五个顶层协议 USTRUCT（FoodClockState、NetHitReport、NetCastRequest、NetHitReceipt、PublicPlayerInfo）原字段/顺序/元数据迁至 ColdSteelPlayerProtocol.h，仍在 FPSGAME 模块；PlayerState 的 RPC 与成员不变，由 UHT 正常生成新头。
- ColdSteelPlayerState.cpp：档案采纳/清洗、档案同步、命中校验、命中准备与结算、法术请求分别迁入原类的职责 cpp，唯一序号、缓存和所有成员保持原类。
- 身体装备仅迁 RebuildWeapons 至独立实现；身体动作按 Capture 与 Apply 分开，纯变换/显隐 helper 内部共用。
- FPSGAMECharacter.h 暂保留：1043 行主体是同一 UCLASS 的反射成员、公开内联合同及交织状态；唯一小型非反射嵌套结构不足以构成自然拆分。为压行数改成员归属、引入状态间接层或删注释均不符合本轮“不增加复杂度”；不做机械 include 碎片。
- FPSPlayerBodyAnimInstance.cpp 暂保留：FControls::Evaluate_AnyThread 与 FProxy::PreUpdate 各自跨越大量同帧局部值，并依赖既有 pose inl 的共享类型。仅机械移动会产生新的超长文件；跨阶段拆解将增加动画工作线程上下文参数，超出本轮的简单清理标准。其既有动作、骨序与时钟完整保留。

状态：可直接迁移项已完成并完成必要后台构建；两项保留是明确结论，不计为已拆分。

第 27 批可直接迁移项已落盘：Character 主文件 647 行（新增完整职责实现均不超过 680 行）；PlayerState 主文件 361 行、协议头 112 行、原头 718 行；身体装备 783 行，身体运动 534 行。第 27 批落盘时累计 23 个原长文件已拆分，2 个保留复杂度结论，当时另外 21 个待后续批次处理。未将保留项计为已拆分。

构建状态补记：00:11:59 启动的第二轮命令会话在第 50/73 个动作后以外层退出码 1073807364 结束，日志没有 UBT 最终回执，未完成链接；本对话没有终止进程。其已报告的 ManifestMatchToleranceCm 错误已修正。随后以隐藏后台 PowerShell 启动 character-network 续编，回执由 build-editor.ps1 写入本轮目录；UHT 已正常生成 13 个文件，正在进行 286 个构建动作。编译器参与编译现有 Audit 源文件不代表运行测试，本轮未执行测试。

## 第 28 批：武器实现职责

先列清单：

- BowWeaponComponent：装备与部件（156–215、234–731）、拉弓/换箭动作（732–1195）、箭矢释放（1196–1372）、瞄准/运动/姿态表现（1373–1475、1658–2034）分别迁移完整方法；生命周期和镜头前动作推进留原文件。弓的三项 CVar、音效路径缓存仍唯一，既有 DampCarry 模板放内部头共享。
- KukriWeaponComponent：装备（176–449）、姿态和镜头（450–713）独立实现；攻击推进和命中保持原位。既有纯常量与无状态 helper 内部共享，删除完全重复的 DynamicMesh include。
- PistolDualWieldComponent：LoadHand 至 CopyLeftAttachments（138–491）及装备槽解析归 Equipment；只共享既有 PistolPoseFamily 函数声明，动作、时钟和弹药仍在原文件。
- RuneSwordComponent：初始化装备（124–300）、姿态/检视（318–424）和镜头/裂隙表现（1029–1434）归 Presentation；攻击与重击状态（425–1028）归 Actions；刀刃采样/扫掠/命中（1435–1635）归 Contact。保持完整方法体、调用顺序和原类状态。
- RuneSwordAzureDragon：TickAzureDragon 至 UpdateAzureDragonTrail（448–995）归 Presentation；准备、资产和销毁留原文件。原不可变调校、采样结构和纯函数移至内部头，网格创建仍只定义一次。
- FPSWeaponFXComponent：曳光段/池/变换/灯光及 TickTracers 归 Tracers，发射烟/抛壳/命中表现归 Emission。几何创建 helper 随曳光移动；CVar 仍各一份，通过内部声明引用，原粒子池、粒子更新与生命周期留主文件。

状态：已按清单实施并完成必要后台构建，最终回执见本文末尾。

## 第 29 批：植被形变与丘陵世界

先列清单：

- GrassDeformSubsystem：GetReadTarget 至 HasLiveContent（738–1047）迁至 GrassDeformRendering，包含原 ping-pong、盖章、窗口重定位、踩踏源和参数发布；材质参数名以内部头共享，资源加载、质量缓存、控制台注册仍在原文件。
- TemperateHillsWorld：Noise 至 ApplySoilRefill（299–546）迁至 Terrain；TreeCandidate 至 SetVegetationGenerationRadius（600–909）迁至 Vegetation。纯散列/曲线函数仅声明共享，地形 CVar 随地形移动，FLayerRadii 随植被移动，存档和 RPC 留原类。移除重复 Engine/StaticMesh include。
- TemperateHillsStreaming：已有 FCell/FJob/FMeshResult 和 FTemperateHillsStreamingState 移至内部头，保持布局及唯一实例；网格构建与 EditMeshBoost 归 StreamingMesh；LoadNextEnvironmentStage / TickPreparation 和对应资产就绪 helper 归 StreamingPreparation；原非 Shipping 的访问命令与落脚 helper 归 StreamingVisit；BuildValleyFog 归 StreamingFog。进程级预算、原 TickStreaming、取消和资源释放留主文件，不新增调度层、不改流送预算。

状态：已按清单实施并完成必要后台构建，最终回执见本文末尾。

第 29 批边界补充：GetMapGroundMaterial / CopyMapGround / PrepareSpawnGround 随 StreamingPreparation 迁移，主文件保留 BeginStreaming 至生命周期职责。

## 第 30 批：动作采样数据

先列清单：

- FPSBodyKukriPresentationData.h 的八个独立数组已有 Jason / Kaitlin 两个自然分组，各约 480 行。提取 FKey 到 Types 头、四个 Jason 数组到 Jason 头、四个 Kaitlin 数组到 Kaitlin 头；原头保留 Sample / Equip / Uppercut 与原 include 入口。同步修改 `SourceAssets/KukriThirdPersonCompletion20261029/export_presentation.py` 的文件输出分组，保留原 .7f 格式和遍历顺序。当前已保存头按原文本移动，不重新求解或重采样动作。
- 另外十个头的长段均为连续多维采样数组，现有消费者直接按帧/变体/骨索引读取，见下方逐项结论。保留整个数组，不按行号切成 include 碎片、不加分块索引适配；这类拆分会增加生成和读取合同，不能算简单重复逻辑清理。

| 数据头 | 实际作者源（SourceAssets 下） | 结论 |
| --- | --- | --- |
| SpellbookAuthoredFocus | SpellbookEvildeer20261009/Focus/IntegratedV30/author_motion.py | 242 帧 × 27 骨的 Poses 与 ReturnRotations 两个连续数组；FocusPose / FocusInterrupt 仍消费，保留 |
| SpellbookAuthoredGrip | SpellbookEvildeer20261009/GripPhotoV3/author_grip.py | 65 姿态 × 27 骨连续数组；SpellbookComponent / BookOrientation 消费，保留 |
| SpellbookAuthoredStrike | SpellbookEvildeer20261009/QuickMelee/author_strike.py | 57 帧 × 27 骨连续数组，接触时刻由 QuickCombatMotion 共用，保留 |
| StaffAuthoredCastElbow20260930 | ApprenticeStaff20260927/CastElbowRepair20260930/author_pose.py | 四变体、六姿态、54 骨连续数组；旧版作者链产物，未证明可删，保留 |
| StaffAuthoredLeftGaitV16 | ApprenticeStaff20260927/LeftGaitV16/author_gait.py | 两步态、32 采样、27 骨连续数组；StaffFreeHandPose 消费，保留 |
| StaffAuthoredPoseV13 | ApprenticeStaff20260927/ArmSupportV13/author_pose.py | 四变体、六姿态、54 骨连续数组；旧版作者链产物，未证明可删，保留 |
| StaffAuthoredPrimaryV28 | ApprenticeStaff20260927/PrimaryWholeArmV28/author_motion.py | 四变体、五姿态、54 骨连续数组；StaffGripPose 消费，保留 |
| StaffAuthoredReleaseAnatomy20261001 | ApprenticeStaff20260927/ReleaseAnatomy20261001/author_motion.py | 四变体、六姿态、54 骨连续数组，附肘角与接触表；StaffGripPose 消费，保留 |
| UnarmedAuthoredLocomotion20261001 | UnarmedLocomotion20261001/author_locomotion.py | 连续双步态、32 采样、54 骨；UnarmedIdle 消费，保留 |
| UnarmedAuthoredPunch20261002 | UnarmedPunch20261002/author_punch.py | 连续左右拳、八关键帧、54 骨；UnarmedPunchPose 消费，保留 |

所有作者脚本实际路径均已定位。本批不执行作者脚本，不生成新动作、不测试；原计划按行数估算的数据分块数撤销，采用以上自然边界结论。

## 第 31 批：剩余合同与复杂度保留项

逐项清单与结论：

- AuthoredDungeonGenerator.cpp：原 PrepareAssembly 单函数 855 行，连续共享 State / Plan / Catalog / SceneModules / Graph / Edges 与捕获局部引用的装配队列；其回滚依赖新碰撞准备后才退役原场景。单独移动该方法仍是超长文件；进一步拆段需要新增装配上下文或跨阶段参数，并调整内部类型及既有 dressing inl 的可见性。本轮保留，不能把这种流程重构计作无复杂度增加的去重。
- FPSGAMECharacter.h、FPSPlayerBodyAnimInstance.cpp：沿第 27 批具体理由保留；反射合同、同帧工作线程局部状态不因行数阈值而改造。
- C04：ServerReportBodyAction 仍是 UFUNCTION(Server,Reliable) RPC，UHT 注册和 ServerRecordAction 的复制状态副作用仍在；未发现手写发起调用不等于证明外部入口无效。保留，不计为删除死代码。
- C06：ColdSteelNet GameMode 的两秒位置诊断位于 bAutoWalkDemo 判断前，属现行行为；保留。
- K01：Dungeon 兼容目录中的存档结构和 RecordKill 仍被奖励路径消费；保留。
- K02：InitialStrike、任务来源注册及 NormalizeTasks 仍参与 UI 正常路径；保留。
- K03：FPSFXAssetPreparation 已是技能/地牢共用工具；继续复用现有实现，不建第二套准备 helper。
- H01–H03 的剩余训练提交和完整回执：各组件私有状态、提交/取消时点不同，公共化需状态转发层；已完成的纯公式去重保持，剩余保留。
- R10：相同的一行冷却公式没有更合适的现有归属，新增包装不减少维护复杂度；保留。
- R11：IceWall / Blizzard 的五行输入判断若再提取会增加组件耦合，保留。
- R12：技能等级缺失返回 0 与缺省等级 1、Validate 与 Sanitize、稳定 ID 与本地化文案有实际行为差异，保留。
- R13：SkillCombatModel、NetCast::AuthorityModel 和 ColdSteelAuthority::ForPawn 对 NPC、远端及未知控制者有不同路由，保留。
- 火球：第 21 批已共用反馈、暴击训练和升级尾段；独立经验倍率、整数舍入与魂奖励保持原语义。本轮档案奖励共用同一升级尾段，不改变火球倍率。
- 规则文档：初始清理已完成 20 份规则入口与 333 处保留原因。本轮只追加实施回执，不扩大规则审计，不将用户后台制作、并行保护、不跨对话协调和不主动测试的工作约定当作“代码里没有”的旧规矩删除。

这些是按本轮标准作出的保留结论，不列为等待许可的隐性待办，不计为已拆分或已删除；若将来改变行为或接受更深重构，应重新列独立任务。


第 28–30 批源码结果：弓主文件 391 行、弯刀 589 行、双持手枪 582 行、符文剑 504 行、苍龙 413 行、武器特效 757 行；植被形变 698 行、丘陵世界 492 行、丘陵流送 793 行；身体弯刀动作入口 26 行，Jason / Kaitlin 数据各 487 行。所有新增实现按完整职责划分，新增数据按原作者家族划分。作者脚本只调整输出归属，未运行。

character-network 中间构建已退出 6：286 个构建动作走到链接阶段，错误为新迁出的武器方法尚未进入本次早先创建的构建动作图（LNK2001 / LNK2019 / LNK1120），没有新增 C++ 编译错误。全部新文件落盘后已重新调用 Build.bat，final 批次重新建立构建图；未启动第二个并行构建、未终止其他进程。

## 第 32 批：统一收尾

原清单 48 个长文件已逐项处置：本轮 33 个完成源码拆分，第 21 批已完成 2 个，保留 13 个（10 个连续生成数据头、Character 反射头、BodyAnimInstance、AuthoredDungeonGenerator）。本轮无未作结论的清单项；保留不等于已拆分。必要 Editor 构建已成功，退出码 0，DLL 已重新链接。未运行测试、lint、静态检查或游戏验收。

| 原文件（Source/FPSGAME 下） | 本轮处理前行数 | 本轮落盘行数 / 结论 |
| --- | ---: | --- |
| `Building/VoxelBuildComponent.cpp` | 1873 | 560 行；已拆分，统一构建完成 |
| `Building/VoxelBuildWidget.cpp` | 928 | 544 行；已拆分，统一构建完成 |
| `Building/VoxelBuildWorld.cpp` | 861 | 772 行；已拆分，统一构建完成 |
| `Characters/FPSBodyKukriPresentationData.h` | 985 | 26 行；已拆分，统一构建完成 |
| `Characters/FPSPlayerBodyAnimInstance.cpp` | 2671 | 复杂度保留，见第 27 / 31 批 |
| `Characters/FPSPlayerBodyEquipment.cpp` | 1131 | 783 行；已拆分，统一构建完成 |
| `Characters/FPSPlayerBodyMotion.cpp` | 859 | 534 行；已拆分，统一构建完成 |
| `Dungeons/AuthoredDungeonGenerator.cpp` | 2280 | 复杂度保留，见第 27 / 31 批 |
| `Dungeons/DungeonRunSubsystem.cpp` | 854 | 684 行；已拆分，统一构建完成 |
| `Dungeons/FacilityHallEncounter.cpp` | 847 | 710 行；已拆分，统一构建完成 |
| `FPSGAMECharacter.cpp` | 4830 | 647 行；已拆分，统一构建完成 |
| `FPSGAMECharacter.h` | 1043 | 复杂度保留，见第 27 / 31 批 |
| `Monsters/BlindSupplicantAuthoring.cpp` | 1127 | 584 行；已拆分，统一构建完成 |
| `Monsters/UnknownHumanoidTactics.cpp` | 843 | 756 行；已拆分，统一构建完成 |
| `Monsters/WildlifeAnimal.cpp` | 1036 | 793 行；已拆分，统一构建完成 |
| `Multiplayer/ColdSteelPlayerState.cpp` | 2734 | 361 行；已拆分，统一构建完成 |
| `Multiplayer/ColdSteelPlayerState.h` | 822 | 718 行；已拆分，统一构建完成 |
| `Production/ProductionToolComponent.cpp` | 940 | 629 行；已拆分，统一构建完成 |
| `Skills/ColdSteelSkillRules.cpp` | 401 | 第 21 批已完成 |
| `Skills/FPSQuickCombatComponent.cpp` | 345 | 第 21 批已完成 |
| `UI/ColdSteelCodexPage.cpp` | 1569 | 677 行；已拆分，统一构建完成 |
| `UI/ColdSteelHUDWidget.cpp` | 1739 | 617 行；已拆分，统一构建完成 |
| `UI/ColdSteelInventoryRules.cpp` | 824 | 734 行；已拆分，统一构建完成 |
| `UI/ColdSteelItemTooltipData.cpp` | 858 | 775 行；已拆分，统一构建完成 |
| `UI/ColdSteelProfileRuntime.cpp` | 1700 | 491 行；已拆分，统一构建完成 |
| `UI/ColdSteelSkillPage.cpp` | 1510 | 383 行；已拆分，统一构建完成 |
| `UI/ColdSteelSmeltingWidget.cpp` | 1278 | 771 行；已拆分，统一构建完成 |
| `UI/ColdSteelWorkbenchWidget.cpp` | 940 | 645 行；已拆分，统一构建完成 |
| `UI/TransitLoadingSubsystem.cpp` | 1167 | 745 行；已拆分，统一构建完成 |
| `Weapons/Bow/BowWeaponComponent.cpp` | 2078 | 391 行；已拆分，统一构建完成 |
| `Weapons/FPSWeaponFXComponent.cpp` | 1747 | 757 行；已拆分，统一构建完成 |
| `Weapons/Kukri/KukriWeaponComponent.cpp` | 1194 | 589 行；已拆分，统一构建完成 |
| `Weapons/PistolDualWieldComponent.cpp` | 990 | 582 行；已拆分，统一构建完成 |
| `Weapons/RuneSwordAzureDragon.cpp` | 1029 | 413 行；已拆分，统一构建完成 |
| `Weapons/RuneSwordComponent.cpp` | 1999 | 504 行；已拆分，统一构建完成 |
| `Weapons/Spellbook/SpellbookAuthoredFocus.h` | 14049 | 连续生成数据保留，见第 30 批 |
| `Weapons/Spellbook/SpellbookAuthoredGrip.h` | 1918 | 连续生成数据保留，见第 30 批 |
| `Weapons/Spellbook/SpellbookAuthoredStrike.h` | 1666 | 连续生成数据保留，见第 30 批 |
| `Weapons/Staff/StaffAuthoredCastElbow20260930.h` | 1369 | 连续生成数据保留，见第 30 批 |
| `Weapons/Staff/StaffAuthoredLeftGaitV16.h` | 1898 | 连续生成数据保留，见第 30 批 |
| `Weapons/Staff/StaffAuthoredPoseV13.h` | 1369 | 连续生成数据保留，见第 30 批 |
| `Weapons/Staff/StaffAuthoredPrimaryV28.h` | 1137 | 连续生成数据保留，见第 30 批 |
| `Weapons/Staff/StaffAuthoredReleaseAnatomy20261001.h` | 1411 | 连续生成数据保留，见第 30 批 |
| `Weapons/Unarmed/UnarmedAuthoredLocomotion20261001.h` | 3852 | 连续生成数据保留，见第 30 批 |
| `Weapons/Unarmed/UnarmedAuthoredPunch20261002.h` | 999 | 连续生成数据保留，见第 30 批 |
| `WorldGeneration/GrassDeform/GrassDeformSubsystem.cpp` | 1047 | 698 行；已拆分，统一构建完成 |
| `WorldGeneration/TemperateHillsStreaming.cpp` | 1758 | 793 行；已拆分，统一构建完成 |
| `WorldGeneration/TemperateHillsWorld.cpp` | 1074 | 492 行；已拆分，统一构建完成 |

恢复依据：本轮 manifest.json 保存每个原文件的处理前字节数与 SHA；before/ 保存原文件字节快照，edits.jsonl 保存各次写入路径/行数/SHA。并行修改仍归原工作区所有，未重置、暂存、提交或推送。


final 构建返回退出码 6，57 个计划动作中执行了 54 个编译动作后因本轮拆分问题未链接：FPSWeaponTracers 的 BuildTrailColumn 缺少原函数闭合括号；流送内部头的 FStreamableHandle 应前置声明为 struct；EntryVegetationRadius 原值 1600.0 需随共享常量迁移。三处均已按原定义修正，随后启动 final-resume 必要续编。无调校、算法或功能变更。

本轮共写入 126 个源码/作者路径，其中 34 个原有、92 个新建；manifest 的 edited_paths 明确记录归属。before/ 另含少数新文件修正前快照，其总数不能当作原有文件数量。构建失败记录保留，不以源码已落盘替代 DLL 成功链接。

final-resume 构建完成 86 个编译动作并进入链接（89 个计划动作），本轮拆分问题未再出现；最终退出 6，缺少 GetUplandGroundPatches 链接符号。定向读取发现其实现已在共享工作区新建的 TemperateHillsUplandCover.cpp 落盘，但未进入这次更早建立的构建图。本对话没有修改该方法或其调用，现重新建立构建图执行 final-resume2，不把其他并行工作计作本轮源码改动。

final-resume2 已重新纳入新增源文件；UBT 使 makefile 失效后安排 1195 个构建动作，正在后台执行。该构建覆盖共享工作区当前目标，不等同于本轮修改了全部这些文件，也不是测试。待此轮最终回执到位再更新完成状态。

final-resume2 运行中观察到共享头 `TemperateHillsWorld.h` 在 09:43:02 被外部工作更新：GameMode 的 UCLASS / GENERATED_BODY 已在 452 / 455 行，而本轮先前生成的 UHT 宏仍为 451 / 454，导致 C2143 / C4430。该头不在本轮写入清单；不覆盖其更新，不手改生成头，等待当前构建自然退出后由下一轮 UHT 正常重建。以上时间取文件及构建原始回执。

final-resume2 最终回执：退出码 6，UBT 1868.73 秒，1195 个计划动作中执行 1192 个编译动作，未链接。错误归属为构建期间外部更新的 TemperateHillsWorld / HillsBlacksmith 反射头、尚未生成的 VillageBlacksmithResident.generated.h 及其派生生成代码；本轮未修改这些头或生成产物。当前构建自然结束后已启动 final-resume3，由 UHT 重新识别当前反射声明后续编，未终止进程或跨任务协调。


### 最终收尾回执（已完成）

等待共享 UBT / 编译器退出后，final-resume3 于原始回执时间 **2026-11-18 10:15:39–10:16:30（+08:00）** 完成后台 `FPSGAMEEditor Win64 Development`。Build.bat 入口又自动等待了一次已有脚本，不抢锁、不终止其他进程。最终返回 **Succeeded、退出码 0**，UBT 耗时 **16.46 秒**。

本次独立续编完成 **4 个动作**：编译共享工作区已提供的 TemperateHillsCompatibility.cpp、链接 lib、链接 UnrealEditor-FPSGAME.dll、写入目标元数据。此前反射头/生成代码同步已随共享工作区的更新和构建到位，不将外部代码修正或共享编译动作记作本轮源码修改。没有在成功后重复构建。

- 本轮第 23–31 批：33 个原长文件拆分及档案奖励尾段去重完成；34 个已有源码/作者文件改动、92 个新建源码文件，合计 126 个写入路径。
- 原 48 项：累计 35 项拆分完成，13 项按数据合同、反射合同或复杂度明确保留；C04 / C06、K01–K03、H / R 差异也全部给出处置结论。没有悬空的待实施批次，也未把保留项计作已删除。
- 没有新增功能、运行测试、lint、额外静态检查、运行验收、编辑器或游戏启动。源码和必要构建产物已落盘，行为与运行效果由用户自行测试。

[最终构建回执](all-batches-20261117/build-final-resume3-20261118-101539.json)；最终 Editor 构建日志（本机资料：`Saved/BuildEditor/cleanup-all-final-resume3-20261118-101539.log`，不随本次发布）。
