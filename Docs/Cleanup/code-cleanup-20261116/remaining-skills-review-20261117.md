# Skills 保留项定向检查

日期：2026-11-17。用户本轮明确授权检查，并选择“本批 Skills 保留项，以及报告中明确列出的疑似死代码调用链”。此文先列检查清单，完成后写入证据与结论；检查期间不修改业务源码。

## 1. 范围和预先清单

仅在 `Source/FPSGAME/Skills` 按功能定位；C04 允许只读追踪 `ServerReportBodyAction → ServerRecordAction` 在 Characters、Multiplayer 及相关工具中的入口与消费者。不检查报告其他 46 个超长文件，不扩大到 C06 插件诊断清理。火球独立经验缩放保留，不删除疑似死代码、不拆超长源码、不添加功能、不编译或运行测试、不启动 UE。

| 编号 | 最多三级职责 | 检查对象与问题 | 本次交付 |
| --- | --- | --- | --- |
| R01 | 武器与战斗 → 技能魔法 → 规则与权威结算 | ColdSteelSkillRules.cpp 的目录、迁移、成长、快照及命中职责 | 基于现有函数边界的拆分方案与依赖 |
| R02 | 武器与战斗 → 技能魔法 → 快速近战 | FPSQuickCombatComponent.cpp 的配置、时钟、表现与命中 | 拆分方案，保留武器类型与动作时钟差异 |
| R03 | 联机与持久化 → 动作同步 → C04 兼容入口 | ServerReportBodyAction / ServerRecordAction 的声明、调用和替代路径 | 明确可达性证据与死代码判定边界 |
| R04 | 武器与战斗 → 技能魔法 → 武技修炼提交 | DashAttack、Whirlwind、ChainSlash、LeapStrike、HeavyStrike | 逐入口对照经验、状态与提交条件 |
| R05 | 武器与战斗 → 技能魔法 → 施法生命周期 | 冰锥、冰墙、圣光、雷击、火甲/领域的预留、取消、退款、提交 | 不同状态机的证据与可共用范围 |
| R06 | 武器与战斗 → 技能魔法 → 目标与地面 | HolyLight、Lightning、MagicOcclusion、MeteorGround、MagicArrowRainGround、FireMagicArea | 遮挡、筛选、坡度和净空区别 |
| R07 | 武器与战斗 → 技能魔法 → 数值与习得 | 冷却、元素/专精、技能树与训练等级 | 运算顺序、限幅和缺省等级区别 |
| R08 | 武器与战斗 → 技能魔法 → 表现与后台准备 | IceArmorPresentation、LightningHastePresentation、PlayerSkillRenderPreparation 及相关投射物准备 | 生命周期、所有权及有效诊断入口 |
| R09 | 武器与战斗 → 技能魔法 → 公共接口与身份 | 单行访问器、常量、类型及伤害标识 | 是否存在值得独立去重的业务逻辑 |

## 2. 检查结论

本轮按 R01–R09 完成定向源码检查，未修改业务源码、资产、规则或构建配置；未编译、测试、运行 Commandlet 或启动编辑器。第 1–15 批及原 Editor 构建完成记录不变。此句描述检查阶段；随后用户授权实施 P01/P02，源码结果见本文第 10 节及主报告第 26 节。仍不能把“已列清单完成”理解为 Skills 已不存在重复。

- 两个超长文件仍为 **973 行 / 82,301 字节**、**813 行 / 42,143 字节**，分别给出三个实现单元的方案；不迁移反射类型，不新增 UE 编译模块。
- **C04 无已证实可删除项**。定向检索没有发现手写发起调用，但 RPC 仍生成并注册，且仍会修改复制状态；结论保持“疑似遗留、不能直接删除”。
- **两个优先候选 P01/P02**：冲刺攻击与旋风的训练重复；四个法术完全同型的冷却倍率尾段。检查时只列方案；随后两项已在第 16 批完成源码去重及 Editor 构建，82 个动作完成、退出码 0。
- **三个确认重复项 H01–H03**：检查时暂保留；随后第 17 批仅提取 H01 经验公式与 H02 冷却追时公式，源码与 Editor 构建已完成（33 个动作、退出码 0）。其余训练/回执状态处理及 H03 继续保留，原因是公共接口成本或局部收益，不误记为“行为一定不同”。
- 第 18 批沿这些入口继续提取三组局部复用：冰墙反馈、火球组件模型读取及冰甲/雷迅相同冷却倍率；详见第 12 节。其余状态机、目标筛选、精度/限幅、表现和准备生命周期差异仍保留。火球独立经验缩放未参与修改。

以下路径若仅写文件名，均相对于 `Source/FPSGAME/Skills/`。行号为本轮读取时的工作区位置，后续并行修改可能移动行号；这里只说明读取到的实现，不声明运行行为已测试。

