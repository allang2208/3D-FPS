# 旧项目（E 盘 gamedev / Godot）装备数据残留审计 · 2026-10-18

用户要求：排查项目里是否还留着旧项目（`E:/3d/3-dfps`、`E:\无尽轮回`，已归档到 `E:/3d/trash/repository-ue5-root-20260910`）的数据与占位，重点是装备。结论：**是，没有剔除**；但需要区分“死数据残留”和“有意的历史/合规记录”。

## 一、判定方法

- 当前 UE 的物品定义只来自 `Content/ColdSteelData/items.json`（运行时 `Definitions` 映射）。
- `Content/ColdSteelData/source-combat-items.json` 只被 `CombatItemFormula::Read` 读取，按 `weaponId` → `name` → `Item.Definition` 顺序查表，给实例**缺失的顶层字段**补默认值。
- `weaponId` 在源码里只被读取、从未写入（全仓库仅 `CombatItemFormula.cpp:30` 一处），`items.json` 也没有任何条目带 `weaponId`。
- 因此：覆盖层条目只要 key 既不等于某个定义 id、也不等于某个物品 `name`，就**永远查不到**——即死数据。

## 二、source-combat-items.json：279 条中 274 条不可达（2026-10-19 已归档；清理后现役 5 条，蓝魔法师与灰钢锁子甲追加后 14 条）

可达的只有 5 条（都是 UE 现役装备的战斗/手感数值）：

| 可达条目 | 内容 |
| --- | --- |
| `ue_field_gloves` | meleeAttackSpeed 0.1 / reloadSpeed 0.1 / bowDrawSpeed 0.1 |
| `ue_field_gloves_black` | meleeAttackSpeed 0.05 / reloadSpeed 0.05 |
| `ue_steel_gauntlets` | reloadSpeed −0.1 / bowDrawSpeed −0.1 |
| `ue_hardknuckle_gloves` | reloadSpeed 0.05 / adsPercent −0.05（2026-10-18 新增） |
| `ue_st6_sleeves` | reloadSpeed 0.05 / sprintStaminaCost −0.1（2026-10-18 新增） |

> 2026-10-19 同日追加：蓝魔法师五件套（`ue_blue_mage_hat/robe/pants/boots/gloves`）的 `armorSet` / `setBonusDesc` / `bonusStats` 先写入本表（10 条）；灰钢锁子甲四件（`ue_steel_armet`、`ue_chainmail_shirt`、`ue_chainmail_pants`、`ue_armored_boots`，护手已在 5 条内）随后加入，现役变为 14 条。上述 274 条归档与“原 279 条”的结论不变。数值见 [蓝魔法师五件套](blue-mage-set-values-20261019.md)、[灰钢锁子甲五件套](steel-chainmail-set-values-20261019.md)。

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

## 五、清理执行（2026-10-19）

用户确认：保留便携背包，其余废案先删除，避免误会。按原方案 A 执行：

- `Content/ColdSteelData/source-combat-items.json` 已收缩为 5 条现役覆盖（`ue_steel_gauntlets`、`ue_field_gloves`、`ue_field_gloves_black`、`ue_hardknuckle_gloves`、`ue_st6_sleeves`），786 字节 / 45 行。2026-10-19 晚追加蓝魔法师五件套与灰钢锁子甲四件后为 14 条；下列 SHA-256 记录的是清理完成时的 5 条状态。
- 274 条旧公式原样移入 `Docs/Archives/legacy-gamedev-combat-items-20261019.json`（79,694 字节）；键、值、顺序逐条保留，归档与现役表的并集经语义比对等于原 279 条。
- `CombatItemFormula::Read` 行为不变：这 274 条本来就查不到，运行时零变化；未改 C++、未编译、未进游戏。
- `ue_portable_backpack` 保留在 `items.json`，未动；`items.json` 在本次清理中零改动（蓝魔法师五件套的 `defense` 为同日稍后另一任务，见 [蓝魔法师五件套](blue-mage-set-values-20261019.md)）。
- 防复发：`SourceAssets/BenelliM4Super9020261006/publish_catalog.py` 改读归档中的 `Super90.attackFormula`；`Tools/Combat/export_remaining_formula_data.mjs` 改为只写归档文件，不再覆盖现役表。
- 文档引用同步：`Docs/Items/tactical-gear-values-20261018.md`、`Docs/Weapons/pkm-retirement-20260922.md`、`pkm-fire-and-balance-20260922.md`、`apprentice-staff-migration-20260927.md` 指向归档。
- 校验：现役表 SHA-256 `F398E3F49D29FDC80306813F68D0CA9E4FE57A13F9F87C0E60E71230FE4CF635`；归档 SHA-256 `CC15340006B38062AC2E509F4B351F0F186643B8BCC8D957AD189E5B2EBE86F0`；归档 key 与 `items.json` 的 id/name 零匹配，并集语义等于原 279 条。

备选 B（彻底删除）与 C（顺带清 `res://` 图标/占位图）未采用；`items.json` 的 92 条旧 `icon` 路径保持原样。

## 六、状态

- 2026-10-18 只读排查；2026-10-19 执行清理，现役表只剩 5 条，旧表在 `Docs/Archives/legacy-gamedev-combat-items-20261019.json`；同日稍后追加蓝魔法师 5 条、灰钢锁子甲 4 条，现役表 14 条。
- 排查脚本：临时目录 `audit_legacy_equipment.py`、`audit_legacy_marks2.py`、`classify_legacy.py`（未入库）。