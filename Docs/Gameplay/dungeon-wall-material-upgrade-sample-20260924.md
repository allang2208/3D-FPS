# 地牢墙面升级：第一批样板

2026-09-24，接续 [墙面检查与升级方案](dungeon-wall-material-upgrade-plan-20260924.md)。第一批完成候选制作、导入、着色器构建及独立样板地图保存；用户随后确认继续，现已[接入正式地牢并保存](dungeon-wall-material-release-20260924.md)。未运行游戏或生成验收截图。

## 查看位置

在 UE 内容浏览器打开：

`/Game/Dungeons/WallUpgrade20260924/Preview/L_WallMaterialComparison`

| 分组 | 内容 |
| --- | --- |
| A_ORIGINAL | 现有通道和升级前材质副本，使用目录中的暖色灯参数 |
| B_UPGRADE | 同一通道模型，绑定候选材质，同样的暖色灯参数 |
| C_ORIGINAL_SIDE_LIGHT | 升级前材质副本，额外加入侧光用于观察表面 |
| D_UPGRADE_SIDE_LIGHT | 候选材质，使用与 C 相同的侧光 |

关卡另有四种表面的旧/新材质板，便于查看通道中没有使用的破损截面。

在世界大纲搜索 `Overview` 并 Pilot 可查看总览；搜索 `B_UPGRADE_Upper_55cm` 查看新版主墙近景，`B_UPGRADE_Mortar_55cm` 查看新版砂浆。`A_` 为对应旧版，`C_`/`D_` 为侧光对照。还保存了约 150cm、285cm 的机位以及 `Boards_AllSurfaces` 材质板机位。距离为镜头到墙面的设计垂直距离。

这些是可供用户查看的预设机位，尚未实际拍摄。样板复用了正式目录中的通道部件和灯参数，但采用统一固定曝光，不能当作正式地牢所有运行时灯光与后处理的完整复现。

## 已制作的表面

- **主墙**：引入 Poly Haven 的 Plastered Wall 扫描，保留对应的颜色、DX 法线、粗糙度/AO 和高度。颜色调整为旧工业空间的冷灰色；主体为 4K，按 200cm 尺寸投影。
- **剥落砂浆和残胶**：使用同组扫描数据的独立配色与 2K 派生图，分别设置 96cm/110cm 尺寸、0.26cm/0.08cm 高度范围与不同颗粒强度。整体结构来自扫描，局部细颗粒来自单独的细节层。
- **毫米级颗粒**：制作 1K、32cm 物理覆盖的周期纹理，包含大小不同的棱角砂粒和不规则小孔。由物理高度求法线，并配套粗糙度及轻微色差；使用同一投影基底进行重定向法线混合。
- **Fab 破损截面**：继续使用 Angled Concrete Wall Section with Heavy Damage 的原始扫描裁片，重新合成 2K 衍生图。候选取样对红色残留、异常边缘和暗区进行惩罚，使用宽重叠权重混合、偏色处理和法线重新归一化。原扫描没有高度图，因此此材质关闭 POM，保留扫描法线并加入细粒层；没有从颜色伪造高度。

本版有两个母材质、四个实例、13 张导入纹理。材质和来源位于独立目录。正式接入保留原有材质路径：主墙入口追加新版材质图，六个实例入口继承新版实例；正式模型的材质槽、地牢目录和原地图未改。主墙包含水平面的原混凝土纹理分支，用于维持壳体水平面的既有表面。样板 A/C 及旧材质板已单独绑定升级前副本，继续保留旧/新对照。

## 制作与性能范围

细节纹理按距离和屏幕纹素覆盖衰减，远处降低颗粒闪烁风险；在衰减结束后通过分支跳过细节采样。浅层 POM 上限为 8 次步进和 2 次细化，约 1.8–5m 衰减。纹理继续使用流送，没有修改项目纹理池、光追或 Lumen 设置。

后台 D3D12/SM6 材质构建记录：主墙母材质 468 条像素指令、10 个采样器；矿物母材质 422 条像素指令、7 个采样器。这些是编译统计，不是实机性能测量，也不代表实际采样次数。此次有增加着色成本，正式推广时应结合用户对近景效果与运行流畅度的反馈决定参数取舍。

后台导入、构建和保存已执行，不止交付脚本。没有主动打开交互编辑器、运行 PIE、截图或进行游戏测试。用户确认继续后，已完成正式材质入口和后续导入流程的接入；实际外观仍由用户自行测试。

## 来源与制作记录

- 扫描来源：[Poly Haven — Plastered Wall](https://polyhaven.com/a/plastered_wall)，作者 Amal Kumar；[CC0 许可](https://polyhaven.com/license)。原图、下载地址及摘要保存在 [来源记录](../../SourceAssets/DungeonWallUpgrade20260924/Sources/PolyHaven/provenance.json)。
- 指定 Fab 素材沿用项目现有采购缓存及 [来源记录](../../SourceAssets/DungeonWallDamage20260923/Sources/provenance.json)。本地游戏使用，未公开发布原图或衍生素材包。
- [贴图制作记录](../../SourceAssets/DungeonWallUpgrade20260924/Authored/materials.json)
- [材质导入与编译回执](../../SourceAssets/DungeonWallUpgrade20260924/Receipts/material-install.json)
- [样板地图保存回执](../../SourceAssets/DungeonWallUpgrade20260924/Receipts/sample-map.json)
- [旧版与候选对应表](../../SourceAssets/DungeonWallUpgrade20260924/Config/material-candidates.json)
- [贴图制作脚本](../../SourceAssets/DungeonWallUpgrade20260924/Scripts/author_textures.py)、[材质导入脚本](../../SourceAssets/DungeonWallUpgrade20260924/Scripts/install_materials.py)、[样板制作脚本](../../SourceAssets/DungeonWallUpgrade20260924/Scripts/build_sample_map.py)
