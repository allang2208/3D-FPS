# 采集工具的装备、低伤害战斗与命中查询

用于伐木斧、矿镐同时承担采集和自卫的接入。动作与冲击节奏见 [双手工具动画](../../ue5-fps-arms-animation/references/two-handed-tools.md)。保持原有采集奖励、身份与存档位置；树木自 2026-09-25 起按生命值结算（见下文「进度口径」与 [树木生命值](../../../Docs/ProductionTreeHealth-20260925.md)）。

## 装备链要闭合

- 斧、镐由主手装备槽提供当前工具，按双手规则占用同组副手；右键装备、拖放、卸下、武器组切换共用已有装备事务。
- 移除直接从背包临时调出的快捷键时，也要清除旧存档里的临时工具覆盖，否则仅删按键仍可绕过装备条件。
- 将它们纳入近战物品识别，但不要因此赋予剑类连击、格挡、强化或精通伤害。铁铲的临时工具入口保持独立。
- 图标方向与格子占用分别处理：矿镐竖直图标仍为 2×3，伐木斧为 1×3。旧存档保留玩家显式旋转、物品 ID 与格子位置；归一化只刷新相应定义字段。

## 数值使用工具自己的快照

在扣除体力的事务完成后，重新取得当前工具并捕获攻击快照；不能借用之前收起武器的基础伤害或附魔。基础公式、物品提示和实战调用走同一武器公式/防御链。

2026-09-20 当前参数：伐木斧 `round(12 + 1.2×力量 + 0.3×敏捷)`，矿镐 `round(10 + 1.0×力量 + 0.2×敏捷)`。角色暴击和目标防御照常结算，排除工具的武器精通固定加伤。参数属于本项目低伤害自卫定位，不是通用平衡标准。

2026-09-25 更新：**树木改吃生命值**，这份自卫伤害就是伐木伤害（见下文「采集与自卫分开结算」与
[树木生命值](../../../Docs/ProductionTreeHealth-20260925.md)）；矿镐对岩块仍是命中数口径，采矿次数不随伤害变化。

## 命中范围与遮挡

- 准星中心射线的有效接触优先；辅助球扫用于增加宽度，而不是把球形前端算作额外攻击距离。
- 对敌和采集分别设置距离/半径。当前对敌 180 cm；伐木表面距离 320 cm、辅助半径 32 cm；矿镐采矿保留 320 cm 中心射线，对敌另有 20 cm 辅助半径。
- 从稳定眼位与控制朝向取查询，镜头冲击不能改变采集瞄准。候选点投影必须在前方，表面距离不超过对应上限，最后做可见性遮挡查询。
- 地形、多个树干可能共用同一 Actor。确认资源遮挡与目标一致时比较组件和实例索引，不能只比较 Actor；怪物则按 Actor 归属识别。
- 初始重叠没有可信表面点，需向目标补查真实表面；不要用玩家眼位充当接触点。
- 单次攻击只结算一个目标。敌人走伤害确认，资源走采集提交；两者共用确认命中的动作和镜头反馈，但敌人不扣采集次数、不产材料或播放木屑效果。友方、玩家和尸体不作为该自卫攻击的有效目标。

当前入口为 `ProductionAxeContact.cpp`（函数名保留 Axe，但服务斧、镐两者）、`ProductionToolComponent.cpp`、`ColdSteelProductionTools.cpp`、`ColdSteelProfileRuntime.cpp` 和 `production_tools.json`。发布时把调用者的镜头接入、装备交互、公式和源动画恢复说明一起提交，避免只提交工具组件。

## 改造系统：四栏数值改造（2026-09-24）

伐木斧与矿镐已接入改造系统，沿用 [模块化近战](modular-melee.md) 的「栏目 ≠ 网格」分工，但**栏目与数值口径独立**，不共用剑类倍率字段。本次接入的制作与检查记录见 [采集工具改造系统](../../../Docs/Weapons/tool-modification-20260924.md)。

- 目录 `Content/ColdSteelData/tool-gunsmith.json`，四栏＝握把 `grip`、握柄 `shaft`、改件 `fitting`、主部件 `head`。加载器 `Weapons/ToolGunsmith.cpp` 写进 `UGunsmithSystem::ToolWeapons`，与剑类 `MeleeWeapons`、枪械 `Weapons` 并列；`ModifiableWeapon` 是三者共同入口，因此背包「改造武器」按钮、J 键与工作台自动覆盖工具，不需要另开一条 UI 路径。
- 存档仍写物品 Data 的 `gunsmith_parts`，槽位键就是栏目键。旧存档没有工具改造字段时按 factory 结算，不需要迁移；`NormalizeProductionState` 只刷新定义字段，不会覆盖 `gunsmith_parts`。
- 数值口径：倍率相乘、绝对值相加。唯一评估入口是 `Production/ProductionToolStats.h::ColdSteelTool::Evaluate`（自卫伤害面板、挥砍节奏、体力、采集距离与宽容半径、产出倍率、所需命中、额外产出几率、暴击与削韧）。**采集链、自卫链、物品浮窗、工作台总览、图鉴都读这一份结果**，不允许任何一处二次换算。
- 铁铲没有目录条目：`Evaluate` 对它返回出厂倍率，行为与改造前一致。不要把铁铲塞进工具目录，除非同时补齐视模与作者动画。

