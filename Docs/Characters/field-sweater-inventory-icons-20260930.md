# 炭灰短袖与橄榄针织长袖装备图标（2026-09-30）

同日后续：炭灰短袖 Body 发现裁切和拟合缺陷后，已经从 `CharcoalGarmentRepair20260930/Authored/Body.json` 同步更新其图标；独立入口识别当前 BodyV4 引用。最新曝光约 -0.246，平均 sRGB 约 60/63/69。橄榄长袖保持本页原结果。模型修复见 [炭灰短袖修复](charcoal-garment-repair-20260930.md)。

按用户要求，将两款装备图标调整到与锁子甲相同的现行图标规则。本轮只制作 PNG 和独立展示源，未改穿戴网格、掉落模型、动作、属性或物品占格；未启动 UE 或游戏。

## 已完成

- `ue_field_sweater`：使用 `FieldSweaterKnit20260929/Authored/Body.json` 的完整橄榄长袖。
- `ue_field_sweater_charcoal`：使用同家族 `ShortSleeve/Body.json` 的完整短袖 T 恤，保留真实短袖卷边。
- 两款均由当前原生骨架与权重重建独立展示副本，双上臂放低 12°；不回写游戏姿态，不出现人体或人台。
- 正交镜头、竖直展示、透明 RGBA、320×320，依实际相机空间轮廓居中。生产图像主体填充 91.25%，中心为画幅的 0.5/0.5。
- 颜色直接读取 UE 材质制作器的线性 tint，使用现行针织/棉布 BaseColor、Normal、ORM，保留罗纹、内壁分槽。离线加入 ORM.R 遮蔽，以 Standard 色彩变换和最多两次曝光修正保持深色布料身份；不声称与 UE 着色逐像素相同。
- 橄榄长袖最终曝光 0、不透明区域平均 sRGB 约 91/97/85；炭灰短袖最终曝光约 -0.263、平均约 60/63/69。长袖保留较粗针织，短袖保留细密棉布。

## 实际落盘与引用

正式 PNG：

- `Content/ColdSteelData/Icons/FieldSweaterKnit20260929/ue_field_sweater.png`
- `Content/ColdSteelData/Icons/FieldSweaterKnit20260929/ue_field_sweater_charcoal.png`

原 `items.json` 的 `ue_icon` 路径保持，背包、装备栏、仓库继续共用。两张作者源 PNG 与 `Icons/ModularOutfit20260924/` 下的旧存档图标别名一同替换；无需物品数据迁移或 UE Texture2D 导入。

独立可编辑场景、作者 PNG、旧图备份及两份生产回执位于 `SourceAssets/FieldSweaterInventoryIcons20260930/`。后台制作日志：`Saved/field-sweater-inventory-icons-20260930.log`。

## 后续出图

`Tools/ModularOutfit/render_field_sweater_inventory_icons.py` 为独立入口，由 Blender 后台执行。只写图标与展示场景，不重导模型。

`save_field_sweater_knit_blend.py` 的完整制作和新增 `--icons-only` 均转入该入口；旧 `author_item_presentation.py` 在当前衣物家族激活时，也把这两款图标交给新入口，防止恢复旧曝光或把炭灰短袖画回长袖。

本轮没有运行游戏/UI 测试或额外验收截图。已经打开的 UI 可能仍持有旧纹理缓存，下一次进入游戏重新载入；实际装备栏效果由用户测试。
