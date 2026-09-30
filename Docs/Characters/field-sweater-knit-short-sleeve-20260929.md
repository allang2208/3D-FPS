# 针织长袖升级与炭灰短袖 T 恤（2026-09-29）

2026-09-30 用户发现炭灰短袖的第三人称破口及攀爬衣袖破片。已重做 Body 裁切/身体覆盖并修复 Traversal 肩端，替换这两处活动引用，同步掉落与图标，见 [炭灰短袖修复](charcoal-garment-repair-20260930.md)。下文 `world_covers=[3]` 和旧 Body/Traversal 版型属于历史状态；曾有完整衣身资产不等于建模和变形质量合格。

2026-09-30 两款装备图标已按现行透明底、竖直正交、320×320 和 91% 填充规则重制，校准深色布料曝光并同步旧存档图标路径；独立出图入口及实际落盘见 [装备图标更新](field-sweater-inventory-icons-20260930.md)。穿戴与掉落模型保持。

沿用原野行长袖上衣的拟合、原生骨架、物品 ID 和装备槽。用户中途指定炭灰配色改为短袖，因此本轮交付两种独立版型：橄榄色粗针织长袖与炭灰色细棉布短袖 T 恤。

## 制作

- 针织主表面和罗纹表面分别使用 8×8 线圈，周期长度 1.92 cm，纱线直径 0.72 mm。按线圈截面投影生成高表面，再叠加同源细纤维高度；法线直接由该高度场求导，不从颜色推断。两种可编辑纱线高模各 163,840 四边面，仅供作者制作，不导入游戏。
- 两套 2048² BaseColor／Normal／ORM／Relief 图；ORM 为遮蔽／粗糙度／金属度，Relief 为高度／纤维遮罩／平铺安全值。保留 mip 和流送，法线为 OpenGL 来源，UE 导入翻绿。
- 布料沿蒙皮 UV 采样。沿用当前衣袖的厘米尺度 UV 和袖口局部尺度，使用有界 6+2 步浅层视差；长袖深度 0.04 cm，棉布深度 0.006 cm，第三人称、内壁与掉落为 0。棉布使用八倍细密的线圈尺度与更弱绒面，不复制粗毛衣观感。
- 炭灰短袖在上臂长度约 55% 处裁切，保留原内外壳，并做向内回折的封闭卷边。原生 M4 母版处理后映射至各骨架，Body 按自己的上臂裁切，不套用 M4 空间。
- JSON 作者源包含完整几何、UV、法线、骨骼和权重。Blend 包含明确标注的 HIGH 纱线与 M4／Body 游戏几何，游戏几何的原生绑定作者 JSON 路径写入对象属性；不宣称静态展示对象包含整套动画绑定。

## 覆盖与接入

FPSModularOutfitComponent 现在优先使用衣服自己的 covers 字段，第三人称优先 world_covers；缺省仍使用原 profile.shirt_covers。只在已有换装构建时读取，不增加 Tick。炭灰短袖 covers=[] 保留原生上臂与前臂，world_covers=[3] 仅隐藏衣服内的躯干。手套仍独立应用自己的覆盖范围，上一轮 WristUnderlapSkin 保留区不改。

橄榄色继续按长袖覆盖；短袖袖口下方显示现有皮肤，未复制第二层裸臂或改动裸手基准。两款均逐材质槽绑定，配方 material 为空。保留物品属性、库存和存档，炭灰名称更新为“炭灰短袖 T恤”。第一人称、Body、掉落模型与正式装备图标同步。

## 文件与实际状态

- Tools/ModularOutfit/build_field_sweater_knit.py：高表面场投影烘焙、长袖原生数据。
- Tools/ModularOutfit/author_charcoal_short_sleeves.py：短袖和内卷边。
- Tools/ModularOutfit/save_field_sweater_knit_blend.py：可编辑高模／游戏母版、掉落 FBX、正式图标。
- Tools/ModularOutfit/import_field_sweater_knit.py、publish_field_sweater_knit.py：后台资产构建保存及精确发布。
- SourceAssets/FieldSweaterKnit20260929/：制作数据、Blend、贴图、保存回执、构建日志和 published.json。

背景制作与图标出图属于交付；未启动 UE 编辑器或游戏进行验收，未做动作或性能测试。实际短袖接触、材质及换装效果由用户测试。