### 采集与自卫分开结算

| 改造项 | 作用链 | 边界与坑 |
| --- | --- | --- |
| `harvest_yield_mult` | 采尽结算时乘在出厂奖励数量上（木材按根散落，石材／矿石仍是一个堆叠拾取物） | 四舍五入，最少 1 |
| `harvest_hits_add` | 岩块：所需有效命中 ＝ 出厂 3 次 ＋ 加值。树木：折算成**伐木伤害倍率**（出厂 3 挥 → 2 挥 ＝ ×1.5），标定伤害下挥砍数仍是「3 ＋ 加值」 | 运行时夹在 ≥1 次；**目录层面命中减免只允许一个来源**，全栏最省仍是 2 次（保留采集节奏），离线自检把这条锁成断言。采尽时把存档进度**补到出厂次数**，否则 `IsProductionDepleted` 与 PCG 补生会认为资源没采完 |
| `harvest_reach_mult`／`harvest_radius_add_cm` | 采集射线距离与辅助球半径 | 矿镐出厂半径 0（只认中心射线），所以辅助宽度必须用**绝对加值**，倍率对它是空操作 |
| `bonus_harvest_chance` | 采尽结算判定一次，成功则整份材料再落一次 | 期望产出 ＝ 产出倍率 ×（1＋几率）；落点沿用同一条随机流，不会重叠 |
| `damage_mult`／`toughness_damage_mult`／`crit_chance_add` | 自卫命中：`damage_mult` 走 `ProcessedDamage` 的 `MeleeDamageMultiplier` 通道，削韧与暴击随 `FColdSteelSkillShot` 进 `ColdSteelSkills::ApplyHit` | 不给连击、重击、格挡与精通口径。**不要**加工具版 `hit_reaction_mult`：受击倍率用 `TGuardValue` 设值而非相乘，内层默认 1 会覆盖外层 |
| `attack_speed_mult` | 只压缩真实时钟（`RateScale`） | 动画与镜头关键帧是**作者秒**：必须传 `AuthoredElapsed = Elapsed × RateScale` 给采样器，真实阈值除以 `RateScale`；`RateScale=1` 时逐帧等价 |
| `stamina_mult` | 每次挥动的采集体力，采集与自卫共用同一笔 | `ColdSteelMelee::AttackStamina` 对工具走 `HarvestCost`，不是近战 15 点，否则 HUD 的可用次数会算错 |

### 进度口径：出厂判定采尽，改造判定完成

`CommitHarvestStrike` 里两个判断不能混用同一份次数（岩块与表土）：

- 「此处资源已经采尽」按**出厂**所需命中（`FProductionResource::HitsNeeded()`）判断。存档里的进度是历史累计命中，可能是用出厂工具打出来的；若按改造后的次数判定，出厂打到 2 次的资源会在换上减命中改造后被判为采尽而**不发奖励**。
- 完成判定用 `After >= Needed`（不是 `==`）：换上减命中改造后历史进度可能已越过新的所需次数，这一挥仍要正常结算，否则资源卡在「差一次」的中间态。
- 采尽后写入 `max(After, 出厂次数)`，因此拆掉改造也不会把已采尽的资源「复活」。

树木不走这条路（2026-09-25 起）：`CommitHarvestStrike` 在 `Layer==0 && MaxHealth>0` 时分流到
`CommitTreeStrike`，按生命值扣血、归零才倒；生命进度存 `TreeHealth`（比例），采尽仍补写命中数与
`TreeGrowth`，两条口径的存档字段互不覆盖。

### 工作台、浮窗与自检

- 工作台复用近战那套结构（`IsStandaloneWorkbench()` ＝ 近战或工具），预览用 `tool_mesh` 建独立静态网格组件并沿用正交取景；**不要**扩 `ColdSteelMeleePreview::Supports`——它同时服务背包图标渲染，扩了会把工具塞进图标链路。
- 栏目标签、选项卡片、详情行与浮窗合计的行名必须与目录 `effects` 逐字一致。`Tools/Production/check_tool_modification_consistency.py` 离线断言这一点，并核对 stats 键与 C++ 加载器逐字对齐、description 不含可推导数字、benefit 方向、命中下限与 `production_tools.json` 字段齐全。
- 当前四栏是**数值改造**，沿用原装外形；实体模块拆分后按同一改造 ID 接入（见 [模块化近战](modular-melee.md) 第 1 节），目录的 `appearance` 字段负责如实说明外观归属，浮窗与详情面板照抄它。
- 新增入口：`Weapons/ToolGunsmith.cpp`、`Production/ProductionToolStats.{h,cpp}`、`Production/ProductionTreeHealth.{h,cpp}`、`UI/M4ToolGunsmith.cpp`；改动入口：`GunsmithSystem.{h,cpp}`、`ProductionToolComponent.{h,cpp}`、`ProductionToolMotion.cpp`、`ProductionAxeLocomotion.cpp`、`ColdSteelProductionTools.cpp`、`ColdSteelProductionDrops.cpp`、`Production/ProductionResource.h`、`WorldGeneration/TemperateHillsProduction.cpp`、`M4Gunsmith*`、`SMeleePartIcon.h`、`ColdSteelItemTooltip{Data,Summary,Formula}.cpp`、`ColdSteelCodexPage.cpp`。

