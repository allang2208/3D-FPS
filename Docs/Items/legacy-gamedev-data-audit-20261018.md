# 旧项目（E 盘 gamedev / Godot）装备数据残留审计 · 2026-10-18

用户要求：排查项目里是否还留着旧项目（`E:/3d/3-dfps`、`E:\无尽轮回`，已归档到 `E:/3d/trash/repository-ue5-root-20260910`）的数据与占位，重点是装备。结论：**是，没有剔除**；但需要区分“死数据残留”和“有意的历史/合规记录”。

## 一、判定方法

- 当前 UE 的物品定义只来自 `Content/ColdSteelData/items.json`（运行时 `Definitions` 映射）。
- `Content/ColdSteelData/source-combat-items.json` 只被 `CombatItemFormula::Read` 读取，按 `weaponId` → `name` → `Item.Definition` 顺序查表，给实例**缺失的顶层字段**补默认值。
- `weaponId` 在源码里只被读取、从未写入（全仓库仅 `CombatItemFormula.cpp:30` 一处），`items.json` 也没有任何条目带 `weaponId`。
- 因此：覆盖层条目只要 key 既不等于某个定义 id、也不等于某个物品 `name`，就**永远查不到**——即死数据。

## 二、source-combat-items.json：279 条中 274 条不可达

可达的只有 5 条（都是 UE 现役装备的战斗/手感数值）：

| 可达条目 | 内容 |
| --- | --- |
| `ue_field_gloves` | meleeAttackSpeed 0.1 / reloadSpeed 0.1 / bowDrawSpeed 0.1 |
| `ue_field_gloves_black` | meleeAttackSpeed 0.05 / reloadSpeed 0.05 |
| `ue_steel_gauntlets` | reloadSpeed −0.1 / bowDrawSpeed −0.1 |
| `ue_hardknuckle_gloves` | reloadSpeed 0.05 / adsPercent −0.05（2026-10-18 新增） |
| `ue_st6_sleeves` | reloadSpeed 0.05 / sprintStaminaCost −0.1（2026-10-18 新增） |

死数据 274 条，按类别：

| 类别 | 条数 | 例子 |
| --- | --- | --- |
| 旧武器 id（`weaponN`） | 64 | `weapon1`…`weapon65`（含 weapon56–65 的盾牌组） |
| 旧武器/其它（英文 slug） | 54 | `akm`、`m416`、`qbz191`、`super90`？、`g18_pistol`、`apprentice_staff`、`training_bow` 等 |
| 旧套装防具（英文 id） | 36 | 12 套 × 3 件：`light`/`flowing`/`heavy`/`robe`/`eclipse`/`lunar`/`stellar`/`zhenyue`/`oracle`/`oracle_robe`/`holy`/`tiangang` 的 `_helmet`/`_armor`/`_boots` |
| 旧套装防具（中文名） | 36 | 疾风轻甲、壁垒重盔、苍月法袍、神域战靴… |
| 旧饰品（英文 id + 中文名） | 18 + 15 | `necklace_*`/`ring_*`/`belt_*` 与 狮心项链、猛攻戒指、生命腰带… |
| 旧盾牌 | 16 | `small_shield`/小圆盾、`oak_garrison_shield`/橡木卫戍盾、`reverse_fate_doomwheel_shield`/逆命劫轮盾… |
| 旧武器/其它（中文名） | 35 | 沙漠之鹰、M416、符文长剑、学徒长杖… |

危害：这张表**活数据与死数据混排且无标记**。2026-10-18 的装备数值任务中，它先被误认成“装备权威表”，随后又被写入了两件新装备的 `bonusStats`；实际只有 5 条真正生效。后续任何按“参考其他数值”做装备的人都会再次踩到同一坑。

## 三、有意的历史/合规记录（建议保留，只做标注）

- `Docs/Weapons/pkm-retirement-20260922.md`：PKM 历史数值“不属于本次 UE 接入，保留”。
- `Docs/Weapons/pkm-fire-and-balance-20260922.md`：`PKM.attackFormula` 是原型历史值。
- `Docs/Weapons/apprentice-staff-migration-20260927.md`：明确写了“已收录旧 weapon20/学徒长杖公式，不表示 items.json 已有可装备长杖”。
- `Docs/Skills/skills-magic-publication-20260915.md`：`CoreFormulaAuditCommandlet` 需要本机旧项目 `reference.json`（不在仓库）。
- `Docs/Characters/steel-gauntlet-stats-20260928.md`、`fingerless-hunt-leather-20260926.md`：这两件装备的数值本来就登记在这张表。

## 四、其它旧项目痕迹

| 位置 | 内容 | 判断 |
| --- | --- | --- |
| `items.json` | **92 条** `icon` 仍是 Godot 路径 `res://assets/...`；92 条全部另有可用的 `ue_icon`，UE 不读 `icon` | 旧数据残留；`Docs/Combat/ammo-icon-wiring-20260922.md` 说明“按原样保留”，可保留或清空 |
| `skills.json` | 5 条 `source = gamedev/data/skills.json:xxx`（溯源标注）；1 条 `quickCombat.icon = Skills/quick_combat_placeholder.png` | 溯源保留；占位图待换正式图 |
| `treasure_chest_assets.json` | `/Game/Props/GamedevTreasureChest20260922/...`、`identity: gamedev_dungeon_treasure` | UE 内实际重制资产（2026-09-22），非残留 |
| `Content/ColdSteelData` 的 11 个“C++ 未引用”JSON | warhammer/common-hammer、`*-modules.json`、`incinerator-recipes.schema.json`、`provenance.json`、`shared-sword-pommels.json` 等 | 均有数据层或 Tools 脚本引用；`hk416_asset_attribution.json` 是署名/许可材料，全部保留 |
| `items.json` 占位条目 | `占位/placeholder/测试/dummy` 名称条目 **0 条** | 干净 |
| 旧项目仓库本身 | 6199 文件已归档 `E:/3d/trash/repository-ue5-root-20260910`（manifest + SHA-256）；旧 Godot 技能仅作迁移参考 | 合规，不在 D 盘工程内 |

## 五、清理方案（未执行，等确认）

- **方案 A（推荐，低风险）拆分标注**：把 `source-combat-items.json` 收缩为 UE 活数据（现 5 条 + 以后新增），并在文件加 `_scope` 说明；把 274 条旧公式原样移到 `Docs/archive/legacy-gamedev-combat-items-20261018.json`，同步更新 PKM/学徒长杖等文档的引用路径。`CombatItemFormula::Read` 行为不变（它本来就查不到这些 key），运行时零风险。
- **方案 B（彻底）直接删除 274 条**：只在本文记录类别、数量与文件 SHA-256；风险是失去人工对照旧公式的历史值，且 PKM/学徒长杖文档的引用会失效，需要改写。
- **方案 C（顺带清理）**：清空 `items.json` 92 条 `res://` 旧图标路径（全部有 `ue_icon` 兜底）；`quick_combat_placeholder.png` 换正式图（需要美术出图）；`skills.json` 的 `gamedev/...` 溯源字段保留。

## 六、状态

- 本轮只读排查，未删除或移动任何数据；`git status` 中这些 JSON 仍属未提交的并行工作。
- 排查脚本：临时目录 `audit_legacy_equipment.py`、`audit_legacy_marks2.py`、`classify_legacy.py`（未入库）。