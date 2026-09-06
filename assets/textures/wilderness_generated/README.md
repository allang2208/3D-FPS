# 旷野新地表贴图 · 2026-09-06

使用 Codex 内置 image_gen 生成，用户本轮授权生成并接入。原图保存为 `turf_albedo_v1.png`（草皮）和 `loam_albedo_v1.png`（棕色泥土）。

`*_alb_ht_v1.png` 由 `tools/prepare_wilderness_textures.gd` 适配现有 Terrain3D 数组：放大到原数组的 4096×4096 尺寸，alpha 为中性高度 0.5。放大只用于格式一致，不代表新增 4K 细节。原图保持原样。

v1 生成的是颜色贴图，最初法线、粗糙度沿用已有 grass004 / ground020。下面 v2 已改为同源推导，不能把 v1 的配置理解为当前默认配置。

## v2 材质调校

`tools/refine_wilderness_maps.gd` 从保留的 v1 原图构造 1024 方形工作图，对两对边缘羽化，并从去除大范围亮度变化后的细节推导高度、法线和粗糙度。颜色 alpha 存高度，法线 alpha 存粗糙度；全部开启 mipmaps。它们是同源的艺术近似，不是实测 PBR 或真实几何重建。4096 版本只用于兼容已有 Terrain3D 数组，不增加原图细节。

当前默认由 `scripts/wilderness_materials.gd` 的 refined 配置控制：保留下载材质的 grass004、gravel041、rock063，挖掘泥土和河岸泥沙采用 loam v2。第二轮实机隔离水面后确认 ground092c 的粗沙纹造成河床条纹，因此河岸改为细泥沙，并单独校准亮度与凹凸强度；原河岸湿度图继续控制干湿过渡。生成草皮保留用于对照，当前光照下偏暗且近景纹理偏密，因此没有选为默认。

Terrain3D 和挖掘曲面共用草、土、岩的纹理尺度。挖掘面颜色与法线使用相同的双偏移采样，减少重复；原地表混合边缘加入小幅噪声，纯材质区域不受此操作影响。

运行 `tests/review_wilderness_materials.gd` 可重拍固定机位。环境变量 `WILDERNESS_MATERIAL_VARIANT` 支持 baseline（优化前生成颜色+旧法线）、existing（调校下载材质）、generated（调校生成材质）、refined（当前混合选择）。不设置变量时使用 refined。

## 最终生成提示词

### 泥土

Use case: photorealistic-natural. Asset type: seamless tileable game terrain albedo texture, square 1024x1024. Produce a single full-frame uniform overhead orthographic scan of freshly excavated brown loam earth, medium warm umber and ochre brown, crumbly small soil clods, fine grains and a few tiny muted pebbles. This texture will be triplanar mapped on excavated walls and floors beneath green turf in a realistic wilderness Godot game. Clearly brown soil throughout, absolutely no grass, moss, green hues, plants, roots, large stones, scene horizon, text, borders, lighting gradients or directional cast shadows. Even neutral diffuse illumination, matte dry to slightly damp soil, moderate microdetail, no large recognizable repeating features. Match opposite edges as a seamless tile. This is the diffuse color texture only, not a material sphere preview or multi-map atlas.

### 草皮

Use case: photorealistic-natural. Asset type: square 1024x1024 seamless tileable wilderness turf albedo for a realistic Godot terrain. Single uniform full-frame orthographic top-down ground surface scan: short fine muted olive green meadow grass, compact irregular tiny tufts with subtle earthy brown soil visible between blades, natural restrained low-saturation greens. Even diffuse neutral flat lighting, no directional cast shadows or bright highlights. Moderately detailed grass surface, not tall grass, no flowers, trees, leaves, horizon, borders, writing, labels or material sphere. Not fluorescent green and not whitish washed out. Small-scale spatially even details and perfectly matching opposite edges, no large repeating focal feature. Output only the diffuse color texture, no atlas or normal map.
