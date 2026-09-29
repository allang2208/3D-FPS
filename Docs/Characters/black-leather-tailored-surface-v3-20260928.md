# 黑色皮革手套 V3：材质分区与柔软腕口

剩余缝制与使用细节的收尾见 [V4 制作记录](black-leather-stitch-wear-v4-20260928.md)。本页保留 V3 制作与保存历史。

用户在 V2 后要求继续优化。本轮针对皮革、织物与抓握区域的区别，以及腕口厚薄和局部压缩制作。物品仍为 `ue_field_gloves_black`。

## 本轮修改

- 在母版解剖空间中生成接触遮罩，依据每根手指局部掌向、骨段权重及掌心位置区分指腹、掌面和手背；不以整只手统一平面把指侧误当作指腹。
- 皮革主体降低短绒量，保留细颗粒；织物、缝线与包边集中呈现短纤维。腕口绒面遮罩沿各模型真实切口生成，Body 不再依赖第一人称腕口的固定坐标。
- 掌心和指腹降低颗粒、法线微起伏与粗糙度，并略微压深颜色，形成柔和的使用抛光；手背护垫及针脚仍保留原设计。没有使用统一的亮色噪点覆盖整个表面。
- 腕口背侧设计厚度约 3.2 mm，内腕约 1.7 mm，两侧局部进一步压缩约 9–14%；轮廓加入不足 0.5 mm 的轻微不齐，避免均匀圆环外形。
- 腕部厚度在约 25 mm 范围收薄，并添加局部实体压褶。包边端面和内回折同步跟随各处厚度，全部继承对应原生腕口权重。
- 保留原掌心、指腹与指缝的几何接触范围；继续复用现有骨架和动画。没有为此新增动作、模拟或运行时逻辑。
- 使用同一新版网格与材质重做掉落模型及 320×320 透明物品图标，装备栏、背包和仓库共用同一图标路径。

## 制作与成本

作者源：`SourceAssets/BlackLeatherDetail20260928/TailoredSurfaceV3/`。

UE 资产目录：`/Game/Characters/ModularOutfit20260924/BlackLeatherTailoredSurfaceV3/`。

图标路径：`Content/ColdSteelData/Icons/BlackLeatherTailoredSurfaceV3/ue_field_gloves_black.png`。

复用 V2 的 4 张纹理和浅层 POM 材质框架，保持颜色/法线/ORM/高度共用偏移 UV、接缝淡出、6 次粗步进与 2 次细化。第一人称 4K，Body 2K，贴图流送与 mip 保留。本轮不增加材质槽、运行时纹理数量或三角面数；双手 25,166、单手 12,583、Body 26,824 三角面，三级 LOD。

生成顺序：

1. `Tools/ModularOutfit/black_leather_tailored_surface.py`：22 套原生源、腕口形体和材质分区遮罩。
2. `build_black_leather_tailored_surface.py`：高模、烘焙、游戏母版、掉落 FBX 与正式图标。
3. `finish_black_leather_tailored_maps.py` 与 `author_black_leather_tailored_family.py`：视差接缝遮罩、原生装备派生。
4. `import_black_leather_tailored_surface.py`：实际导入保存、更新现有物品引用。

上一版 V2 源与资产保留。开始制作时读取并保留当前黑色手套配方；接入时重新读取物品表，仅更新本物品的外观和图标字段。

## 接入记录

后台 commandlet 已完成导入并以退出码 0 结束，日志记录 `BLACK_LEATHER_DETAIL_PUBLISHED ue_field_gloves_black 22`。本轮保存 22 个骨骼网格、8 张贴图、2 个材质和 1 个掉落网格，共 33 个 UE 资产；现有物品的外观配方、掉落引用、说明和统一图标路径已更新。

保存回执为作者目录 `published.json`，导入日志为 `Saved/black-leather-tailored-surface-v3-import-20260928.log`。资产保存与游戏表现分别记录。

本轮不主动启动 UE 交互编辑器、游戏、预览或验收测试。实际光照、抓握和与上衣搭接效果由用户测试。
