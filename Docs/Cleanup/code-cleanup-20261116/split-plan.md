# 超过 800 行文件的拆分方案

日期：2026-11-16。共 48 项；本轮不修改这些文件。尺寸见读取时快照，候选责任基于路径、声明或局部入口，实施前仍需在对应模块内确认完整调用边界。

## 实施约束

1. 每批只处理一个三级职责；先复用现有职责文件，避免同义重复实现。
2. 方法移动保留原类、签名和行为；纯 helper 迁移需注意匿名命名空间、内部链接和 include 依赖。
3. 反射头文件先设计类型归属，不靠把成员机械塞进 include 片段绕过 800 行。
4. 生成数据先改作者输出策略，保持逐项数值、骨序和时钟；不能把动作轨道当死代码删减。
5. 需要实施时完成相应必要后台构建；本轮仅方案，无构建和运行测试。

## 逐项方案

所有路径相对于 `D:/FPS3D/FPSGAME`。建议实现单元以 600 行左右为目标，仍以自然职责和 800 行边界为准。

| 文件 | 行数 | 字节 | 职责与拆分建议 | 必须保留 |
| --- | ---: | ---: | --- | --- |
| `Source/FPSGAME/Building/VoxelBuildComponent.cpp` | 1,873 | 114,935 | 建造事务：放置查询与对齐 / 资源提交 / 拆除交互分别移至既有或新职责 cpp | 承重、库存扣费与回执顺序 |
| `Source/FPSGAME/Building/VoxelBuildWidget.cpp` | 928 | 54,637 | 建造面板：布局构造 / 构件列表数据 / 输入交互 | 原样式、选择状态和建造命令 |
| `Source/FPSGAME/Building/VoxelBuildWorld.cpp` | 861 | 52,709 | 建造世界：实例登记 / 空间查询 / 保存恢复 | 构件身份、持久化键和碰撞语义 |
| `Source/FPSGAME/Characters/FPSBodyKukriPresentationData.h` | 985 | 85,748 | 动作采样数据：定位作者生成器与采样消费者；分离类型/时间轴/采样入口，将骨段或时间块数据输出为约 2 个小于 800 行的数据单元（数量仅按当前行数估算） | 原精度、骨序、插值与动作长度；正式作者源和有效旧版依赖 |
| `Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp` | 2,671 | 187,911 | 身体动画：状态采样 / 移动姿态 / 武器上身 / IK 接触分别归入职责实现 | 动画 Tick 顺序、骨序和接触时钟 |
| `Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp` | 1,131 | 74,693 | 身体装备：装备解析 / 网格生命周期 / 显隐与外观应用 | 异步就绪、装备身份和原生绑定 |
| `Source/FPSGAME/Characters/FPSPlayerBodyMotion.cpp` | 859 | 55,417 | 身体运动表现：移动步态 / 动作混合 / 过渡采样 | 原时间域和本机远端分支 |
| `Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.cpp` | 2,280 | 143,881 | 地牢布局：布局搜索 / 连接合法性 / 清单序列化；先隔离纯算法 helper | 随机种子、搜索顺序及超时布局回执 |
| `Source/FPSGAME/Dungeons/DungeonRunSubsystem.cpp` | 854 | 41,515 | 地牢流程：区域进度 / 奖励与退出 / 持久化生命周期 | 任务 ID、团队和个人返程边界 |
| `Source/FPSGAME/Dungeons/FacilityHallEncounter.cpp` | 847 | 46,370 | 大厅遭遇：生成调度 / 精英目标 / 激活与结束 | 槽位身份、异步准备和真实击杀开门 |
| `Source/FPSGAME/FPSGAMECharacter.cpp` | 4,830 | 309,244 | 角色门面：保留构造与生命周期；优先利用已有 CharacterAmmo/Reload/Profile/ActionPriority 文件，剩余按输入绑定、装备切换、交互路由分开 | 现有成员签名、组件创建顺序和动作占用 |
| `Source/FPSGAME/FPSGAMECharacter.h` | 1,043 | 61,177 | 角色公开合同：先缩减可前置声明 include；区分反射成员、输入门面和私有纯状态，提出独立状态类型后再逐项迁出 | UCLASS、UPROPERTY、RPC、generated.h 与已有 Blueprint 路径 |
| `Source/FPSGAME/Monsters/BlindSupplicantAuthoring.cpp` | 1,127 | 64,966 | 怪物作者工具：资产装配 / 材质和表现配置 / 保存步骤 | 已有资产路径与制作顺序 |
| `Source/FPSGAME/Monsters/UnknownHumanoidTactics.cpp` | 843 | 43,397 | 人形战术：目标评估 / 近远程选择 / 移动掩体决策 | 战斗状态机、随机选择和权威归属 |
| `Source/FPSGAME/Monsters/WildlifeAnimal.cpp` | 1,023 | 41,483 | 环境动物：移动行为 / 受击死亡 / 掉落与复制表现 | 状态快照、尸体和待提交掉落 |
| `Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp` | 2,730 | 168,162 | 玩家权威门面：档案传输优先复用 ColdSteelProfileTransfer；命中、施法、生命周期定义分开并复用现有各武器 Authority 文件 | RPC 名称、序号、反作弊与事务提交顺序 |
| `Source/FPSGAME/Multiplayer/ColdSteelPlayerState.h` | 822 | 47,101 | 权威反射合同：协议值类型和非反射缓存先提取；RPC/UPROPERTY 声明暂留原类，再按引用设计私有状态分组 | 网络序列化、反射布局和旧存档 |
| `Source/FPSGAME/Production/ProductionToolComponent.cpp` | 940 | 58,670 | 生产工具门面：装备准备 / 输入与状态 / 外观资源；复用 ProductionToolMotion 等现有实现 | 工具/近战共用占用、支付和武器身份 |
| `Source/FPSGAME/Skills/ColdSteelSkillRules.cpp` | 973 | 82,301 | 第 21 批已实施：原文件保留 LoadDefinition（401 行）；迁移/校验/成长/摘要移至 ColdSteelSkillProgression.cpp（194 行）；快照/弱点/命中/归属移至 ColdSteelSkillCombat.cpp（385 行） | 声明与导出、旧档版本分支、唯一静态序号/转发器、影子档案归属、既有缓存所有权；详见本页补充链接 |
| `Source/FPSGAME/Skills/FPSQuickCombatComponent.cpp` | 813 | 42,143 | 第 21 批已实施：原文件留生命周期/动作时钟（345 行）；Configure 与镜头/表现读取移至 QuickCombatPresentation.cpp（320 行）；ContactHit 移至 QuickCombatContact.cpp（170 行） | 原组件与字段、武器专属时钟、接触预测/权威结算、现有 WarhammerQuickCombat.cpp 职责；详见本页补充链接 |
| `Source/FPSGAME/UI/ColdSteelCodexPage.cpp` | 1,569 | 84,138 | 图鉴页面：布局 / 条目数据 / 详情交互 | 可见数据范围和输入状态 |
| `Source/FPSGAME/UI/ColdSteelHUDWidget.cpp` | 1,739 | 98,520 | HUD 门面：构造绑定 / 任务与导航 / 战斗状态刷新；优先复用现有 HUD 职责文件 | 现有有界刷新、输入和生命周期 |
| `Source/FPSGAME/UI/ColdSteelInventoryRules.cpp` | 824 | 52,711 | 库存规则：占格约束 / 移动与叠放 / 装备资格 | 实例身份、旋转占格和事务一致性 |
| `Source/FPSGAME/UI/ColdSteelItemTooltipData.cpp` | 858 | 75,156 | 物品浮窗数据：属性格式 / 装备机制 / 套装与来源说明 | 现有公式、百分比口径和属性分组 |
| `Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp` | 1,700 | 116,986 | 档案运行时：档案生命周期 / 属性变更 / 奖励提交；先拆再与法术结算去重 | 旧档版本、原子提交和奖励去重 |
| `Source/FPSGAME/UI/ColdSteelSkillPage.cpp` | 1,492 | 158,875 | 技能页面：树布局 / 选择详情 / 习得与快捷槽交互 | 稳定技能 ID、前置提示和输入焦点 |
| `Source/FPSGAME/UI/ColdSteelSmeltingWidget.cpp` | 1,278 | 87,429 | 冶炼页面：布局 / 配方队列视图 / 订单回执 | 权威订单和原材料事务 |
| `Source/FPSGAME/UI/ColdSteelWorkbenchWidget.cpp` | 940 | 62,085 | 工作台界面：布局 / 配件展示 / 交互与导航状态 | 实际实例、预览就绪和改造记忆 |
| `Source/FPSGAME/UI/TransitLoadingSubsystem.cpp` | 1,167 | 63,395 | 入场与后台准备：加载遮罩 / 地图准备 / 技能后台调度 / 取消清理 | 场景放行时点、快速进入与换图取消 |
| `Source/FPSGAME/Weapons/Bow/BowWeaponComponent.cpp` | 2,078 | 108,630 | 弓门面：搭箭拉弦 / 发射结算 / 装备与表现；先核对现有 Bow 子模块 | 拉弦会话、箭矢实例与远端时钟 |
| `Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp` | 1,747 | 100,475 | 枪械表现：枪口与弹道 / 命中与退壳 / 声音及资源持有 | 本机远端区分、效果池与音画时钟 |
| `Source/FPSGAME/Weapons/Kukri/KukriWeaponComponent.cpp` | 1,194 | 70,753 | 弯刀门面：动作阶段 / 主副手选择 / 攻击与装备呈现 | 双刀身份、接触时点及互斥规则 |
| `Source/FPSGAME/Weapons/PistolDualWieldComponent.cpp` | 990 | 56,595 | 双持手枪：左右手调度 / 弹药换弹 / 呈现同步 | 两手独立实例和共享弹池 |
| `Source/FPSGAME/Weapons/RuneSwordAzureDragon.cpp` | 1,029 | 63,765 | 苍龙武器机制：激活状态 / 数值结算 / 远端表现 | 权威增益窗口和每次攻击去重 |
| `Source/FPSGAME/Weapons/RuneSwordComponent.cpp` | 1,999 | 117,665 | 符文剑门面：装备生命周期 / 攻击阶段 / 命中与权威路由；复用 Guard/Uppercut 等现有职责文件 | 原攻击时钟、手别、费用和客户端请求 |
| `Source/FPSGAME/Weapons/Spellbook/SpellbookAuthoredFocus.h` | 14,049 | 1,104,006 | 动作采样数据：定位作者生成器与采样消费者；分离类型/时间轴/采样入口，将骨段或时间块数据输出为约 24 个小于 800 行的数据单元（数量仅按当前行数估算） | 原精度、骨序、插值与动作长度；正式作者源和有效旧版依赖 |
| `Source/FPSGAME/Weapons/Spellbook/SpellbookAuthoredGrip.h` | 1,918 | 210,747 | 动作采样数据：定位作者生成器与采样消费者；分离类型/时间轴/采样入口，将骨段或时间块数据输出为约 4 个小于 800 行的数据单元（数量仅按当前行数估算） | 原精度、骨序、插值与动作长度；正式作者源和有效旧版依赖 |
| `Source/FPSGAME/Weapons/Spellbook/SpellbookAuthoredStrike.h` | 1,666 | 183,660 | 动作采样数据：定位作者生成器与采样消费者；分离类型/时间轴/采样入口，将骨段或时间块数据输出为约 3 个小于 800 行的数据单元（数量仅按当前行数估算） | 原精度、骨序、插值与动作长度；正式作者源和有效旧版依赖 |
| `Source/FPSGAME/Weapons/Staff/StaffAuthoredCastElbow20260930.h` | 1,369 | 177,792 | 动作采样数据：定位作者生成器与采样消费者；分离类型/时间轴/采样入口，将骨段或时间块数据输出为约 3 个小于 800 行的数据单元（数量仅按当前行数估算） | 原精度、骨序、插值与动作长度；正式作者源和有效旧版依赖 |
| `Source/FPSGAME/Weapons/Staff/StaffAuthoredLeftGaitV16.h` | 1,898 | 199,665 | 动作采样数据：定位作者生成器与采样消费者；分离类型/时间轴/采样入口，将骨段或时间块数据输出为约 4 个小于 800 行的数据单元（数量仅按当前行数估算） | 原精度、骨序、插值与动作长度；正式作者源和有效旧版依赖 |
| `Source/FPSGAME/Weapons/Staff/StaffAuthoredPoseV13.h` | 1,369 | 177,752 | 动作采样数据：定位作者生成器与采样消费者；分离类型/时间轴/采样入口，将骨段或时间块数据输出为约 3 个小于 800 行的数据单元（数量仅按当前行数估算） | 原精度、骨序、插值与动作长度；正式作者源和有效旧版依赖 |
| `Source/FPSGAME/Weapons/Staff/StaffAuthoredPrimaryV28.h` | 1,137 | 147,747 | 动作采样数据：定位作者生成器与采样消费者；分离类型/时间轴/采样入口，将骨段或时间块数据输出为约 2 个小于 800 行的数据单元（数量仅按当前行数估算） | 原精度、骨序、插值与动作长度；正式作者源和有效旧版依赖 |
| `Source/FPSGAME/Weapons/Staff/StaffAuthoredReleaseAnatomy20261001.h` | 1,411 | 182,144 | 动作采样数据：定位作者生成器与采样消费者；分离类型/时间轴/采样入口，将骨段或时间块数据输出为约 3 个小于 800 行的数据单元（数量仅按当前行数估算） | 原精度、骨序、插值与动作长度；正式作者源和有效旧版依赖 |
| `Source/FPSGAME/Weapons/Unarmed/UnarmedAuthoredLocomotion20261001.h` | 3,852 | 415,861 | 动作采样数据：定位作者生成器与采样消费者；分离类型/时间轴/采样入口，将骨段或时间块数据输出为约 7 个小于 800 行的数据单元（数量仅按当前行数估算） | 原精度、骨序、插值与动作长度；正式作者源和有效旧版依赖 |
| `Source/FPSGAME/Weapons/Unarmed/UnarmedAuthoredPunch20261002.h` | 999 | 103,189 | 动作采样数据：定位作者生成器与采样消费者；分离类型/时间轴/采样入口，将骨段或时间块数据输出为约 2 个小于 800 行的数据单元（数量仅按当前行数估算） | 原精度、骨序、插值与动作长度；正式作者源和有效旧版依赖 |
| `Source/FPSGAME/WorldGeneration/GrassDeform/GrassDeformSubsystem.cpp` | 1,047 | 52,504 | 植被形变：影响源收集 / 空间筛选 / 实例提交与释放 | 有界预算、材质参数与组件存活 |
| `Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp` | 1,720 | 94,674 | 丘陵流送：邻域需求 / 资源准备 / 提交与释放 | 出生碰撞、分帧预算和取消边界 |
| `Source/FPSGAME/WorldGeneration/TemperateHillsWorld.cpp` | 1,040 | 58,031 | 丘陵世界：生成入口 / 天气生态设置 / 世界生命周期 | 种子、运行时高度场和资产路径 |

