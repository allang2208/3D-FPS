---
name: ue5-skill-magic-workflow
description: 开发和迁移 FPSGAME 的主动、被动技能与魔法，贯通技能数据、修炼存档、快捷栏、动作占用、施法手势和 Niagara 特效。火球 V3 是已获用户认可的左手施法基线；手臂蒙皮细节转手臂技能，面板细节转冷钢 UI 技能。
---

# 本机维护源入口

弓专属技能的搭箭、持续费用、元素 CD、标记及队友表现，读取 [弓系准备技能](references/bow-prepared-skills.md)。

范围、连锁技能被栏杆或镂空障碍误挡时，读取[范围与连锁遮挡](references/area-skill-occlusion.md)。

本机共用流程统一读取[ue5-skill-magic-workflow](C:/Users/allan/.codex/skills/ue5-skill-magic-workflow/SKILL.md)，不要叠加旧镜像流程。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。

此入口依赖本机个人目录；跨机器交付需另行导出所需维护源和引用。

- 雷暴领域当前法杖门槛、等级范围、室内落雷与密云作者见 [领域落雷与蓄力贯穿](references/electric-magic-migration.md) 顶部2026-10-12规则；覆盖旧的空手释放说明。

## 上挑强制击飞

上挑（2026-10-15）：双手剑／双手锤共用 `ColdSteelSkillModel::ApplySkillWeaponHit`，伤害与削韧结算后对 `swordUppercut` 调用 `ReceiveForcedLaunch`。普通怪物直接可击飞；有韧性条的精英、领主和首领仅 `Broken` 阶段可击飞，当次破韧立即生效。不要在武器局部命中重复追加普通推退。说明同步技能数据与详情页；工程记录 `Docs/Skills/uppercut-forced-launch-20261015.md`，未实机测试。

## 魔法书专注与施法快照

- 法杖＋副手书的施法加速、减耗、受击扣魔及影子档案事务，读取[副手魔法书](../ue5-weapon-workflow/references/spellbook-focus-and-publication.md)。派生电系法术只应用一次专注；客户端反应与服务器扣魔通过轮次和累计记录衔接。

## 持续魔法联机

暴风雪自 2026-10-14 起是必须当前装备法杖的高级魔法；施法门槛、切杖退蓝及快捷槽提示读取 [暴风雪迁移](references/blizzard-migration.md) 顶部规则，覆盖历史“无需法杖”。

龙息、雷暴领域和暴风雪的施法编号、预测回执、异步表现、奖励档案及离场结算，读取 [持续魔法的联机状态与收尾](references/persistent-magic-network.md)。

## 已学技能进入预载（2026-10-15）

新增或替换战技／魔法运行资产时，同步维护 `Source/FPSGAME/Skills/PlayerSkillAssets.cpp` 的资源入口（暴风雪复用原路径表）。进入准备顺序为存档与场景就绪、已学战技、已学魔法、释放输入；同类按 `SkillCatalog()`，不按快捷槽筛选。`FPlayerSkillPreparation` 顺序异步加载并保留句柄，轮询 Niagara 编译／渲染可用状态，不实际施法。保留快速进入、换图、取消重试与客户端路径。制作记录见 `Docs/Skills/learned-skill-entry-preparation-20261015.md`；未实机测试，不能宣称所有首次施法卡顿已消除。

### 进入预载等待陷阱（2026-10-15 用户实测）

技能队列曾卡在冰锥引用的世界级附加 `NS_IceImpactMist`，包加载已经完成但 `IsReadyToRun()` 一直为 false。它原本由 `UFluidPresentationSubsystem` 在世界开始时异步加载和建池，不应重复作为所有技能进入的硬门槛。大旋风前景替换表也只能按随身武器、握柄和部件实际引用筛选，不能整张预载。已就绪资源按小时间预算批量推进，避免“每帧一个”叠加编辑器后台 3 FPS 的人为等待；新编译/PSO 请求仍让出当帧。详情与用户重试日志见工程 `Docs/Skills/learned-skill-entry-preparation-20261015.md`。