## 3. R01：ColdSteelSkillRules.cpp 拆分方案

### 当前职责与证据

| 函数块 | 当前行号 | 实际职责 |
| --- | --- | --- |
| LoadDefinition | 54–446 | 先填技能默认值，再读取 `ColdSteelData/skills.json`，逐技能解析参数；101–108 保留失败回退及非有限数回退。 |
| Migrate / Validate | 447–586 | 版本 0–32 的旧档补齐与数据合法性；不能把旧版本分支当死代码。 |
| IsRifle / IsPistol / IsCriticalHit | 587–609 | 武器分类与各怪物专属弱点识别；不属于目录加载。 |
| Effect / ExperienceRequired / AddExperience / EffectSummary | 610–658 | 常驻效果、等级经验、修炼推进和摘要；AddExperience 在 641 行检查是否习得。 |
| Snapshot | 659–823 | 武器/装备与影子档案快照；676 行包含函数内静态攻击序号。 |
| NetHitForward / AwardKillByOwner / NotifyKillByOwner / GrantBerserkOnWeaponHit / ApplyHit / IsMasteryTrainingTarget | 824–973 | 权威路由、伤害、奖励归属、命中附加效果和训练目标；客户端转发在 860–863 行先于本地结算。 |

### 建议三个实现单元

| 目标 | 移动范围与保留内容 | 预计规模，非已实施结果 |
| --- | --- | --- |
| 原 ColdSteelSkillRules.cpp | 保留 LoadDefinition；仅留下目录解析直接需要的 include。 | 约 410–450 行 |
| 新 ColdSteelSkillProgression.cpp | Migrate、Validate、Effect、ExperienceRequired、AddExperience、EffectSummary。 | 约 210–240 行 |
| 新 ColdSteelSkillCombat.cpp | 武器/弱点分类、Snapshot 及 824–973 行的权威命中/奖励函数。 | 约 380–430 行 |

`ColdSteelSkillRules.h` 当前只有 34 行，保留声明、默认参数和导出名；三个 .cpp 留在现有 FPSGAME 模块，不改 Build.cs。拟用的两个新文件名目前不存在。`ColdSteelAdditionalMasteries.cpp:5–10` 已拥有 AdditionalDefinitions 静态缓存，`ColdSteelSkillTree.cpp:122` 已拥有技能树缓存；拆分不复制这些缓存，也不把 LoadDefinition 改成新加载机制。Snapshot 的 NextMasteryAttack 和 NetHitForward 的函数内静态实例各保留唯一实体，不放进会被多翻译单元实例化的头文件。

还发现两项只能在后续获准修改该超长文件时处理的局部问题：

- 15、19 行重复包含 `../Monsters/MonsterCombatComponent.h`，属于明确重复 include。
- 494 行“only <11 reaches here”注释与当前 449–473 行的版本分支不符：例如版本 20 也能到达该处。应修正注释，不能据此删除 493 行以后的兼容初始化；本轮未改注释或迁移行为。

## 4. R02：FPSQuickCombatComponent.cpp 拆分方案

### 建议三个实现单元

| 目标 | 保留/迁移的现有方法 | 预计规模，非已实施结果 |
| --- | --- | --- |
| 原 FPSQuickCombatComponent.cpp | 构造、BeginPlay、Model、BeginAction、PhaseForAge、ActionSourceDuration/Remaining、Cancel、IsImpactPaused、TickComponent、AdvanceAction、FinishAction、EndPlay、ActionDuration/Remaining。 | 约 350–400 行 |
| 新 QuickCombatPresentation.cpp | 48–144 行 Configure 系列及弓反冲/源播放速率访问器；259–469 行 PhaseFraction、LayerWeight、GetCameraFOV、GetCameraMotion。 | 约 325–360 行 |
| 新 QuickCombatContact.cpp | 647–791 行 ContactHit，保留各武器目标查询、快照、反馈、音效与击杀待结算标志。 | 约 170–195 行 |

头文件 `FPSQuickCombatComponent.h` 当前 98 行，UCLASS、字段和私有方法不变；同一个类的方法可分布在这些实现单元，不额外创建组件或转发表。两个拟用文件名目前不存在。已有 `WarhammerQuickCombat.cpp:18/28` 分别拥有 ConfigureForWarhammer 和 ContactWarhammer，继续留在原文件，不把它们搬回主文件或复制到新接触文件。

必须保留的差异：

