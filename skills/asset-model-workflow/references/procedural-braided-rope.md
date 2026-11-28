# 程序化麻绳：复用马车与仓库的绳索材质和平滑扫掠

**第一条（FPSGAME）　文件位置与引用路径。** 从[制作目录与功能索引](../../../Docs/Production/README.md)和[存储规则第 4.1 节](../../../WORKFLOW.md#41-存储分配与文件操作边界)查找功能入口，再确定制作源、正式资产与输出位置；交付时在同一功能条目登记位置和恢复版本。

## 材质

绳索槽统一绑定 `/Game/WorldGeneration/TemperateHills/VillageStable/PropsR43/Materials/M_StableWeatheredRope`（2K `T_StableRope` BaseColor / NormalDX / ORM）。马车、仓库、伐木场和机械工坊都在用。旧的 `VillageWindmill/MI_Prop_Rope_All_Windmill` 在部分宿主中显示为白模，新资产不再使用。为什么：只维护一份绳索材质，换宿主或重新导入后不会退回白模。

## 几何

参考 [props_geom.py::rope_braid](../../../Tools/WorldGeneration/VillageStable/PropsR43/props_geom.py) 与工坊的 [`braided_rope_sweep()`](../../../SourceAssets/HillsVillageHighWall20261120/GarrisonWorkshop/author_workshop.py)：

1. 曲线按弧长重采样（盘绳 `1.6–2.4 cm`，长缠绕 `9–12 cm`），使用平行移动（Bishop）坐标系，不用 Frenet 坐标系。为什么：Frenet 坐标系在曲率接近 0 时会翻转，扫掠体会出现扭结。
2. 截面 12 点。三股绞合用 `1 + a·cos(3θ)`，近景盘绳 `a≈0.09`、扭距 `≈18 cm`；紧密缠绕在鼓上的绳子用圆截面、不扭转，绳匝的起伏就足够表现纹理。
3. **逐顶点法线取径向（截面偏移方向的单位向量），不用面法线。** 为什么：手写网格器默认每个三角形一个法线，绳子会显得多棱角、像纸花；三叶截面加上大扭转还会产生尖刺。
4. UV：U = 弧长 / 22 cm，V = 截面周长 / 22 cm，与 `props_geom` 的 `uv_scale_override=0.22` 一致。
5. 缠绕两端在 3 个采样点内平滑收进鼓芯（`r - 3.6·t²`），不另外拉直线引出段。

## 预算

工坊家具（盘绳加 20 匝绞盘缠绳）合计约 `25k` 三角形。近景复杂道具允许，按[用途预算](geometry-budgets-by-use.md)执行，不为降面数牺牲平滑法线。