## 建议次序

- 首批：Character、PlayerState、ProfileRuntime 的门面职责设计；先处理反射/存档/联机边界，再移动实现。
- 第二批：UI 页面、世界流送和具体武器执行器，按模块逐批实施。
- 独立数据批：Spellbook、Staff、Unarmed 及身体动作数据；先定位作者脚本，不与玩法重构合并。

SpellbookAuthoredFocus.h 开头标注 `Focus/IntegratedV30/author_motion.py`；尚未核定该作者脚本的当前实际路径。因此这项保留“先定位作者源”的前置条件，不能宣称生成器拆分已经可直接执行。

## 2026-11-17：仅细化本批两个 Skills 文件

用户选择只检查 Skills 保留项及 C04 调用链。本次重新读取上述两文件的行数、职责入口及相关调用，补充了方法级拆分方案；其他 46 项继续保持 2026-11-16 的初始方案和快照，不表示已重新检查。

完整方法归属、预计尺寸、依赖与保留理由见 [Skills 保留项定向检查第 3、4 节](remaining-skills-review-20261117.md)。所有新文件名均为建议；本次未创建这些源码文件，未迁移方法、删除兼容分支或修改超长文件。

## 2026-11-17：第 21 批实施授权与清单

用户随后明确将超长文件纳入清理；上述“本轮仅方案”描述保留为初始盘点和定向检查阶段历史。现仅实施表中两个 Skills 文件，方法边界、精确文件清单及保持行为的约束已在[主报告第 31 节](../code-cleanup-20261116-report.md)先行写明：规则按定义/进度/战斗拆分，快速近战按时钟/表现/命中拆分。其他 46 项不在本次源码修改范围。源码完成后补充实际行数与必要后台构建结果；不运行测试。