- BeginAction 的徒手分支（185–195）发起 GenericMelee 并支付普通攻击体力；其他分支（199–200）提交 quickCombat 并发放使用修炼。FinishAction（795–799）也有对应排除，不能统一为“每次动作都训练 quickCombat”。
- TickComponent（473–484）有由角色先行推进的武器分支，不能一律自行 AdvanceAction，否则同一帧会推进两次。
- ActionSourceDuration/Remaining（208–237）包含弓的源时钟映射、ASH12 分段速度及确认命中停帧；AdvanceAction（527–645）分别处理这些时钟、锤头停帧、准确接触帧与普通累计。
- ContactHit（747–790）允许弓在本地物理接触时预测反冲/声音，伤害、击退、修炼与命中反馈仍使用权威结果；不能把所有反馈门禁并为 `Applied > 0`。
- 131–142 行书推与徒手已经复用 ConfigureForStaffPunch，再分别设置 Style；这是已有共享路径，不应继续包装一层。

该方案只移动现有方法，不改手别、技能门槛、音效时点、专属速度或网络回执。实施顺序建议先移纯表现，再移接触结算，最后整理原文件 include；本轮没有执行这些操作。

## 5. R03 / C04：疑似死代码调用链

明确入口：`Multiplayer/ColdSteelPlayerState.h:247–248` 为 `UFUNCTION(Server, Reliable)` 的 ServerReportBodyAction；没有 BlueprintCallable 标记。其实现（`.cpp:2267–2274`）取拥有者控制器/Pawn/Body 后调用 `Characters/FPSPlayerBodyActions.cpp:742–754` 的 ServerRecordAction。

| 证据层 | 本次结果 | 可以得出的结论 |
| --- | --- | --- |
| 手写 C++ 与文本工具 | 对 `Source/FPSGAME`、`Plugins/ColdSteelNet/Source`、`Tools/Multiplayer`、`Config` 只检索两个精确符号。结果仅为两处声明、两处定义及 RPC 实现内的一处调用；没有发现手写代码发起 ServerReportBodyAction。 | 支持“疑似闲置”，不能据此认定反射入口不存在。 |
| 当前生成代码，只读 | `Intermediate/Build/Win64/UnrealEditor/Inc/FPSGAME/UHT/ColdSteelPlayerState.gen.cpp:5743–5749` 仍有包装；5802–5809 有执行跳板；7376 和 7460 保留注册。 | 当前生成产物仍暴露该 RPC；生成代码不是实际调用者证据，也不是死代码。未重新运行 UHT。 |
| 当前主要同步路径 | `Characters/FPSPlayerBodyComponent.cpp:474` 调用 SendBodyPresentation；`FPSPlayerBodyNetwork.cpp:117–121` 调用 ServerBodyTransition / ServerBodySnapshot；144–152 进入 AcceptBodyPresentation 并检查序号，153–154 检查动作/运动枚举。 | 新快照路径确实已有手写发起方，旧 RPC 不在这条主链上。 |
| 旧实现仍有副作用 | `FPSPlayerBodyActions.cpp:744–753` 改写 ReportedPresentation、LastPresentationReceivedAt、DisplayState、ReplicatedState 并 ForceNetUpdate；745 行注明旧事件不得消耗客户端序号。 | 若旧入口被调用，行为并非空操作；不能只删除方法体。 |

结论：**保留，未证明可删除**。没有启动 UE 做资产引用解析、没有记录运行调用覆盖，也未确认历史客户端/外部反射调用约定。RPC 的存在与正常业务是否使用是两个问题。其所在 PlayerState 头/实现仍为 822 / 2730 行，本轮只读目标片段，未扩大为这两个文件的完整审计或拆分。

后续若决定正式退役，应先确认动态调用与兼容范围，再将 RPC 声明、实现及 Body 方法视作一个退役单元；不手工修改生成代码，不把正常 ServerBodyTransition / ServerBodySnapshot 一并删除。本轮没有执行退役。

## 6. R04 / R07：优先去重候选

### P01：冲刺攻击与旋风的训练函数

`ColdSteelDashAttackModel.cpp:93–99` 与 `ColdSteelWhirlwindModel.cpp:75–81` 除技能键以外，经验表达式、XP/满级早退、SyncRuntime、Snapshot、AddExperience、StageTraining 都相同。文件分别 99 / 81 行，符合后续小范围处理上限。

可优先抽取其纯经验计算，或在不扩大私有模型接口的前提下复用已有训练入口；支付、冷却和动作提交不参与本项。原表达式的加法次序是“命中 + 多目标 + 击杀”；`ColdSteelSpellRewards.h:28–31` 的现有 helper 是“命中 + 击杀 + 多目标”，因此严格保持运算顺序时不能机械替换后宣称逐步计算完全相同。保留原整数类型、调用位置、早退及不增加使用/多杀奖励。

旧报告把整个武技训练组归因于行为差异过于笼统，检查时本项更正为“重复已确认”；后续实施结果见第 10 节。

