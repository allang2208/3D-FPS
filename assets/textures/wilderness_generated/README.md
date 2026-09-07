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

## GPT image 第二组写实候选

2026-09-06 使用 Codex 内置 image_gen 生成两轮草土混合候选与 `colluvium_albedo_gptimage2_v1.png`。固定机位发现第一轮草丝过密偏黄，第二轮虽增加泥土占比并压暗颜色，仍有细线网状感，因此两轮草皮均淘汰，源图和派生贴图已从正式仓库清理，默认继续使用摄影 PBR 草地；下方提示词与失败结论保留，后续可按同一约束重新生成。坡积碎石 v1 通过候选筛选并接入陡坡/山脚，仓库保留其原图与 Terrain3D 使用的 4096 颜色/高度、法线/粗糙度组合贴图；未引用的 1K 派生副本不保留。推导通道仍是艺术近似，未来可由 5080 本地 Material Maker/摄影测量结果按同名版本替换。

### 坡积碎石提示词

Use case: stylized-concept. Asset type: seamless tileable game terrain albedo source for Godot Terrain3D. Primary request: photorealistic temperate mountain slope colluvium, compact brown-gray loam mixed with many small angular slate and granite fragments, sparse dry moss and occasional tiny grass threads. Straight-down orthographic capture, uniform edge-to-edge material sample, diffuse neutral overcast reference lighting, no directional light or baked shadows. Centimeter-scale gravel, restrained gray-brown and muted olive palette. Seamless matching edges, no large rocks, footprints, paths, leaves, flowers, text, logos, borders or watermark.

### 草土混合提示词

Use case: stylized-concept. Asset type: seamless tileable game terrain albedo source for Godot Terrain3D. Primary request: photorealistic temperate wilderness meadow ground, short mixed green grass interwoven with small patches of dark moist loam, tiny dried blades and subtle natural color variation. Straight-down orthographic capture, uniform edge-to-edge material sample, diffuse neutral overcast reference lighting, no directional light or baked shadows. Restrained desaturated greens and earth browns, seamless matching edges, no large stones, flowers, leaves, footprints, paths, text, logos, borders or watermark.

## 5080 / ComfyUI 与 GPT Image 共用入口

本地 5080 不需要另一套游戏接入代码。ComfyUI、Stable Diffusion 或其它本地工作流只需输出一张正方形 PNG 原始颜色图；建议 1024 或 2048、正交俯拍、无烘焙方向光、无地平线/大物件/文字，文件名带生成器和版本，例如 `mossy_bank_5080_v1.png`。先把它放入本目录，再运行：

```powershell
godot --headless --path E:\3d\3-dfps --script res://tools/build_wilderness_pbr_candidates.gd -- --source=mossy_bank_5080_v1.png --output=mossy_bank_5080_v1 --normal-strength=2.8 --roughness=0.9 --height-gain=1.6
```

也可以把 `--source` 指向绝对路径。脚本会保留原图，输出 1K 与 Terrain3D 数组兼容的 4096 组合图。候选必须再用 `tests/review_wilderness_materials.gd` 的固定机位检查近景、远景和混合边缘，通过后才在 `scripts/wilderness_materials.gd` 注册；新增材质不需要修改地形公式核心。

如果 5080 工作流能直接生成同源 height、normal、roughness，应优先保留这些真实分图并另做通道打包，不使用本脚本的亮度推导近似。GPT Image 适合快速探索颜色与地貌语言；5080 适合批量出变体、固定 seed 和 ControlNet 约束。两者都只作为候选生产端，共用同一筛选、版本和运行时接口。