第 21 批源码拆分已落盘：规则为 ColdSteelSkillRules.cpp 401 行 / ColdSteelSkillProgression.cpp 194 行 / ColdSteelSkillCombat.cpp 385 行；快速近战为 FPSQuickCombatComponent.cpp 345 行 / QuickCombatPresentation.cpp 320 行 / QuickCombatContact.cpp 170 行。表中原行数/字节仍保留为拆分前快照；声明和成员归属未改。必要后台 Editor 续编返回 Failed (OtherCompilationError)、退出码 6，因 Skills 外 HillsBlacksmith.cpp 的 C2248 访问错误未完成链接；源码拆分已完成，构建仍受外部错误阻塞，未测试。

第 21 批后续构建状态更新（2026-11-17 22:26）：等待用户关闭编辑器及共享构建退出后，22:05:09–22:26:16 的 Editor 续编返回 Failed (OtherCompilationError)、退出码 6，耗时 1242.13 秒。原 HillsBlacksmith 访问错误本次未再出现；最新阻塞为其他地编头文件、生成头及类型/复制声明错误，详见主报告第 31 节续办结果。两个 Skills 文件的拆分源码状态不变，本次未再修改源码、未完成 DLL 链接、未测试。

第 21 批最终构建状态（2026-11-17 22:36，已完成）：等待共享 Editor/Game 构建退出后，22:36:16–22:36:28 的独立 Editor 收尾返回 Succeeded、退出码 0，目标已是最新，0 个编译/链接动作，UBT 耗时 11.89 秒。两个 Skills 超长文件的拆分源码及必要构建现均完成；前文失败回执保留为历史。此次未再修改源码、未测试、未启动编辑器/游戏。