### P02：四个法术的同型冷却倍率尾段

精确入口：`ColdSteelHolyLightModel.cpp:61`、`ColdSteelIceSpikeModel.cpp:63–64`、`ColdSteelLightningModel.cpp:65`、`ColdSteelIceWallModel.cpp:60`。四处均使用 double 的 CooldownReduction，目标 Cooldown 字段为 float，先做 `Cooldown *= Max(.2, double(1-CooldownReduction) * (1-SetEffect(...)))`，再做第二次 `Cooldown *= Rune.SkillCooldown * Rune.MagicCooldown`。

可在已有 Skills 内部 helper 中提取这两个赋值，按原位置传入已计算的倍率，保留每次赋值回 float 的舍入。不能合成一次连续乘法或调换 SetEffect 的读取时点，也不合并各法术此前不同的基础冷却计算。

`ColdSteelFireMagicModel.cpp:49/67` 的 CooldownReduction 是 float，减法先在 float 中完成；暴风雪（39/55）与电系（42/58）另有显式 float 转换及 `[0,300]` Clamp，本项不包括这些入口。四个候选文件当前分别 129 / 121 / 129 / 141 行。

## 7. 已确认重复，但暂保留的局部实现（检查时）

| 编号 | 精确入口 | 重复与区别 | 本次建议 |
| --- | --- | --- | --- |
| H01 | ColdSteelChainSlashModel.cpp:60–66；ColdSteelLeapStrikeModel.cpp:67–73 | 同样先排除未学/满级，再计算“使用 + Max(0,Kills)×击杀 + 多杀”，再提交；分别读取 D.ChainSlash / D.LeapStrike 的 MultiKillExperience。 | 确认训练骨架重复。仅为一行增加泛型入口收益有限，可与下一轮训练整理合并考虑；不统一它们的施法支付。 |
| H02 | ColdSteelChainSlashModel.cpp:43–58；ColdSteelLeapStrikeModel.cpp:50–65 | 回执主体同构，仅冷却字段不同；包括耗竭观察、累计体力合并、Revision 判定、服务器时间追算、Dirty 与广播。 | 确认重复；先复用已有 UppercutStaminaReceipt::Merge，不为消除少量重复暴露私有 Current/通知状态。纯追时计算可候选，整段参数化暂保留。 |
| H03 | FPSHolyLightComponent.cpp:230–248；FPSLightningComponent.cpp:254–272 | Accepted / Rejected / Cancelled 结构相同，仅退款技能键不同；释放后仍保留 NetPaidMana / bNetResultPending 直到回执。 | 确认重复，不声称这对回执本身有行为差异；目前不为它们引入共用状态基类或大量私有状态引用参数。两种完整施法/选目标流程仍不同。 |

支付事务必须另外保留：Whirlwind（48–72）含逐风冲刺特殊分支并通过 Snapshot/CommitState；ChainSlash（22–40）与 LeapStrike（28–47）直接更新 Current、累计 UppercutStaminaSpent、观察耗竭；SwordUppercut（ColdSteelHeavyStrikeModel.cpp:42–66）还可能先发送客户端释放请求。共享训练计算不等于这些事务可以合并。

重击训练（ColdSteelHeavyStrikeModel.cpp:78–86）只取最高达成档位，按 5 杀 / 5 命中 / 2 杀 / 2 命中 / 使用依次选择；上挑（69–75）为击杀优先、否则命中、否则使用，并 FindOrAdd 技能记录。它们与累计经验公式不同，继续保留。

## 8. R05–R09：保留行为差异的具体证据

