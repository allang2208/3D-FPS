# 2K 矢量魔法阵、写实寒冰晶柱与 Niagara 避坑规范（2026-11-27）

**第一条（FPSGAME）　文件落盘与引用路径。** 先查[制作目录与功能索引](../../../Docs/Production/README.md)与[存储规则第 4.1 节](../../../WORKFLOW.md#41-存储分配与文件操作边界)。工程资产引用使用 `/Game/...`，制作脚本从工程根或已配置制作源拼接相对路径；交付时在同一功能条目登记制作源、正式包、发布回执与备份位置。

---

## 1. 2K 4 通道矢量法阵规范（`ArcaneCirclesV3` 范式）

纯极坐标数学（`abs(r-const)` + `pow(cos, N)`）在近景贴脸或大半径贴地时线条粗糙、重复感强，且环形背景雾极易发糊。高精细法阵统一采用 **4K 超采 → Lanczos 2048×2048 4 通道线性 BC7 矢量贴图 + 分带随层辉光**：

- **贴图导入铁律**：
  - `srgb = False`、`compression_settings = TC_BC7`、`address_x/y = TA_CLAMP`（防旋转采样边沿漏色）、`filter = TF_TRILINEAR`、`mip_gen_settings = TMGS_SHARPEN2`、`lod_group = TEXTUREGROUP_EFFECTS`、`max_texture_size = 2048`。
  - **必须开启 `never_stream = True`**：雷枪蓄力（`0.5–1.5 s`）与绝对零度蓄寒（`1.1–1.5 s`）持续时间短，默认流送会导致首帧从低级 mip 渐进加载、前 `0.3–0.6 s` 糊掉；开启 `never_stream = True`（单张 2K BC7 约 `4 MB` 显存）确保第 0 帧满清锐利。
- **4 通道径向分带与零重影辉光**：
  - `R`：外圈星盘刻度、主几何星冠与角饰勋章（顺转）；跨过符文带的几何连弦压细降亮，避免与符文打架。
  - `G`：独立手绘互不重复符文带（`24–32` 枚精雕古符文 + 装饰分隔符，逆转）。
  - `B`：内圈净空边沿微雕花边与瞄准/方位括弧（微旋或呼吸缩放）。
  - `A`：**按径向分带隔离的贴线紧致高斯微辉 + 勋章星点**（清除一切大范围均匀糊雾）。HLSL 仅需 `3` 次 `Texture2DSample`（外/符文/内三组旋转 UV），每层同时读取自身通道与对应径向段的 `.a`，实现正反三层独立旋转时辉光严格随层、**零重影**。
- **严格中心净空与动态表现**：
  - 2K 下采样后对中心净空半径内（如雷枪 `r < 0.565`、绝对零度 `r < 0.485`）二次硬清零，消除 Lanczos 振铃渗漏；HLSL 外沿乘 `step(r, 0.994)` 防旋转裁角。
  - 加入蓄力/进度逐字顺序点亮、双螺旋能量电流脉动、白热核心描边与 `(Time + ColorSeed)` 驱动的蓝/紫/青无重复随机色游走（联机通过复制种子如 `NetSigilColorSeed` 同步，地面点光与发射激波 `MuzzleIrisMID` 同写 `ColorSeed` 避免色相跳变）。
- **3D 全息双层视差实测缩放**：
  - 复用既有网格（如 `SM_ThunderLanceIris`）作纵深副阵前，必须先读 `get_bounds()` 实测单位半径（`SM_ThunderLanceIris` 为 `1.0 cm`，而 `/Engine/BasicShapes/Plane` 半宽 `50 cm`）。按距镜头深度比（`82 / 66 cm`）放大约 `1.07×`（`46.5→52.0 cm`），才能让副阵净空口严格留在主阵瞄准窗之外，同时获得真实 3D 视差。
- **贴地大半径法阵细分**：
  - `FrostSurfaceMesh::BuildConformingDisc` 半径达 `5.2 m` 时，细分需至少 `64×9`（函数内部限幅 `NumAngles ∈ [16, 72]`、`NumRings ∈ [3, 20]`）以消除地形折线感。

入口参考：`Tools/Skills/generate_arcane_circle_textures_v3.py`、`Tools/Skills/author_arcane_circles_v3_20261127.py`、`SourceAssets/AbsoluteZeroV2_20261126/AbsoluteZeroSigil.hlsl`、`SourceAssets/ThunderLanceRay20261005/Authoring/LanceIris.hlsl`。

---

## 2. UE 5.8 寒冰/粒子 VFX 与 ISM 材质避坑（`AbsoluteZero V4` / `IceWall V5` / `IceSpike V3`）

- **`DepthFade` 引脚名陷阱（方块粒子根因）**：
  - UE 5.8 `MaterialExpressionDepthFade` 的输入引脚名是 **`'Opacity'`**（不是 `'InOpacity'`）；使用错引脚名静默断连后，粒子材质会退化成全幅不透明灰方块。连接引脚优先按 `get_material_expression_input_names(node)[0]` 取名并校验返回值为 `True`。
- **ISM 标志与无锁新建版本**：
  - 任何供 `UInstancedStaticMeshComponent` 使用的冰柱/冰锥/碎冰材质必须显式开启 `MATUSAGE_INSTANCED_STATIC_MESHES`；否则回退默认材质或发灰土褐。
  - 不要直接覆写已被旧蓝图/怪物 CDO（如 `M07MagicAttack`）引用的历史坏材质或旧粒子，保留旧包并新建独立版本资产（`M_IceSpikeHeartV3`、`M_AbsoluteZeroIceDust`、`NS_FrostCrystalsV2`）。
- **写实解理冰晶造型与双层材质**：
  - 雕冰体不要套体素重网格或大面积平滑（会发圆发塑）；使用平面解理切割 + `~4 mm` 微倒角 + `20°–28°` 锐边分离法线 + 底面归零（`Z=0`）与 `-15 cm` 贴坡裙边，烘焙 `R/G/B/A` 曲率/积霜/凹谷/高度顶点色并以 `VertexColorImportOption.REPLACE` 导入，顺手生成 3 级静态网格 LOD（`100% / 50% / 22%`）。
  - 主体冰柱采用「世界空间三向投影不透明深寒冰芯（`IOR=1.31` 折射 + 3 层视差裂纹，避免暮光自发光发粉洗白）+ 略外扩 `1.012–1.032×` 半透光泽外晶壳（`TLM_SURFACE_PER_PIXEL_LIGHTING`，`42 m` 裁剪）」；碎冰爆散用真实 3D 翻滚 `InstancedStaticMesh` 替代 2D 纸片。
- **贴地建网与联机性能边界**：
  - 静止驻场或坍塌结束后的 ISM 停止每帧重传实例缓冲；伴生副刺复用主柱地面射线高度可省 ~60% 首帧射线；`FrostSurfaceMesh` 在 `Caster == nullptr` 时仍走世界射线贴地挡墙，保证远端或晚入场副本正确贴合地形。
  - `NM_DedicatedServer` 拦截纯表现组件（冰墙冷雾、绝对零度蓄寒法阵/点光等）；蓄寒组件按需开关 Tick 并缓存脚下地面射线结果。

入口参考：`Tools/Skills/author_absolute_zero_v3_meshes.py`、`Tools/Skills/author_absolute_zero_v3_assets.py`、`Tools/Skills/author_ice_wall_glacial_v5_meshes.py`、`Tools/Skills/author_ice_wall_v5_and_spike_color_fix_20261127.py`、`Tools/Skills/author_frost_polish_and_lods_20261127.py`。
