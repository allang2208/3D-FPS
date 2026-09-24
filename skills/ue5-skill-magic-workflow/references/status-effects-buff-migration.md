# 状态（Buff/Debuff）系统迁移：旧 gamedev → UE 状态栏与机制层

2026-09-24 完成 100% 迁移（未测试，用户自测）。案例：`Docs/Combat/buff-migration-audit-20260924/`（五卷源盘点 + 目标盘点 + 覆盖矩阵）。本文件沉淀可复用方法与该域的实现合同；单状态定义一律以 `Content/ColdSteelData/status_effects.json` 为唯一目录源。

## 1. 迁移方法（先清单后代码）

1. **源侧五卷穷举**再动手：①ID 全目录（实体注册 ∪ HUD 独有 ∪ 未注册施加 ∪ 事件目录，含图标/色/参数与源码行号）②逐状态机制实现 ③全部施加入口 ④HUD 规格与隐藏语义 ⑤总数对账（例：106 静态 = 28+10+5+63）。目录表是数据真源，可直接脚本落盘（`Tools/Combat/generate_dungeon_event_buffs.py` 从审计表生成 63 条 JSON，图标/色/参数/按场数一体）。
2. **覆盖矩阵**是唯一验收面：每行=旧 type+图标+旧机制+UE 落地点+状态（♻️已有/🆕新增/⚠️机制就绪但生产者宿主未迁移）。"100% 迁移"的完成定义=矩阵无未决行，而不是所有卡都会亮。
3. 迁移决策（复刻旧缺陷 or 修复）写进矩阵 §4 偏差表：如旧 HUD 串台（无阵营守卫）按**修复**迁移；旧"3 秒后原地复活"简化为即时。旧死字段（`_synergyPoisonChance` 类）**不接线**并在矩阵标注，防后人当规格恢复。

## 2. 架构合同（FPSGAME 状态域）

- **显示层**：`UStatusEffectsComponent` 每实体 Records（`SetTimed/SetTimedDisplay/SetPersistent/SetBattles/Remove`，同型刷新保留更长 End）+ 毒/恐惧**活状态适配器**（真相在组件字段，Snapshot 时合成）。HUD（`UStatusEffectsHUD`）只绑玩家 pawn——怪物卡片是内部账本，与旧"玩家状态栏"语义一致。`HasType` 目录门用于过滤无正式条目的动态 ID（如 `dungeon_relay_*`），避免渲染 "?" 卡。
- **机制层**：目标侧状态字段与乘区集中在 `UCombatStatusFormula`；承伤链按旧 `takeDamage` **乘区顺序逐段 floor**（防御+腐蚀/shred→魔法加成→魔易伤→石化→感电→无人机→献祭→冻结→来源侧→标记→圣佑→玩家侧金刚石封顶），怪物侧在 `CombatFormulaRuntime::MitigateMonster`、玩家侧在 `UFPSCombatHealthComponent::DamageAfterArmor(Damage,Type,Attacker)`——两条链顺序必须逐行对照，不要顺手合并。
- **免疫闸门** `IsImmune()` 必须铺到**所有**入口：全部 Add*、毒组件 AddStack、恐惧 Apply，漏一处即偏差。
- **控制阻断**：`BlocksMovement()`（stun/bind/frozen/petrified）统一给 `StartDodge` 等入口；玩家控制中断走 `UPlayerGuardBreakComponent`，怪物走各 AI 类 `InterruptAttack` 白名单。
- **献祭/地牢层**：`FColdSteelFormulaBuff`（Battles=旧地牢事件按场消耗，Specials=旧 special 块原值）；卡片同步 `SyncTributeTiles/SyncDungeonBattleTiles` 用 **published 集 diff 发布**（TMap 存上次值，变了才写），逐帧调用安全。施加通道 `ApplyDungeonEventBuff(Id)` 读 `dungeon_event_buffs.json`。

## 3. 性能与广播纪律（硬性）

- 状态 Tick **禁止**每帧 SetTimed：DoT 卡（burn/bleed/corrosion/drone）改**事件式**——层数/场次变化才重发布，倒计时由 `End` 自然收敛（0.1s HUD 刷新读 Remaining）。
- JSON 目录（`status_effects.json`、`dungeon_event_buffs.json`）是**进程内 static 缓存**：改数据必须重启编辑器才生效，交付说明里写清。
- 图标占位策略（用户指定）：emoji 字符直进 JSON `icon`，`seguiemj.ttf` 渲染；换真美术时只改 JSON 字段。颜色 `#rrggbb` → `FColor::FromHex`（不带 alpha；`FColor::Gold` 不存在，用 `FColor(255,215,0)`）。

## 4. 踩坑清单（本次实际付出过代价）

- UHT/声明同步：头文件删字段必须同步删 cpp 引用（`RenewalStacks` 残留=C2039）；同一方法在头里声明两次=C2535。全量重写头文件后逐字段对照旧 cpp。
- `TSet` 无 `operator==`：diff 发布用 contains/Reset 重建或 `TMap`，别写 `A==B`。
- 灼烧跳伤保持 `UFireballDamage`（已注册魔防链）；只有新机制（矿毒）才开 `UStatusMagicDamage` 并同步 `CombatFormulaRuntime::IsMagic`。
- 过载链传导要给被传导者 **+1 感电层**（级联过载），只传伤害是漏项。
- PowerShell 读 emoji JSON 一律 `-Encoding UTF8`；`FMath::Max(0,...)` 混 float/int 会 C2782。
- 并行工作树（本仓库 600+ 脏文件常态）：文件级 `git add` 会把他人未提交的感染/储物/巫婆/手势计费等 hunks 夹带发布。实操：纯本任务文件按路径 `git add`；混合文件从工作树拷贝到 scratch，整行删他人新增行 + 行内回改他人对 HEAD 行的修改（`git show HEAD:<path>` 取原文），断言零残留标记后 `git hash-object -w --path=<rel> <blob>` + `git update-index --cacheinfo 100644,<sha>,<rel>` 入索引——工作树逐字节不动，他人未提交内容在提交后仍以未暂存 diff 形式留在树上。暂存完用 `git grep --cached <他人标记>` 与 `git diff --cached --check` 复核。切片在并行期无法独立编译（基线 HEAD 亦引用未发布子系统），以全工作树构建绿作为代码正确性证据并在提交说明中如实记录。

## 5. 新增一个状态的标准步骤

1. `status_effects.json` 加条目（type/icon/name/color/description；emoji 占位）。2. `UCombatStatusFormula` 加 `AddXxx`（IsImmune 闸门＋卡片＋数值字段）与消费点（乘区/Tick/MovementMultiplier）。3. 若走控制：并入 `BlocksMovement`/`PurgeTransient`/`CleanseDebuffs` 白名单（净化清单见旧 SUPPORT_CLEANSE_TYPES 11 项，感电连层数硬置零）。4. 生产者缺失时机制照迁、卡片照挂，在矩阵标 ⚠️ 宿主。5. 构建绿即交付，声明未测试。