### 当前方案覆盖：进入后后台加载（2026-10-15）

用户因继续卡在 94% / 冰锥而要求回退。撤销此前“技能全部准备好才进入”的门槛；场景完成即恢复操作，加载遮罩淡出后由 TransitLoadingSubsystem 顺序推进已学战技、魔法。每次一个异步资源请求，保留引用/去重，取消换图安全，结束停止额外 Tick。不得再用 Niagara IsReadyToRun、材质 ShaderMap 或 PSO/强制编译作为进场条件；单项失败只记日志并继续。以上覆盖本技能此前的进入预载放行条款；记录仍见 Docs/Skills/learned-skill-entry-preparation-20261015.md。默认不自动测试。


### 全已学技能的后台准备补全（2026-10-15）

用户进一步要求排查其他战技/魔法的首用加载。继续先放行场景，再按目录顺序准备已学战技、魔法；当前实现允许在后台逐资产进行非强制 Niagara 编译、PSO、隐藏预备实例、音效 Prime 和组件绑定，每帧一个新操作、等待有上限，绝不作为进入条件。玩家技能 BeginPlay 使用 PlayerSkillAssets::Defer 注册资源回调，由同一队列接入；新增/覆写软引用同时列入 Gather/ExtraPaths。新学技能自动追加，普通属性变化不复制全背包或重复预载。龙息复用自己的实际流体实例，战锤分帧预建实际撞击池；普通 Niagara 使用隐藏代表实例提前准备共享脚本/管线，不宣称每次施法的组件分配都消失。参见 Docs/Skills/learned-skill-background-audit-20261015.md 与 PlayerSkillRenderPreparation.*。该规则覆盖旧的“后台队列完全不做渲染准备”；进场非阻塞规则不变。

### 冷资源的待提交编译不能当作已在编译（2026-10-15）

龙息用户实测持续“火焰准备中”，原因是 UE 5.8 的 `HasOutstandingCompilationRequests(true)` 包含 `NeedsRequestCompile()`；不能因此只执行 `PollForCompilationComplete(false)`，否则请求从未真正提交。技能后台准备改用 `PollForCompilationComplete(true)`，只提交待处理的非强制请求，并按帧轮询，不能改成运行时 `WaitForCompilationComplete` 或进场等待。适用于龙息拥有者实例和通用技能渲染准备；后台顺序、逐项超时与场景放行保持。直接证据及会话接入记录见工程 `Docs/Skills/dragon-first-cast-preparation-20261015.md` 顶部。本次不更改 R6 火焰外观。

### 首次火焰必须包含实际绘制材质准备（2026-10-15 实测）

重新进入游戏的真实画面曾出现：Niagara/GPU 实例已就绪且扣蓝正常，但首次火焰仍缺失。龙息预热使用可参与渲染的组件，同时将 Strength 置零，使发光、密度和温度消光均不可见；按帧等待实际 MI/MID 对应的 ShaderMap、编译与 PSO 可用，再暂停隐藏驻留。不能只看系统实例，也不能拿未使用的基材 ShaderMap 当作实例材质状态。准备不得加入进场放行条件或同步等待。R6 外观与玩法保持；本轮验证源和截图见 `Docs/Skills/dragon-first-cast-regression-20261015.md`。

- [坚冰铠甲表现与联机](references/ice-armor-presentation.md)：2026-10-18 本轮实现经验与恢复边界，按问题读取；不授权自动测试。

## 地面魔法的范围合同

陨星准备卡住、范围预览拖动、斜坡判定、起手锁点及提前销毁结算，读取 [地面魔法的预览、范围与锁点](references/meteor-ground-contract.md)。

装备近战体力／施法法力减耗、强化与聚能叠加，读取 [资源费用乘区与最低费用](../ue5-item-asset-workflow/references/resource-cost-multipliers.md)；同件加法、跨件乘法，最终保留正基础费用的 20%，执行与预览共用。