| 检查项 | 证据位置 | 保留原因 |
| --- | --- | --- |
| 冰锥的预留/完成 | ColdSteelIceSpikeModel.cpp:69–75、111–120；FPSIceSpikeComponent.cpp:242–253；FPSIceSpikeVolley.cpp:400–409、510–516 | Begin 支付并置 bIceSpikeReserved，普通 Finish 要求预留并清除；元素箭另走训练路径；取消按 Phase==2 退款。Volley Finish 有 bFinished 门禁，EndPlay 会触发结算，不能当纯表现销毁。 |
| 冰墙的预留/释放 | ColdSteelIceWallModel.cpp:65–78；FPSIceWallComponent.cpp:287–315 | 单独记录 IceWallReservedMana，释放时清预留；组件保留 PaidMana、Seed/Preview、2.5 秒权威墙未达退款。Cancelled 回执本身不再退款，防止和 Cancel 重复。 |
| 火甲与雷暴领域 | FPSFireMagicComponent.cpp:499–512；FPSStormDomainNetwork.cpp:18–58 | 各自持有释放时奖励模型；先清奖励批次/引用，再在权威且存活条件下结算。领域在 FadeDomain 已结算，视觉尾段与 FinishDomain 分开；不能按统一 Destroy 时点结算。 |
| 圣光目标与雷击遮挡 | FPSHolyLightComponent.cpp:44–59、160；HolyLightTargets.cpp:25–44；FPSLightningComponent.cpp:44–61 | 圣光可以治疗友方、检查生命值，视线是单射线；雷击排除友方，并用多点暴露及玻璃特判。共用 UI/手势不代表可共用目标判断。 |
| 开放栏杆与地面区域 | MagicOcclusion.cpp:8–17、19–65；FireMagicArea.cpp:13–24、37–59 | 仅忽略标记的穿透组件，整段重查最多 16 次；身体五点采样；地面技能另做脚点、法线高度带、目标体半径和玩家/敌方分支。不能忽略整座楼梯/建筑或省略地面带筛选。 |
| 陨星与箭雨 | MeteorGround.cpp:5–23；MagicArrowRainGround.cpp:14–49 | 陨星有法线阈值 .45、2 cm 距离容差、可选视线及地面复核；箭雨已经复用该验证，但还需屋顶高度和 20 段引导箭净空。Select 已查地面，不应再次重复 Trace。 |
| 基础数值与取整 | HolyLightModel:26–33、58–61；IceSpikeModel:33、61–64；IceWallModel:28–38、57–60；ElectricMagicModel:23–28、56–58 | 圣光按等级步长减冷却，冰锥插值且保留下限，冰墙保持固定基础冷却；冰墙 INT/WIS 物理冲击使用两次 FloorToFloat，不是通用魔法伤害。此行的 Model 文件名均以 ColdSteel 开头。 |
| 已学与缺省等级 | ColdSteelAdditionalMasteries.cpp:12–17；ColdSteelSkillTree.cpp:125–134；ColdSteelSkillTypes.h:27–31；ColdSteelSkillRules.cpp:636–648 | FindRef 缺省构造的 Level 为 1；MasteryProgress 对未学/无记录返回 0；SkillLevel 也考虑习得，旧树版本另有迁移兼容；AddExperience 检查习得。不能用同一个 getter 替换这些语义。 |
| 冰甲与雷迅表现 | IceArmorPresentation.cpp:21–50、65–81、129–149；LightningHastePresentation.cpp:25–50、74–90 | 冰甲拥有壳、镜片、雾、碎片和衣物遮挡，结束保留消散；雷迅持有借用骨骼的 Tick 前置关系和弧线路径，结束解除依赖并销毁。两处已有 ClearLimbTickPrerequisites 复用，不能统一整个清理状态。 |
| 准备宿主与运行实例 | PlayerSkillRenderPreparation.cpp:22–50、59–92；PlayerSkillPreparation.cpp:158–174、296–319 | 隐藏代表实例是准备宿主所有，切换资产销毁；龙息自有体积跳过通用代表；加载 30 秒/渲染 10 秒超时由队列拥有。不是实际施法，也不替代远端投射物自己的初始化与结束结算。 |
| 远端电弧与冰锥 | FPSLightningArc.cpp:163–198；FPSIceSpikeVolley.cpp:400–409、510–516 | 电弧根据复制的种类准备表现并等待数据；冰锥拥有奖励结算及来源通知。不能通过共享“特效准备/销毁”函数掩盖玩法所有权。 |
| 诊断入口 | SkillNetworkAuditCommandlet.cpp:34、40；LightningHasteVisualAudit.cpp:39；IceArmorNetworkAudit.cpp:20 | Main 根据 LightningHasteVisual / IceArmorOnly 参数调用具体实现，有静态可达入口；不是由于“测试代码”身份就可删除。本轮只读取，未运行。 |
| 单行方法与伤害类型 | FPSQuickCombatComponent.h:36–65；Characters/FPSPlayerBodyActions.cpp:480–494；ColdSteelHolyLightModel.cpp:99、ColdSteelIceSpikeModel.cpp:101、ColdSteelLightningModel.cpp:104 | 身体采样实际调用动作时钟接口；三个空 UDamageType 子类分别作为 StaticClass 传入伤害函数，具有独立反射身份。单行/空类体不等于死代码，不增加参数化包装。 |

上述是按清单入口的检查，不是这些目录每个函数均已审计，也没有把“保留”当作运行正确性的验收结论。

## 9. 后续次序与交付边界

