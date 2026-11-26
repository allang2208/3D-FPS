# 野行船型翎羽帽

用户确认概念图后指定使用 Blender 尽可能精细建模。该帽为新物品 `ue_ranger_feather_hat`，名称“野行翎羽帽”，与已制作的 `ue_field_sweater` 皮革布料上衣配套。

## 结构与源文件

按当前 Jason 头部源几何拟合帽口。以头顶下 7.2 cm 为佩戴截面，根据该截面的实际椭圆范围留出内衬余量；作者坐标为 Jason 原生坐标，+Y 朝前、+X 为佩戴者左侧。FBX 导入后的头骨挂接变换由三个不共线的定位骨计算，避免猜测导入旋转与单位。

帽冠与翻边均有独立内外表面和实体口沿。帽冠厚度约 2.3 mm，翻边约 2.0 mm，皮革帽带约 1.4 mm；翻边外缘有直径约 2.6 mm 的皮革滚边。帽冠中缝、帽带和翻边带实体断续针脚。黄铜羽座有真实中空管壁、滚唇和两颗固定铆钉。

羽毛长度 19 cm，包含闭合薄羽片、逐渐变细的羽轴、420 条细羽枝起伏和轻微不齐的羽缘。羽轴、羽片和羽枝共用连续骨权重，根部固定在羽座中。沿用现有头部装备的局部弹簧，三个羽毛骨最大摆幅 5 度、频率 2.8 Hz、阻尼 0.8；帽体固定跟随头部。

Blender 母版包括完整游戏对象、11 组可独立编辑的分件，以及另置的真实表面高度烘焙源。游戏 FBX 仅导出游戏对象与绑定骨架，不含编辑副本和高模。

- 可编辑母版：`SourceAssets/FieldRangerFeatherHat20261021/Exports/FieldRangerFeatherHat_Detailed.blend`
- 游戏导出：`Exports/FieldRangerFeatherHat.fbx`（`FieldHat.fbx` 为现有导入器的兼容文件）
- 完整几何／UV／权重：`Authored/hat.json`
- 作者配方：`Tools/FieldRangerFeatherHat/author.py`
- 认可概念：`Design/FieldRangerFeatherHat_Concept01.png`

## 材质与预算

复用 `FieldRangerTop20261020` 的橄榄斜纹布、棕皮革、内衬、黄铜、缝线材质与原纹理对象，保持 8 cm 表面尺度。羽毛另有 1024×2048 BaseColor / Normal / ORM，来自明确的物理高度场；OpenGL 法线导入 UE 时翻绿。羽毛使用实体表面，不依赖透明裁片。

LOD0 为 **152,098 三角形**，额外几何用于实体内衬、连续帽边、缝线、羽枝与金属口沿。三档穿戴 LOD 目标为 100% / 55% / 25%，拾取和图标展示为 100% / 55% / 30%。没有根据面数推断帧率，也未做性能采样。

装备图标由实际 Blender 模型制作，320×320 透明底，同时保存对应静态展示几何和掉落模型。全部新 UE 包位于 `/Game/Characters/ModularOutfit20260924/FieldRangerFeatherHat20261021/`。

## 接入与状态

新增独立目录条目和 `head_equipment.ue_ranger_feather_hat`。装备槽、占格、价格及防御数值沿用现有野行奔尼帽模板；不替换已有帽子。头部配置通过共享字段事务写入器保存。

Blender 作者源、FBX 与图标制作完成；UE 穿戴模型、三档 LOD、羽毛材质、拾取模型、图标展示和 UI 纹理均已保存，新物品及头部挂接配置已注册。`saved_assets.json` 与 `published.json` 均记录完成，资产生产日志为 `save-01.log`。共享布料与皮革材质直接引用上衣的已保存资产。本次不修改 C++，无需重新编译原生模块。

未启动编辑器界面、PIE 或游戏，未进行穿戴／动画／视觉验收。头型贴合、羽饰摆动和游戏光照下的效果由用户试玩确认。

## 按标准接入后的使用入口

重新进入试玩后，在 **F6 开发面板 → 物品 → 装备 → 头部装备 → 野行翎羽帽** 领取，通过现有背包装入头部槽。定义 ID 为 `ue_ranger_feather_hat`，占格 2×2；不自动改写玩家背包或增加掉落表。

- 领取：`ColdSteelDevelopmentTools::ItemCatalog` 从现有物品目录读取，按 `equipment` 与“头部装备”自动归类。
- 穿戴：`FPSPlayerHeadEquipment` 读取本物品配方，异步加载并挂到 Jason 的 `head` 骨；沿既有显隐与头发恢复规则处理。开放式帽子不添加第一人称视野遮罩。
- 羽饰：使用既有 `FPSHeadEquipmentMeshComponent` 三骨局部弹簧，帽体保持固定。
- 图标：家族 PNG、根目录缓存 PNG、UE UI Texture、独立静态展示网格四项已保存并引用。
- 拾取：`ColdSteelPickupConsumable::BuildConsumable` 的 equipment 分支读取 `world_mesh`，以真实包围盒设置已有物理根；沿现有丢弃、对准拾取与存档事务。
- 打包：`DefaultGame.ini` 已覆盖 `/Game/Characters/ModularOutfit20260924`；`FPSGAME.Build.cs` 已将 `Content/ColdSteelData/...` 声明为 UFS 运行依赖，无需追加重复规则。本轮未运行打包。

本次完成说明文案与正式接入记录，使用已保存的同一版模型，不重建几何或启动试玩。数据与资源就绪不代表已完成游戏、动画或联机验收。
