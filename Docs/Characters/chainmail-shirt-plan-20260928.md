# 锁子甲上衣：方案与制作

2026-09-29 活动家族已更新为 `ChainmailInterlace20260929`，交错锁环、实体袖口、分槽材质、原生派生和统一图标见 [V2 制作与接入](chainmail-interlace-v2-20260929.md)。[第一版表面升级](chainmail-ring-relief-20260929.md) 保留为历史；下文为初始细密灰钢材质及版型／绑定来源，不是重跑旧导入恢复旧表面的指令。

用户要求参考现有长袖衣服，使用钢甲护手当前的灰色金属护层，重点完成手臂覆盖。独立物品 `ue_chainmail_shirt`，名称“灰钢锁子甲”，占上衣槽 7，与手套槽分开穿脱。

## 制作方案

1. 从当前 `ue_field_sweater` 的实际装备配方读取全部原生网格。保留现有肩部、肘部、前臂轮廓和完整蒙皮，包括已调整的袖口搭接，派生独立锁子甲资产；原上衣和裸臂不改。
2. 沿用 `GreyMetalLiner_Baked` 对应的灰色金属环纹 BaseColor、Normal、ORM 三张生产贴图。在新上衣的 UV 上按物理面积校准密度，避免直接套用手套 UV 后锁环过大或变细。保留原有 UV 接缝和蒙皮，不使用会在动作中滑动的世界坐标投影。
3. 贴身锁子甲随原手臂骨架变形。肩部至前臂覆盖 V7 的上臂／前臂区，手和腕口由原有裸手或独立手套接续；复用已拟合袖口与手套的搭接位置。不另建动作、不增加逐环刚体或实时布料求解。
4. 第一人称各武器、双持、弓、攀爬及 Body 采用各自现有原生绑定。新网格沿用三级 LOD，单个材质槽；环纹细节由重复 PBR 表达。
5. 配套制作完整上衣掉落模型与 320×320 透明装备图标，单件竖向居中、约 91% 填充，使用同一灰色金属材质。图标渲染是本次物品交付，不启动游戏或动作验收。
6. 全部目标资产实际保存后，精确增加物品与换装配方。沿用现有库存、穿脱、存档和调参生成入口；本轮不沿用钢甲护手的独有防御和减速数值。

## 实施范围

- 作者目录：`SourceAssets/ChainmailShirt20260928/`。
- UE 资产目录：`/Game/Characters/ModularOutfit20260924/ChainmailShirt20260928/`。
- 制作入口：`Tools/ModularOutfit/export_chainmail_sources.py`、`author_chainmail_shirt.py`、`import_chainmail_shirt.py`。
- 数值、手套材质与现有衣服保持各自现状。新上衣的战斗数值可在后续按用户指定配置。

## 本次交付

- 已保存 22 个独立骨骼网格，全部沿用当前上衣原生骨架与蒙皮，生成三级 LOD、单个灰钢材质槽。覆盖 Body、M4、AKM、QBZ191、ASH12、M16、M1911、DW715、A762、SVD、PKM、RuneSword、FrostSword、FrostArms、Axe、Pickaxe、DW715_l/r、M1911_l/r、Traversal、Bow。
- 已保存 `Materials/MI_ChainmailShirt_GreySteel` 和 `Pickups/SM_ChainmailShirt_Pickup`，共新增 24 个 UE 资产。材质实例继承钢甲护手当前的 `FullMetal20260928/M_GreyMetalLiner`，未修改其父材质或贴图。
- 已增加 `items.json` 的“灰钢锁子甲”与 `modular_outfits.json` 对应的独立上衣配方。上衣占格 3×3，复用原上衣类别与库存保存契约；未给新物品添加战斗属性。
- 已发布统一的 320×320 透明图标：`Content/ColdSteelData/Icons/ChainmailShirt20260928/ue_chainmail_shirt.png`。背包、装备栏和仓库引用同一物品图标。
- 作者源包含 22 份独立原生绑定 Blender 文件、规范化 UV 的网格数据、完整衣服 FBX、生产图标及可编辑展示场景。原始版型沿用项目已有 MakeHuman fisherman sweater 派生资产，来源与原授权记录保持一致。
- 导入完成回执：`SourceAssets/ChainmailShirt20260928/published.json`；执行结果：`Saved/chainmail-import-20260928-01.json`。本次使用已运行编辑器的互斥桥完成保存，没有启动新编辑器或游戏，不需要 C++ 构建。

重新进入游戏后，从物品生成入口搜索“灰钢锁子甲”（`ue_chainmail_shirt`），放入上衣栏。未进行游戏测试；肩肘变形、武器动作和袖口搭接由用户在游戏内测试。