1. 检查阶段建议优先实施 P02 的四处冷却尾段和 P01 的两处训练；两项已在后续第 16 批按精确清单完成，见第 10 节。H01–H03 后续按复杂度筛选的实施/保留结果见第 11 节，不为减少行数增加新的状态框架。
2. 两个超长文件只交付第 3、4 节方案；原“超过 800 行文件不动”边界未因本次检查授权而解除。
3. C04 仍是待确认兼容入口，不安排删除。其他 46 个超长文件、插件诊断 C06、火球独立经验缩放和资产二进制不在本次检查范围。
4. 本次只写本检查文档、主报告及拆分方案中对应的两行/说明。没有源码修改、编译或测试；运行效果仍由用户测试。

## 10. P01/P02 后续实施状态（第 16 批）

用户在检查后明确授权实施这两组优先项。按主报告第 26 节先列八文件清单，再保存原件并完成源码去重；本节不改写前面检查时的证据行号。

P01：两个武技入口共用现有 ColdSteelSpellRewards.h 的 MartialHitTrainingExperience，原“命中 + 多目标 + 击杀”加法次序不变；早退和私有训练提交留在拥有者。P02：四法术共用 ColdSteelSpellCrafting.h 的 ApplyCooldownMultipliers，保持两次 float 赋值、原 double 倍率和调用位置。

源码及 Editor 构建均已完成：等待共享构建和用户关闭项目编辑器后，18:43:49–19:02:49 执行后台构建，返回 Succeeded、退出码 0、82 个动作完成，重新链接 UnrealEditor-FPSGAME.dll，UBT 耗时 1136.17 秒。两项之外的 H01–H03、C04、超长文件和火球独立经验缩放保持原状。没有新增功能或测试，未主动启动编辑器或游戏；运行效果仍由用户测试。

实施清单、前后尺寸、构建与恢复记录见[主报告第 26 节](../code-cleanup-20261116-report.md)及[第 16 批源码清单](batch-16-training-cooldown/source-manifest.json)。

## 11. H01–H03 后续实施状态（第 17 批）

用户要求只清理能保持行为不变且不增加复杂度的部分，主报告第 27 节在源码修改前列出四文件精确清单。只修改 ColdSteelChainSlashModel.cpp、ColdSteelLeapStrikeModel.cpp、ColdSteelSpellRewards.h、NetCastUtils.h，最大修改后文件 85 行；不新增源码文件。

- H01：提取纯经验公式 MartialKillTrainingExperience，保留原 int32、负击杀数归零、多杀条件和加法顺序；各自定义的 MultiKillExperience 显式传入。资格判断和私有 StageTraining 提交不合并。
- H02：提取纯冷却追时公式 RemainingCooldown，保留 double 时间差先归零、转 float 后相减并再次归零。服务器时间读取仍在原 Revision 分支内；体力、耗竭、Duration/Revision、Dirty 与广播不改。
- H03：保持 Accepted / Rejected / Cancelled 原实现；不引入多私有状态参数、通用基类或只包装两三条赋值的间接层，也不把本地流程转调固定 Phase 的网络回执。此项是明确保留，不宣称已消除重复。

源码与必要 Editor 构建已完成：等待共享构建退出后，于 19:39:01–19:40:55 完成 33 个动作，返回 Succeeded、退出码 0，重新链接 UnrealEditor-FPSGAME.dll，UBT 耗时 113.83 秒。H01/H02 的剩余状态处理、H03、C04、两个超长文件和火球独立经验缩放保留；没有新增功能或测试，运行效果由用户测试。实施与构建详情见[主报告第 27 节](../code-cleanup-20261116-report.md)及[第 17 批源码清单](batch-17-h01-h03/source-manifest.json)。

## 12. 剩余局部复用（第 18 批）

用户继续授权在现有边界内清理。按主报告第 28 节先列五文件清单，再实施 C24–C26；没有扩大到超长文件、疑似死代码或其他模块。

- C24：冰墙反馈的 FWeaponDamageResult 默认 bCritical=false，和既有 NotifyHit(...,false) 等价；复用时保留死亡查询、角色 Cast/通知、训练计数和冰缓的原先顺序。
- C25：火球组件的 Model() 与 LocalModel 分支相同，直接复用；同时清除同文件重复的 FPSCombatHealthComponent include 和本次替换后无直接用途的两个 include。此项不涉及火球独立经验缩放、奖励模型或预扣/退款相位。
- C26：冰甲与雷迅冷却倍率彼此完全同型，但不同于四法术两次赋值版本。仅这两者共用 AuraCooldownMultiplier，保留 float 阶段、两个 double 符文倍率的左结合顺序和最终一次 float 赋值；法杖门禁和属性读取时点不移动。

共修改五个已有 Skills 文件，最大修改后文件 646 行；无新增源码文件、状态结构或功能。19:46:45–19:48:00 后台 Editor 构建成功，14 个动作完成，退出码 0，UBT 耗时 73.39 秒，并重新链接 DLL。未测试或启动编辑器/游戏，运行效果由用户测试。