### 强化系统（金属材质档位，外观）

工具强化与上面的四栏**数值改造**是两套东西：它只换金属部位材质槽的材质实例，不改数值、不改网格，独立字段 `tool_enhance_level`（1…5，缺省 1，逐级 +1、不可降级、不可跳级）。设计与阶段划分见 [采集工具强化系统设计](../../../Docs/Weapons/tool-enhancement-design-20260925.md)（**第 10 节是阶段 1 实施记录**，含已落地文件、构建结果与"材质未制作时的三层降级"；**第 11 节是阶段 2 资产实施记录**）；栏目细化见 [强化栏规划](../../../Docs/UI/tool-enhancement-column-plan-20260925.md)。离线自检 `Tools/Production/check_tool_enhancement_consistency.py`（与 `check_tool_modification_consistency.py` 并列，互不覆盖）。**本条目只作指针，细节以那两份文档为准。**

阶段 2 资产管线的可复用结论（2026-09-25，全部 headless 完成）：

- 拆槽 v1 曾用纯 Z 切面心（斧 0.195、镐 0.315），**被用户否决**：吞了镐前端绳缠与木帽。v2 语义规则：镐＝连通域（metallic_mean≥0.15 且 chroma_mean≤0.16 且 z_min≥0.33）；斧＝逐面（z≥0.195 且 chroma<0.20 或 metallic>0.2）；视模用 `(WPN_root_rest⁻¹·v).z + grip_z` 还原世界 z 后套同一规则。动手前先跑连通域＋UV 采样 metallic/chroma 分带分析（`analyze_resplit.py` 模式）。
- UE 侧编辑器已关时走 `UnrealEditor-Cmd -run=pythonscript -unattended -NullRHI`；`AssetImportTask.save` 必须 True，否则 commandlet 退出丢弃整次导入。
- **保存必须验真**：`EAL.save_asset`／`save_loaded_asset` 在 PIE 期间静默返回 false；一律检查返回值，或改走 `EditorLoadingAndSavingUtils.save_packages([pkg], False)`，并以回读／uasset mtime 为准（2026-09-25 视模金属槽因此退回 WorldGridMaterial）。
- FBX 导入即使 `import_materials=False` 仍会**按槽名匹配项目内同名材质**；匹配不到就是 WorldGridMaterial——拆槽名（Metal/Wood）不要指望自动匹配，导入后必须显式绑定并回读。
- **拆槽会平移下游按索引引用槽的数据**：`Content/ColdSteelData/modular_outfits.json` 的 `hide_source_materials` 按索引隐藏源视模手臂槽（`FPSModularOutfitComponent` 逐 LOD 关 section），旧 3 槽布局 [1,2] 在 4 槽布局下会隐藏 Metal。拆槽交付前全局搜索按索引引用（手模隐藏、覆写表），该 json 运行时读取、改后重启生效。
- 视模"部件缺失"先区分三层：资产槽材质（commandlet 回读盘）、运行时 section 隐藏（modular_outfits）、材质渲染（离屏 SceneCapture 渲染，`-ExecutePythonScript -RenderOffscreen` 独立隐藏编辑器，参照 RuneSword run_review.ps1；PIE 期间活编辑器不能 spawn 诊断 actor）。
- 静态网格换 FBX 用**删除后全新导入**：重导入保留旧槽名/旧槽，槽索引与面索引对应不可靠；LOD 用 `StaticMeshEditorSubsystem.import_lod` 补回＋`set_lod_screen_sizes`。
- **资产写边界**：运行中编辑器持有 .uasset 文件锁（外部 commandlet 删/改报 Error 32）；活编辑器 `import_lod` 异步生效（恒返回 -1、后续 tick 落地），失败批次的排队任务还会污染同路径重导包。整包替换安装（删＋新导＋LOD）放**编辑器关闭后的 commandlet 窗口**；活编辑器桥只做槽绑定、save_packages 等短操作。
- UE 5.8 Python：MI 参数用 `MaterialEditingLibrary.set_material_instance_*_parameter_value`（对象方法已移除）；`StaticMaterial` 只有 `material_slot_name`／`material_interface`；`Texture2D` 无尺寸属性。
- commandlet 里 `print()`／`unreal.log()` 都不进日志：探针脚本把结果写 JSON 文件再读。
- 覆盖任何已发布二进制（FBX、图标 PNG）前先备份进任务目录 `Before/` 并把前后散列写进 `before-backup.json`；失败重跑可能把新文件误备为旧文件，备份源优先找作者源文件。
