# 棕色皮革靴与皮革裤

本对话先设计与当前棕色露指皮革手套配套的靴子、裤子概念图，用户随后要求继续构建。新增独立装备 `ue_leather_boots` 和 `ue_leather_pants`，现有手套 `ue_field_gloves` 的模型、贴图、动作和属性保持原状。

## 外观与源

- 原图：`SourceAssets/BrownLeatherSet20261004/LeatherBoots_Concept_v1.png`、`LeatherPants_Concept_v1.png`；`Concept_prompts.txt` 保留内置生图提示词，`ExistingFingerlessGlove_Reference.png` 为实际手套图标参考。
- 完整可编辑母版：`BrownLeatherSet.blend`，包含分件、完整 Jason 原生骨架、打包纹理、普通裤脚和两种靴子搭配。默认显示高筒靴配套组合，其余裤脚集合隐藏但保留。
- 原始构件源：`LeatherSet_Construction.blend`；厘米制几何、面角法线、UV、骨架、权重与材质槽保存在 `Jason_Leather*.json`。
- 概念图仅有正面斜视，后侧、内部与装配结构按服装结构制作，不称扫描还原。

皮革靴保留人体脚型与小腿收腰，补齐皮革包头、加固后跟、双侧扣、贯穿后侧的绑带、靴口内壁、薄卷边、鞋底沿条和缝线。鞋底在维持原脚底最低点的情况下形成浅足弓与低后跟。款式不带金属护胫或钢鞋头，金属仅用于扣件。

皮革裤具有连续腰臀、弧形裆部、逐渐收窄的裤腿与实体裤口；新增腰带、袢、搭扣、平面门襟、口袋缝边、弧形大腿拼缝和柔性护膝片。护膝是贴合腿形的薄皮革补强，沿边双线缝合。已有裤装提供尺度与原生绑定参考，未覆盖其游戏资产。

## 材质与绑定

皮革颜色参考当前手套的制作记录 `GloveCompanionDetail20260928/Fingerless/artwork.json`：线性 RGB 约为 `[0.088733, 0.050687, 0.033175]`。新作周期皮革微高度场，将颗粒与压纹烘焙到 1024² BaseColor、Normal、ORM；不是直接把手套图集套到裤腿。强化裁片使用同源贴图与稍深色调，鞋底沿用已保存皮革底材质。

五个槽为老化钢扣、暖棕皮革、层压皮底、蜡线和加固皮革。几何承担包边、厚度、较粗缝线和扣件，微颗粒来自 `LeatherHighField.npz`。UV 以 25 cm 标定、材质重复四次形成 6.25 cm 周期；法线为 OpenGL 约定、UE 翻绿，ORM 为遮蔽／粗糙度／金属度。保留 mip 与纹理流送，不新增 POM。

双靴作者 LOD0 为 61,100 个位置顶点、113,630 个三角形、66 个可编辑分件；裤子每个版本为 40,974 个位置顶点、73,584 个三角形、46 个可编辑分件。分件合入各自一个运行时骨骼网格；细节不创建独立组件或新骨骼，保存三档 LOD。制作高模皮革表面场位于隐藏 `BAKE_ONLY` 集合，不导入游戏。

靴子使用现有脚踝／前掌与小腿原生绑定；裤子保留同骨架体系并沿裤装原生权重制作新增裁片。未改动作、新增 Tick 或布料模拟。动作、穿插和性能未验收，面数不用于推算帧率。

## 接入与配套

- `ue_leather_boots`：棕色皮革靴，鞋靴槽 13，普通品质，2×3 格，初始基础防御 12、价格 55。
- `ue_leather_pants`：棕色皮革裤，裤装槽 15，普通品质，2×3 格，初始基础防御 20、价格 50。
- 无新增速度惩罚或套装加成；同套表示外观设计关系，数值为初始配置，未经平衡测试。
- 普通裤脚搭配裸足或休闲鞋；`ShortBootsFit` 搭配现有系带皮靴；`HighBootsFit` 搭配新棕色皮革靴或灰钢铠甲靴。
- 裤脚按完整截面缩放，内衬、包边与缝线保留相对厚度，不将所有层投射到同一圆筒表面。只修改独立搭配版本。
- 新皮革靴沿当前高筒靴的身体遮挡合同；牛仔裤、工装裤、锁子甲裤对新靴子的搭配复用已有高筒收口资产。活动身体基础网格不变。
- 背包、装备栏、仓库与存档沿通用物品流程，正式图标来自实际展示网格与生产材质。靴子图标为单只斜视，裤子为完整一条；掉落模型分别为一双靴和整条裤子。

## 制作入口与状态

`Tools/BrownLeatherSet/` 中的 `bake_surfaces.py`、`author_set.py`、`prepare_fits.py`、`save_editable.py` 制作外部源；`save_assets.py`、`publish_catalog.py` 与 `finish_background.ps1` 负责后台资产保存、定向发布与图标生产。`geometry.py` 是既有作者工具的独立快照，不会执行旧铠甲靴的生成或回写其文件。

新 UE 资产根：`/Game/Characters/ModularOutfit20260924/BrownLeatherSet20261004`。只在保存回执产生后发布两个新物品及三个已有裤装的新靴子映射；发布前重新读取当前配置并保留无关内容。玩家库存、存档和现有手套不修改。

可编辑源、表面烘焙、两件模型与裤脚配套均已制作。UE 已保存皮革靴、普通皮革裤、短靴配套裤和高筒靴配套裤四个骨骼网格，以及两个掉落网格、两个展示网格、材质与三档 LOD；两个独立物品及裤脚搭配映射已发布。

两张正式图标已生产到 `Content/ColdSteelData/Icons/ue_leather_boots.png` 与 `ue_leather_pants.png`，作者目录保留副本。最终落盘分别记录在 `saved_assets.json`、`published.json`、`icon-ue_leather_boots.log` 和 `icon-ue_leather_pants.log`，后台完成标记为 `BROWN_LEATHER_SET_BACKGROUND_COMPLETE`。本轮没有原生 C++ 改动，无需重新构建 FPSGAME 模块。

本轮不启动编辑器、游戏、PIE 或额外验收渲染，不主动检查、测试或回归，由用户测试。仅生产正式装备图标。