H01/H02 的剩余状态处理、H03、火甲 float 减法、暴风雪/雷暴 Clamp、不同的支付与目标/生命周期继续保留；本次定位入口中的可清理项已完成，不以整模块无重复作为结论。详见[主报告第 28 节](../code-cleanup-20261116-report.md)及[第 18 批源码清单](batch-18-local-reuse/source-manifest.json)。

## 13. 箭雨回执复用与新增保留记录（第 19 批）

先按主报告第 29 节列清单，仅实施 C27：MagicArrowRainResources::Apply 复用已有 NetCast::RemainingCooldown，保持原资源修订号门槛、服务器时间读取、本地世界时间回退和 float 转换/归零次序；体力、魔力、箭数、预留状态、AdoptNetMirror 与广播不动。唯一源码修改文件 MagicArrowRainResources.cpp 为 34→35 行，没有新增 helper、文件、状态结构或功能。

R10：照明箭/箭雨的一行冷却倍率同型，但无直接同合同入口，不为单行再加包装或用虚拟零参数套用另一公式。R11：冰墙/暴风雪 InputAvailable 同型，但没有已有共享输入入口，不把它塞进轨迹绘制/网络工具或新建状态框架；两项继续保留。火球投射物的权威模型回退也没有套用带其他施法者分支的 AuthorityModel，不触及奖励路径。

等待共享 Game 构建退出后，19:58:25–19:59:00 本批 Editor 构建完成 4 个动作，返回 Succeeded、退出码 0，UBT 耗时 34.12 秒，已重新链接 DLL。没有测试、启动编辑器/游戏或跨对话协调。H01/H02 的剩余状态处理、H03、超长文件、疑似死代码及火球独立经验缩放继续保留；运行效果由用户测试。

详情见[主报告第 29 节](../code-cleanup-20261116-report.md)及[第 19 批源码清单](batch-19-arrow-receipt/source-manifest.json)。

## 14. 专精等级读取（第 20 批）

按主报告第 30 节先列清单，仅实施 C28：ColdSteelSkillTree::SpecRank 内层手写 Find/判空/缺省 0 分支改用已有 TMap::FindRef。保留外层专精不存在时返回 0，已有 int32 值原样返回，不插入记录或增加限幅。只修改 ColdSteelSkillTree.cpp，前后均为 286 行；没有新增 helper、类型、源码文件或功能。

R12 继续保留：未学/缺失技能等级与默认技能记录 Level=1 的差异、Validate/Sanitize 的校验/修正职责、技能/专精条件及 ID/名称文案不同，不为同形分支强行合并。奖励批次结构、资产就绪判定以及此前 H01/H02、H03、R10/R11 保留项也未改；超长文件、疑似死代码和火球独立经验缩放不动。

等待已运行的后台 UE 进程退出后，20:37:33–20:38:03 本批 Editor 构建完成 6 个动作，返回 Succeeded、退出码 0，UBT 耗时 29.70 秒，已重新链接 DLL。未测试、启动编辑器/游戏或跨对话协调，运行效果交由用户测试。

详情见[主报告第 30 节](../code-cleanup-20261116-report.md)及[第 20 批源码清单](batch-20-spec-rank/source-manifest.json)。

## 15. 原保留项实施状态（第 21 批）

用户最新授权将超长文件、疑似死代码和火球独立经验纳入清理。前面各节的“只检查/不动”是当时边界；本批在主报告第 31 节先写精确清单与完整函数拆分方案，再修改 Skills 源码，其他 46 个超长文件与 Skills 外实现保持原状。

- R01 已按方案拆为 ColdSteelSkillRules.cpp（定义，401 行）、ColdSteelSkillProgression.cpp（迁移/校验/成长，194 行）及 ColdSteelSkillCombat.cpp（快照/命中/归属，385 行）。函数体原样迁移，仅纠正迁移旧注释及归置 include；唯一静态序号、转发器与导出声明保留。
- R02 已按方案拆为 FPSQuickCombatComponent.cpp（生命周期/动作时钟，345 行）、QuickCombatPresentation.cpp（配置/表现，320 行）及 QuickCombatContact.cpp（命中，170 行）。同一组件的字段和反射声明不变，武器时钟、预测/权威和空手训练差异未合并。
- 火球在原位置复用 NotifyHit、AccumulateCriticalTraining 和从通用奖励尾段提取的 ApplyExperienceLevels。独立经验缩放、魂奖励、失败早退、元素箭及四项训练系数、提交后奖励登记仍归原拥有者；纳入清理不等于统一不同奖励语义。
- C04 仍保留。按已有符号链刷新，没有手写发起者，但 RPC 包装/注册与实际复制状态写入仍在，不能据此确认安全删除。未改 Skills 外源码，未扫描二进制资产或做运行审计。