## 2026-11-18：第 23–31 批逐项处理

原 48 项现均有明确实施或保留结论：本轮新增拆分 33 项，加上第 21 批共 35 项；其余 13 项按本轮“不改变行为、不增加复杂度”标准保留。原表行数与字节是初始快照；本轮实际起始状态、职责拆分、当前尺寸和保留原因以[统一清理记录](all-batches-20261117.md)及[manifest.json](all-batches-20261117/manifest.json)为准，不能继续按原表当作待实施清单。

Spellbook Focus 作者脚本已定位为 `SourceAssets/SpellbookEvildeer20261009/Focus/IntegratedV30/author_motion.py`。原方案按行数估算分成若干数据单元的建议已撤销：连续姿态数组保持其生成/索引合同，10 个数据头明确保留；有自然角色分组的 FPSBodyKukriPresentationData 已按 Jason / Kaitlin 分开，并同步原作者输出脚本。没有重采样、运行作者脚本或测试。

Character 反射头、BodyAnimInstance 的工作线程动画流程和 AuthoredDungeonGenerator 的装配流程分别按其实际耦合边界保留，不通过行号碎片或新增状态框架压行数。必要 Editor 构建现已成功，退出码 0，4 个动作完成并重新链接 DLL；最终回执及失败历史见统一清理记录。未测试。