共修改四个现有源码，新增四个承接完整函数的实现文件；无新增功能、状态框架、测试或运行验收。源码完成，必要 Editor 续编于 20:51:40–20:54:09 返回 Failed (OtherCompilationError)、退出码 6，耗时 148.76 秒；HillsBlacksmith.cpp:45–52 访问 BronzeTorch 受保护成员导致 C2248，未完成 DLL 链接。该错误在 Skills 外，本批未修改。具体等待、首次自有命令中断及续编记录见主报告与 build-receipt.json。H01/H02 状态处理、H03、R10–R12 等因行为或复杂度保留的项目不因解除三类范围限制而强行合并。

清单和结果见[主报告第 31 节](../code-cleanup-20261116-report.md)及[第 21 批源码清单](batch-21-retained-skills/source-manifest.json)。

### 第 21 批后续构建回执（22:26）

用户保存并关闭编辑器后，本批继续等待共享编译及剩余编译器进程退出，于 22:05:09–22:26:16 完成必要后台 Editor 续编调用。返回 Failed (OtherCompilationError)、退出码 6、UBT 耗时 1242.13 秒；150 个计划动作中记录 147 个编译动作（含失败），未完成 DLL 链接。本次没有新增源码修改。

原 HillsBlacksmith 访问错误本次未再出现；新阻塞位于 Skills 外的 TemperateHillsWorld.h、VillagePlantingDisplay.h、TemperateHillsLandscapeCapture.cpp、VillageDefenseDebris.cpp、VillageDefenseGate.cpp、VillageDefenseSection.cpp，具体编译位置及另 5 处首个头文件提示见主报告第 31 节续办结果。没有越界修改、手工修改生成文件、运行测试或重试未解决的同一构建。

源码清理完成、完整 Editor 构建受阻的交付边界保持不变；[本次构建回执](batch-21-retained-skills/build-resume-receipt-20261117.json)与此前失败记录同时保留。

### 第 21 批最终构建状态（22:36，已完成）

此前 Skills 外的阻塞对应修正已由工作区其他更新提供；本次没有新增源码修改。等待既有 Editor 构建及接续 Game 构建退出后，22:36:16–22:36:28 执行本批必要 Editor 收尾调用，返回 Succeeded、退出码 0，UBT 耗时 11.89 秒。目标已是最新，0 个编译/链接动作，没有把前序共享构建的链接记为本次执行。

第 21 批 C29–C31 源码和必要 Editor 构建收尾均完成；前述失败状态保留为历史。C04 及其他基于行为/复杂度的保留项不变。未加功能、未测试、未启动编辑器或游戏，运行效果由用户测试。见[最终构建回执](batch-21-retained-skills/build-resume2-receipt-20261117.json)。

## 16. 第 22 批：拆分后战斗模型读取

第 21 批拆分使 ColdSteelSkillCombat.cpp 成为可独立处理的战斗职责文件。本批按主报告第 32 节先列清单，再把 Snapshot、GrantBerserkOnWeaponHit、ApplyHit 三处相同的角色影子档案/GI 回退读取合并为本文件内的 SkillCombatModel(AActor*)。只修改该 cpp，385→391 行；保持每个入口的原调用位置和门槛，未新增公开 API、类型、成员状态或功能。

R13：既有 NetCast::AuthorityModel 额外处理 UnknownSpell，ColdSteelAuthority::ForPawn 另有 NPC/权威/本机控制分支，无法直接替换这三处。击杀奖励归属仍使用原 ForPawn；本批不把不同回退语义强行合并。C04、H01/H02 剩余状态处理、H03、R10–R12 及 Skills 外长文件继续按原范围与理由保留。

源码与必要后台 Editor 构建均已完成。等待已有后台 UE 进程退出后，23:49:52–23:50:24 构建返回 Succeeded、退出码 0，UBT 耗时 32.44 秒，4 个动作完成并重新链接 DLL。未运行测试或启动编辑器/游戏，运行效果由用户测试。见[第 22 批源码清单](batch-22-combat-model/source-manifest.json)、[构建回执](batch-22-combat-model/build-receipt.json)和[主报告第 32 节](../code-cleanup-20261116-report.md)。


## 17. 第 23–31 批统一收尾索引

后续“全部批次”授权已扩展到原报告其余模块；33 个额外长文件已按职责拆分，必要 Editor 构建最终 Succeeded、退出码 0，详情见[统一清理记录](all-batches-20261117.md)。本页 Skills 已完成结果保持；C04、H / R 保留项及火球独立倍率的最终理由集中在该记录第 31 批。未将这些保留项计作删除或行为统一，未测试。
