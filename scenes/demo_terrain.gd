extends Node3D

# 地形演示场景：Terrain3D + 免费 CC0 资产（Poly Haven 热带岛树/岩石、Kenney 灌木草石、AmbientCG 地表纹理、HDRI 天空）

const WorldLighting := preload("res://scripts/world_lighting.gd")
const PREP_TEX := "res://assets/textures/terrain_prepared/%s_%s.png"
const DATA_DIR := "res://assets/terrain_data/demo"
const NpcConfig := preload("res://ui/npc_config.gd")
const NpcPanels := preload("res://ui/npc_panels.gd")
const WeaponFormula := preload("res://ui/weapon_formula.gd")
const GameplayPlayerFactory := preload("res://scripts/gameplay_player_factory.gd")

var terrain: Terrain3D
var rng := RandomNumberGenerator.new()
var _player: Node3D
var _status_bar: CanvasLayer
var _npc_bar: CanvasLayer
var _item_db
var _backpack
var _equipment
var _economy
var _warehouse
var _panels := {}
var _player_status: RefCounted
var _backpack_hud: Control
var _meadow_noise := FastNoiseLite.new()  # 草甸斑块掩码：控制草类疏密分布
var _tree_cache := {}  # 树模型路径 -> {"base": scale=1 底座偏移, "size": 包围盒尺寸}
var _hud_retries := 0  # HUD 桥接重试计数：backpack 未就绪时有限重试，避免无限 call_deferred 递归崩溃

func _ready() -> void:
	rng.seed = 20260809
	_meadow_noise.seed = 991
	_meadow_noise.noise_type = FastNoiseLite.TYPE_PERLIN
	_meadow_noise.frequency = 0.006
	_meadow_noise.fractal_octaves = 2
	_build_environment()
	_build_light()
	terrain = _build_terrain()
	_build_instanced_nature()
	_build_landmark_rocks()
	_build_river()
	_build_ambience()
	_build_particle_grass()
	_build_trees()
	_build_player()
	_build_hud()
	_build_return_portal()
	_build_mouse_king()
	print("[demo_terrain] scene ready")

func _build_environment() -> void:
	add_child(WorldLighting.create_environment())

func _build_light() -> void:
	add_child(WorldLighting.create_sun())


## 河流中心线 Z 坐标：高度生成/水面网格/睡莲水草共用此公式，改河道只改这里
func _river_center_z(wx: float) -> float:
	return 40.0 * sin(wx / 90.0)


## Procedural colormap, 1:1 with the heightmap (1024x1024, RGBA8).
## RGB multiplies in the Terrain3D shader (darken-only), so keep it near white
## with gentle tints: warm tan on the riverbed, fresh green on the grass,
## cool grey-green on rocky/high patches. Alpha is the wetness channel
## (0.5 = neutral); the river corridor gets ~0.34 = -30% roughness so banks
## read as wet mud/glossy, per the official "mud" recipe.
func _build_colormap() -> Image:
	var cm := Image.create_empty(1024, 1024, false, Image.FORMAT_RGBA8)
	var tint_noise := FastNoiseLite.new()
	tint_noise.seed = 20260810
	tint_noise.noise_type = FastNoiseLite.TYPE_PERLIN
	tint_noise.frequency = 0.014
	tint_noise.fractal_octaves = 3
	var patch_noise := FastNoiseLite.new()
	patch_noise.seed = 777
	patch_noise.noise_type = FastNoiseLite.TYPE_PERLIN
	patch_noise.frequency = 0.0045
	patch_noise.fractal_octaves = 2
	for x in cm.get_width():
		for y in cm.get_height():
			var wx := x - 512.0
			var wz := y - 512.0
			var cz := _river_center_z(wx)
			var dist := absf(wz - cz)
			var patch := patch_noise.get_noise_2d(x, y)
			var rgb := Color(0.94, 0.97, 0.90)
			# Lake basin widens the corridor tint west of x=-350 (same as heightmap)
			var tint_r := 70.0 + maxf(0.0, lerpf(0.0, 90.0, clampf((-350.0 - wx) / 80.0, 0.0, 1.0)))
			if dist < tint_r:
				# River corridor: warm tan bed fading into damp bank green.
				var edge := clampf(dist / tint_r, 0.0, 1.0)
				rgb = Color(0.88, 0.84, 0.76).lerp(Color(0.90, 0.95, 0.86), edge)
			elif patch > 0.28:
				rgb = Color(0.90, 0.92, 0.84)  # warm sunlit patch
			elif patch > 0.08:
				rgb = Color(0.92, 0.95, 0.89)  # warm-green mid patch
			elif patch < -0.28:
				rgb = Color(0.84, 0.88, 0.86)  # cool mossy patch
			elif patch < -0.08:
				rgb = Color(0.91, 0.94, 0.90)  # cool-green mid patch
			var v := tint_noise.get_noise_2d(x, y) * 0.055
			rgb = Color(
				clampf(rgb.r + v, 0.76, 1.0),
				clampf(rgb.g + v, 0.76, 1.0),
				clampf(rgb.b + v, 0.76, 1.0))
			var wet := 0.5
			var wet_r := 16.0 + maxf(0.0, lerpf(0.0, 40.0, clampf((-350.0 - wx) / 80.0, 0.0, 1.0)))
			if dist < wet_r:
				wet = 0.30
			elif dist < wet_r * 2.0:
				wet = lerpf(0.30, 0.5, (dist - wet_r) / wet_r)
			cm.set_pixel(x, y, Color(rgb.r, rgb.g, rgb.b, wet))
	return cm


func _build_terrain() -> Terrain3D:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DATA_DIR))
	var t := Terrain3D.new()
	t.name = "Terrain3D"
	add_child(t)
	t.data_directory = DATA_DIR
	t.material.auto_shader = true
	t.material.world_background = Terrain3DMaterial.NONE
	t.material.dual_scaling = true
	t.material.set_shader_param("auto_slope", 0.35)
	t.material.set_shader_param("blend_sharpness", 0.85)

	t.assets = Terrain3DAssets.new()
	# 地表纹理集：草(001/004/005/007)、森林落叶土(020)、碎石地(030)、
	# 泥土(037)、沙(080)、岩(063)。uv_scale 越小纹理越大。
	var tex_ids := ["grass001", "grass004", "grass005", "grass007",
		"ground020", "ground030", "ground037", "ground080", "rock063",
		"ground106", "ground092c",
		"scatteredleaves008", "gravel041"]
	var uv_scales := [0.08, 0.08, 0.09, 0.09, 0.08, 0.06, 0.08, 0.06, 0.05, 0.07, 0.07, 0.06, 0.05]
	for i in tex_ids.size():
		var ta := Terrain3DTextureAsset.new()
		ta.name = tex_ids[i]
		ta.albedo_texture = load(PREP_TEX % [tex_ids[i], "alb_ht"])
		ta.normal_texture = load(PREP_TEX % [tex_ids[i], "nrm_rgh"])
		# 参考图地面更"厚实"：法线强度略提、AO 更强，配合新 alpha 高度混合
		ta.normal_depth = 1.5
		ta.ao_strength = 2.5
		ta.uv_scale = uv_scales[i]
		ta.detiling_rotation = 0.12
		t.assets.set_texture(i, ta)

	# 地形数据缓存：region 文件已落盘时直接加载，跳过 2×1M 像素的 GDScript 重建
	# （高度图 + colormap 各 1024² 循环 + 噪声采样），传送门来回不再卡。
	# 生成器是确定性的（种子固定），缓存与程序化重建数据完全一致，画面零变化。
	t.region_size = Terrain3D.RegionSize.SIZE_256
	var data_dir_abs := ProjectSettings.globalize_path(DATA_DIR)
	var region_files: Array[String] = []
	if DirAccess.dir_exists_absolute(data_dir_abs):
		for f in DirAccess.get_files_at(data_dir_abs):
			if f.ends_with(".res"):
				region_files.append(f)
	if region_files.size() > 0 and t.data.has_method("load_directory"):
		t.data.load_directory(DATA_DIR)
		print("[terrain] loaded %d cached region file(s), skip heightmap rebuild" % region_files.size())
	else:
		# 程序化高度图：低频山体 + 高频微起伏（避免地面过平），
		# 并沿蛇形路径刻一条溪流河道（低洼带，供后续水体 shader 使用）
		var macro := FastNoiseLite.new()
		macro.noise_type = FastNoiseLite.TYPE_PERLIN
		macro.frequency = 0.004
		macro.fractal_octaves = 4
		macro.fractal_gain = 0.5
		var micro := FastNoiseLite.new()
		micro.noise_type = FastNoiseLite.TYPE_PERLIN
		micro.frequency = 0.035
		micro.fractal_octaves = 2
		var img := Image.create_empty(1024, 1024, false, Image.FORMAT_RF)
		for x in img.get_width():
			for y in img.get_height():
				var wx := x - 512.0
				var wz := y - 512.0
				# 平缓起伏草甸：宏观 ±8m + 高频微起伏 ±1.5m（实际米，除以 import scale=45）
				var macro_m := macro.get_noise_2d(x, y) * 8.0
				var micro_m := micro.get_noise_2d(x, y) * 1.5
				var h := (macro_m + micro_m) / 45.0
				# 溪流河谷：走廊内地形平滑降到一条缓坡河床（西 -8m → 东 -12m），
				# 水面全程连续、两侧缓坡抬升回草甸，杜绝“碎水面悬浮”
				var cz := _river_center_z(wx)
				var dist := absf(wz - cz)
				# Downstream valley widens into a lake basin (R 55 -> 150 west of x=-350)
				var R := 55.0 + maxf(0.0, lerpf(0.0, 95.0, clampf((-350.0 - wx) / 80.0, 0.0, 1.0)))
				if dist < R:
					var tt := clampf(dist / R, 0.0, 1.0)
					var edge := smoothstep(0.35, 1.0, tt)
					var bed_m := lerpf(-4.0, -7.0, clampf((wx + 430.0) / 860.0, 0.0, 1.0))
					bed_m += micro.get_noise_2d(x + 512, y + 512) * 0.6
					h = lerpf(bed_m / 45.0, h, edge)
				img.set_pixel(x, y, Color(h, 0.0, 0.0, 1.0))
		t.data.import_images([img, null, _build_colormap()], Vector3(-512, 0, -512), 0.0, 45.0)
		t.data.save_directory(DATA_DIR)
		print("[terrain] heightmap rebuilt and saved to region files")
	t.collision.set_mode(Terrain3DCollision.FULL_GAME)  # 全量运行时碰撞（1km 地图性能足够）
	t.collision.build()

	# 植被/岩石 instancer 网格资产（顺序即 instancer id，须与 _build_instanced_nature 的 specs 对应）
	var mesh_specs: Array[String] = [
		"res://assets/models/polyhaven/shrub_02/shrub_02_2k.gltf",
		"res://assets/models/polyhaven/shrub_03/shrub_03_2k.gltf",
		"res://assets/models/polyhaven/shrub_04/shrub_04_2k.gltf",
		"res://assets/models/polyhaven/grass_bermuda_01/grass_bermuda_01_2k.gltf",
		"res://assets/models/polyhaven/grass_medium_01/grass_medium_01_2k.gltf",
		"res://assets/models/polyhaven/grass_medium_02/grass_medium_02_2k.gltf",
		"res://assets/models/polyhaven/flower_gazania/flower_gazania_2k.gltf",
		"res://assets/models/polyhaven/flower_heliophila/flower_heliophila_2k.gltf",
		"res://assets/models/polyhaven/dandelion_01/dandelion_01_2k.gltf",
		"res://assets/models/polyhaven/tree_stump_01/tree_stump_01_2k.gltf",
		"res://assets/models/polyhaven/tree_stump_01/tree_stump_01_2k.gltf",
		"res://assets/models/polyhaven/dead_tree_trunk_02/dead_tree_trunk_02_2k.gltf",
		"res://assets/models/polyhaven/dead_tree_trunk_02/dead_tree_trunk_02_2k.gltf",
		"res://assets/models/kenney_nature/rock_largeA.glb",
		"res://assets/models/kenney_nature/rock_smallA.glb",
		"res://assets/models/polyhaven/grass_medium_01/grass_medium_01_2k.gltf",
		"res://assets/models/polyhaven/grass_bermuda_01/grass_bermuda_01_2k.gltf",
		"res://assets/models/polyhaven/tree_stump_01/tree_stump_01_2k.gltf",
		"res://assets/models/polyhaven/dead_tree_trunk_02/dead_tree_trunk_02_2k.gltf",
		"res://assets/models/polyhaven/fern_02/fern_02_2k.gltf",
		"res://assets/models/polyhaven/leafy_grass/leafy_grass_2k.gltf",
		"res://assets/models/polyhaven/nettle_plant/nettle_plant_2k.gltf",
		"res://assets/models/polyhaven/weed_plant_02/weed_plant_02_2k.gltf",
		"res://assets/models/polyhaven/rock_moss_set_01/rock_moss_set_01_2k.gltf",
		"res://assets/models/polyhaven/searsia_burchellii/searsia_burchellii_2k.gltf",
		"res://assets/models/polyhaven/moss_01/moss_01_2k.gltf",
		"res://assets/models/polyhaven/searsia_lucida/searsia_lucida_2k.gltf",
		"res://assets/models/polyhaven/leafy_grass/leafy_grass_2k.gltf",
		"res://assets/models/polyhaven/wild_rooibos_bush/wild_rooibos_bush_2k.gltf",
		"res://assets/models/polyhaven/fir_sapling/fir_sapling_2k.gltf",
		"res://assets/models/polyhaven/moss_01/moss_01_2k.gltf",
		"res://assets/models/polyhaven/tree_stump_01/tree_stump_01_2k.gltf",
		"res://assets/models/polyhaven/tree_stump_01/tree_stump_01_2k.gltf",
		"res://assets/models/polyhaven/dead_tree_trunk_02/dead_tree_trunk_02_2k.gltf",
		"res://assets/models/polyhaven/dead_tree_trunk_02/dead_tree_trunk_02_2k.gltf",
		"res://assets/models/polyhaven/periwinkle_plant/periwinkle_plant_2k.gltf",
		"res://assets/models/polyhaven/periwinkle_plant/periwinkle_plant_2k.gltf",
		"res://assets/models/polyhaven/island_tree_01/island_tree_01_1k.gltf",
		"res://assets/models/polyhaven/island_tree_02/island_tree_02_1k.gltf",
		"res://assets/models/polyhaven/island_tree_03/island_tree_03_1k.gltf",
		"res://assets/models/polyhaven/shrub_01/shrub_01_2k.gltf",
		"res://assets/models/polyhaven/grass_medium_02/grass_medium_02_2k.gltf",
	]
	for i in mesh_specs.size():
		var scn: PackedScene = load(mesh_specs[i])
		var ma := Terrain3DMeshAsset.new()
		ma.name = "mesh_%02d" % i
		ma.scene_file = scn
		# instancer 按 transform.y + height_offset 摆位：用模型底座偏移补偿，避免悬浮
		var probe: Node = scn.instantiate()
		add_child(probe)
		ma.height_offset = -_scene_aabb(probe).position.y
		# Kenney 低模草是纯色青绿材质（实测 albedo≈(0.45,0.93,0.87)），
		# 与粒子草/地表深绿格格不入——统一覆盖为自然深绿（共享材质全局生效）
		if mesh_specs[i].contains("kenney_nature/grass"):
			_fix_grass_material(probe)
		remove_child(probe)
		probe.free()
		t.assets.set_mesh_asset(i, ma)
	return t

func _fix_grass_material(node: Node) -> void:
	# 草色基准：地面实际渲染色（D3D12 实测 RGB≈(137,172,136)，亮低饱和草绿）
	var grass := Color(0.54, 0.67, 0.53)
	for m in node.find_children("", "MeshInstance3D", true, false):
		var mi := m as MeshInstance3D
		if mi.mesh == null:
			continue
		for s in mi.mesh.get_surface_count():
			var mat := mi.mesh.surface_get_material(s)
			if mat is BaseMaterial3D:
				var bm := mat as BaseMaterial3D
				bm.albedo_color = grass
				bm.roughness = 0.8

func _build_instanced_nature() -> void:
	# [mesh_id, count, lo, hi, h_min, h_max, scale_min, scale_max]
	var specs: Array = [
		[0, 55, -460, 460, -35.0, 24.0, 0.8, 1.4],  # ph shrub_02
		[1, 55, -460, 460, -35.0, 24.0, 0.8, 1.5],  # ph shrub_03
		[2, 55, -460, 460, -35.0, 24.0, 0.8, 1.3],  # ph shrub_04
		[3, 150, -460, 460, -40.0, 30.0, 0.8, 1.4],  # grass
		[4, 140, -460, 460, -40.0, 30.0, 0.8, 1.4],  # grass_large
		[5, 130, -460, 460, -40.0, 30.0, 0.8, 1.4],  # grass_leafs
		[6, 30, -460, 460, -38.0, 26.0, 0.8, 1.3],   # ph flower_gazania
		[7, 30, -460, 460, -38.0, 26.0, 0.8, 1.3],   # ph flower_heliophila
		[8, 30, -460, 460, -38.0, 26.0, 0.8, 1.3],   # ph dandelion_01
		[9, 25, -460, 460, -38.0, 26.0, 0.8, 1.4],   # stump_old
		[10, 25, -460, 460, -38.0, 26.0, 0.8, 1.4],  # stump_round
		[11, 30, -460, 460, -38.0, 26.0, 0.8, 1.4],  # log
		[12, 30, -460, 460, -38.0, 26.0, 0.8, 1.4],  # log_stack
		[13, 70, -460, 460, -42.0, 32.0, 0.6, 1.5],  # rock_largeA
		[14, 70, -460, 460, -42.0, 32.0, 0.6, 1.5],  # rock_smallA
		[15, 45, -460, 460, -40.0, 30.0, 0.8, 1.4],  # ph grass_medium_01
		[16, 45, -460, 460, -40.0, 30.0, 0.8, 1.4],  # ph grass_bermuda_01
		[17, 15, -460, 460, -36.0, 24.0, 0.7, 1.2],  # ph tree_stump_01
		[18, 15, -460, 460, -36.0, 24.0, 0.7, 1.2],  # ph dead_tree_trunk_02
		[19, 130, -460, 460, -40.0, 30.0, 0.5, 1.1],  # ph fern_02 蕨类（林下主体）
		[20, 60, -460, 460, -40.0, 30.0, 0.35, 0.7],  # ph leafy_grass 阔叶草簇
		[21, 90, -460, 460, -40.0, 30.0, 1.3, 2.3],   # ph nettle_plant 荨麻（放大）
		[22, 80, -460, 460, -40.0, 30.0, 1.6, 2.8],   # ph weed_plant_02 杂草（放大）
		[23, 30, -460, 460, -42.0, 28.0, 0.08, 0.16], # ph rock_moss_set_01 青苔石组
		[24, 35, -460, 460, -38.0, 26.0, 1.1, 2.2],   # ph searsia_burchellii 灌木
		[25, 55, -460, 460, -40.0, 28.0, 0.8, 1.3],   # kenney hanging_moss 垂藤丛
		[26, 50, -460, 460, -40.0, 28.0, 0.9, 1.5],  # ph searsia_lucida
		[27, 85, -460, 460, -40.0, 30.0, 0.8, 1.4],   # kenney grass_leafsLarge 大草
		[28, 45, -460, 460, -40.0, 28.0, 0.9, 1.5],  # ph wild_rooibos_bush
		[29, 40, -460, 460, -38.0, 26.0, 1.2, 2.2],   # ph fir_sapling 小针叶树（放大）
		[30, 90, -460, 460, -40.0, 30.0, 1.5, 3.0],   # ph moss_01 地面苔藓斑
		[31, 20, -460, 460, -38.0, 26.0, 0.8, 1.3],   # kenney stump_oldTall
		[32, 20, -460, 460, -38.0, 26.0, 0.8, 1.3],   # kenney stump_roundDetailed
		[33, 20, -460, 460, -38.0, 26.0, 0.8, 1.3],   # kenney log_large
		[34, 18, -460, 460, -38.0, 26.0, 0.8, 1.3],   # kenney log_stackLarge
		[35, 16, -460, 460, -40.0, 26.0, 0.9, 1.4],   # ph periwinkle_plant 岸花
		[36, 16, -460, 460, -40.0, 26.0, 0.9, 1.4],   # ph periwinkle_plant 岸花
		[37, 180, -460, 460, -40.0, 28.0, 1.2, 2.1],  # ph island_tree_01 密集背景林（instancer 无碰撞）
		[38, 200, -460, 460, -40.0, 28.0, 1.3, 2.3],  # ph island_tree_02 密集背景林
		[39, 140, -460, 460, -40.0, 28.0, 1.1, 2.0],  # ph island_tree_03 密集背景林
		[40, 60, -460, 460, -40.0, 28.0, 1.0, 2.0],   # ph shrub_01 写实灌木
		[41, 60, -460, 460, -40.0, 28.0, 0.8, 1.4],   # ph grass_medium_02
	]
	for spec in specs:
		_scatter(spec[0], spec[1], spec[2], spec[3], spec[4], spec[5], spec[6], spec[7])

func _scatter(mesh_id: int, count: int, lo: float, hi: float, h_min: float, h_max: float,
		scale_min: float, scale_max: float) -> void:
	# 草类资产走草甸掩码：只有噪声>阈值的区域密集，形成"一簇密一簇疏"的天然草甸
	var is_grass := mesh_id in [3, 4, 5, 15, 16, 19, 20, 27]
	var xforms: Array[Transform3D] = []
	var placed := 0
	var guard := 0
	while placed < count and guard < count * 30:
		guard += 1
		var pos := Vector3(rng.randf_range(lo, hi), 0.0, rng.randf_range(lo, hi))
		pos.y = terrain.data.get_height(pos)
		if pos.y < h_min or pos.y > h_max:
			continue
		# avoid river corridor (water/bank zone handled by _build_river)
		if absf(pos.z - _river_center_z(pos.x)) < 12.0:
			continue
		if is_grass and _meadow_noise.get_noise_2d(pos.x, pos.z) < 0.15:
			continue
		var yaw := rng.randf_range(0.0, TAU)
		var s := rng.randf_range(scale_min, scale_max)
		var basis := Basis(Vector3.UP, yaw).scaled(Vector3.ONE * s)
		xforms.append(Transform3D(basis, pos))
		placed += 1
	terrain.instancer.add_transforms(mesh_id, xforms)

func _build_landmark_rocks() -> void:
	_place_scene("res://assets/models/polyhaven/boulder_01/boulder_01_2k.gltf", Vector3(-240, 0, -180), 0.035)
	_place_scene("res://assets/models/polyhaven/boulder_01/boulder_01_2k.gltf", Vector3(210, 0, 150), 0.045)
	_place_scene("res://assets/models/polyhaven/rock_09/rock_09_2k.gltf", Vector3(120, 0, -260), 0.25)
	_place_scene("res://assets/models/polyhaven/rock_09/rock_09_2k.gltf", Vector3(-60, 0, 300), 0.3)
	# 参考图岩石形态多样：补两座大石（Kenney tall 变体）
	_place_scene("res://assets/models/kenney_nature/rock_tallC.glb", Vector3(-320, 0, 40), 2.2)
	_place_scene("res://assets/models/kenney_nature/rock_tallE.glb", Vector3(280, 0, -320), 2.4)

func _build_river() -> void:
	# 沿蛇形河道生成一张"贴合地形的带状水面"：
	# 用 ArrayMesh 沿路径 + 宽度方向采样地形高度，每个顶点 y = 地形高度 + 水深，
	# 彻底消除分段平面造成的悬浮/接缝问题。
	var mat := ShaderMaterial.new()
	mat.shader = load("res://assets/shaders/river_water.gdshader")
	var river := Node3D.new()
	river.name = "River"
	add_child(river)
	var half_w := 9.0      # 水面带半宽（m），两侧 2.5m 由顶点色渐隐做软岸线
	var water_core := 6.5  # 全不透明核心半宽（m）
	var depth := 0.55      # 水面到河床的高度（m）
	var step := 3.0        # 沿路径采样步长（m）
	var pts: Array[Vector3] = []
	for wx in range(-430.0, 431.0, step):
		var cz := _river_center_z(wx)
		pts.append(Vector3(wx, 0.0, cz))
	# 生成带状网格
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var verts: Array[Vector3] = []
	for i in pts.size():
		var p := pts[i]
		# 切线方向：端点用一阶差分，中间用前后点
		var tan: Vector3
		if i == 0:
			tan = (pts[1] - pts[0]).normalized()
		elif i == pts.size() - 1:
			tan = (pts[i] - pts[i - 1]).normalized()
		else:
			tan = (pts[i + 1] - pts[i - 1]).normalized()
		var side := tan.cross(Vector3.UP).normalized()
		# 三排顶点：右岸(透明) / 中心(不透明) / 左岸(透明)
		for k: float in [-1.0, 0.0, 1.0]:
			var v := p + side * (half_w * k)
			# 外缘贴合地形（0 深度），中心保留水深：杜绝岸边悬空唇边
			v.y = terrain.data.get_height(v) + depth * (1.0 - absf(k))
			verts.append(v)
	for i in verts.size():
		var row := i % 3
		var lat := absf((row - 1) * half_w)
		var a := clampf((lat - water_core) / (half_w - water_core), 0.0, 1.0)
		st.set_color(Color(1.0, 1.0, 1.0, 1.0 - a * a))
		st.set_normal(Vector3.UP)
		st.add_vertex(verts[i])
	for i in pts.size() - 1:
		var a := i * 3
		var b := (i + 1) * 3
		# 四边形拆两个三角形：右→中→下一行右、中→左→下一行中、中→左→下一行左
		st.add_index(a)
		st.add_index(a + 1)
		st.add_index(b)
		st.add_index(a + 1)
		st.add_index(b + 1)
		st.add_index(b)
		st.add_index(a + 1)
		st.add_index(a + 2)
		st.add_index(b + 1)
		st.add_index(a + 2)
		st.add_index(b + 2)
		st.add_index(b + 1)
	var mesh := st.commit()
	mesh.surface_set_material(0, mat)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	river.add_child(mi)
	# 河床：贴地形铺一条沙质河床带（宽于水面核心、略低于水面），
	# 透过半透明水面看到沙/碎石底，复刻参考图"清澈见底"
	var bed_mat := StandardMaterial3D.new()
	bed_mat.albedo_texture = load("res://assets/textures/riverbed_sand.png")
	bed_mat.albedo_color = Color(0.85, 0.85, 0.80)
	bed_mat.roughness = 1.0
	bed_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	var bed_st := SurfaceTool.new()
	bed_st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var bed_half := 7.0
	for i in pts.size():
		var p := pts[i]
		var tan: Vector3
		if i == 0:
			tan = (pts[1] - pts[0]).normalized()
		elif i == pts.size() - 1:
			tan = (pts[i] - pts[i - 1]).normalized()
		else:
			tan = (pts[i + 1] - pts[i - 1]).normalized()
		var side := tan.cross(Vector3.UP).normalized()
		for k: float in [-1.0, 1.0]:
			var v := p + side * (bed_half * k)
			v.y = terrain.data.get_height(v) + 0.08
			bed_st.set_uv(Vector2(float(i) * 0.2, (k + 1.0) * 0.5))
			bed_st.set_normal(Vector3.UP)
			bed_st.add_vertex(v)
	for i in pts.size() - 1:
		var a := i * 2
		var b := (i + 1) * 2
		bed_st.add_index(a)
		bed_st.add_index(a + 1)
		bed_st.add_index(b)
		bed_st.add_index(a + 1)
		bed_st.add_index(b + 1)
		bed_st.add_index(b)
	var bed_mesh := bed_st.commit()
	bed_mesh.surface_set_material(0, bed_mat)
	var bed_mi := MeshInstance3D.new()
	bed_mi.mesh = bed_mesh
	river.add_child(bed_mi)
	# 河岸装饰：沿河道放碎石（全部 rock 变体随机混用，形态更自然）
	var rock_variants := [
		"res://assets/models/kenney_nature/rock_smallA.glb",
		"res://assets/models/kenney_nature/rock_smallB.glb",
		"res://assets/models/kenney_nature/rock_smallC.glb",
		"res://assets/models/kenney_nature/rock_smallD.glb",
		"res://assets/models/kenney_nature/rock_smallE.glb",
		"res://assets/models/kenney_nature/rock_smallF.glb",
		"res://assets/models/kenney_nature/rock_smallFlatA.glb",
		"res://assets/models/kenney_nature/rock_smallFlatB.glb",
		"res://assets/models/kenney_nature/rock_largeB.glb",
		"res://assets/models/kenney_nature/rock_largeC.glb",
	]
	for i in 90:
		var wx := rng.randf_range(-420.0, 420.0)
		var cz := _river_center_z(wx)
		var at := Vector3(wx + rng.randf_range(-14.0, 14.0), 0.0, cz + rng.randf_range(-10.0, 10.0))
		at.y = terrain.data.get_height(at)
		var inst: Node = load(rock_variants[rng.randi_range(0, rock_variants.size() - 1)]).instantiate()
		river.add_child(inst)
		inst.scale = Vector3.ONE * rng.randf_range(0.8, 1.8)
		inst.rotation.y = rng.randf_range(0.0, TAU)
		var base := _scene_aabb(inst).position.y
		inst.position = Vector3(at.x, at.y - base + 0.05, at.z)
	# Submerged stones: half-hidden in the shallow stream so they stay visible
	# through the transparent water, matching the reference "clear stream".
	for i in 46:
		var wx := rng.randf_range(-410.0, 410.0)
		var cz := _river_center_z(wx)
		var at := Vector3(wx + rng.randf_range(-3.2, 3.2), 0.0, cz + rng.randf_range(-2.2, 2.2))
		at.y = terrain.data.get_height(at) + 0.06
		var winst: Node = load(rock_variants[rng.randi_range(0, rock_variants.size() - 1)]).instantiate()
		river.add_child(winst)
		winst.scale = Vector3.ONE * (2.2 if i % 3 == 0 else rng.randf_range(0.5, 1.4))
		winst.rotation.y = rng.randf_range(0.0, TAU)
		var wbase := _scene_aabb(winst).position.y
		winst.position = Vector3(at.x, at.y - wbase + 0.02, at.z)
		if i % 3 == 0:
			_place_rock_foam(river, Vector3(at.x, at.y + 0.55, at.z), winst.scale.x)
	# Distant lake: ellipse water surface over the widened west basin.
	var lake_cz := _river_center_z(-430.0)
	var lake_center := Vector3(-430.0, 0.0, lake_cz)
	var lake_h := terrain.data.get_height(lake_center) + 0.55
	var lake_st := SurfaceTool.new()
	lake_st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var lrx := 150.0
	var lrz := 85.0
	var lrings := 24
	var lsegs := 48
	for ri in lrings + 1:
		var rt := float(ri) / lrings
		for sj in lsegs:
			var ang := TAU * float(sj) / lsegs
			var px := lake_center.x + cos(ang) * lrx * rt
			var pz := lake_center.z + sin(ang) * lrz * rt
			var lat := clampf((rt - 0.55) / 0.45, 0.0, 1.0)
			lake_st.set_color(Color(1.0, 1.0, 1.0, 1.0 - lat * lat))
			lake_st.set_normal(Vector3.UP)
			lake_st.add_vertex(Vector3(px, lake_h, pz))
	for ri in lrings:
		for sj in lsegs:
			var a := ri * lsegs + sj
			var b := (ri + 1) * lsegs + sj
			var c := ri * lsegs + (sj + 1) % lsegs
			var d := (ri + 1) * lsegs + (sj + 1) % lsegs
			lake_st.add_index(a)
			lake_st.add_index(b)
			lake_st.add_index(c)
			lake_st.add_index(b)
			lake_st.add_index(d)
			lake_st.add_index(c)
	var lake_mesh := lake_st.commit()
	lake_mesh.surface_set_material(0, mat)
	var lake_mi := MeshInstance3D.new()
	lake_mi.name = "Lake"
	lake_mi.mesh = lake_mesh
	river.add_child(lake_mi)




var _foam_tex: ImageTexture


func _rock_foam_texture() -> ImageTexture:
	if _foam_tex != null:
		return _foam_tex
	var img := Image.create_empty(128, 128, false, Image.FORMAT_RGBA8)
	for y in img.get_height():
		for x in img.get_width():
			var d := Vector2(x - 63.5, y - 63.5).length() / 63.5
			var ring := smoothstep(0.42, 0.6, d) * (1.0 - smoothstep(0.82, 1.0, d))
			var hole := 0.75 + 0.25 * sin(x * 0.6 + y * 0.47)
			var a := ring * hole
			img.set_pixel(x, y, Color(1.0, 1.0, 1.0, clampf(a, 0.0, 1.0)))
	_foam_tex = ImageTexture.create_from_image(img)
	return _foam_tex


func _place_rock_foam(parent: Node3D, at: Vector3, rock_scale: float) -> void:
	var q := QuadMesh.new()
	q.size = Vector2(4.2 * rock_scale, 4.2 * rock_scale)
	var fm := StandardMaterial3D.new()
	fm.albedo_texture = _rock_foam_texture()
	fm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	fm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	q.material = fm
	var mi := MeshInstance3D.new()
	mi.mesh = q
	mi.rotation_degrees = Vector3(-90, 0, 0)
	mi.position = at
	parent.add_child(mi)


func _build_ambience() -> void:
	# 森林溪流环境音：程序化合成的 12s 无缝流水循环（tools/gen_river_ambience.py）
	var amb := AudioStreamPlayer3D.new()
	amb.name = "RiverAmbience"
	amb.stream = load("res://assets/sfx/river_ambience.wav")
	amb.position = Vector3(0, -8.0, 0)
	amb.unit_size = 8.0
	amb.max_db = 3.0
	amb.volume_db = -5.0
	amb.autoplay = true
	add_child(amb)
	# 林区落叶：CPUParticles3D 从密林斑块上方飘落
	var leaf_tex := load("res://assets/textures/leaf_dropped.png") as Texture2D
	var mat := StandardMaterial3D.new()
	mat.albedo_texture = leaf_tex
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.vertex_color_use_as_albedo = true
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	var quad := QuadMesh.new()
	quad.size = Vector2(0.22, 0.14)
	quad.material = mat
	var leaves := CPUParticles3D.new()
	leaves.name = "FallingLeaves"
	leaves.position = Vector3(-80, 12.0, 200)
	leaves.emitting = true
	leaves.one_shot = false
	leaves.amount = 60
	leaves.lifetime = 10.0
	leaves.preprocess = 6.0
	leaves.spread = 180.0
	leaves.gravity = Vector3(0, -0.5, 0)
	leaves.initial_velocity_min = 0.3
	leaves.initial_velocity_max = 0.9
	leaves.damping_min = 0.1
	leaves.damping_max = 0.4
	leaves.angular_velocity_min = -2.2
	leaves.angular_velocity_max = 2.2
	leaves.scale_amount_min = 0.7
	leaves.scale_amount_max = 1.4
	leaves.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	leaves.emission_box_extents = Vector3(26, 8, 26)
	leaves.color = Color(0.78, 0.86, 0.5, 0.95)
	leaves.mesh = quad
	add_child(leaves)


func _build_particle_grass() -> void:
	# Terrain3D 官方 GPU 粒子草：GPUParticles3D shader 直接采样地形高度图，
	# 在相机周围撒几千根草（实例间距 0.3m，随相机移动），几乎不占 draw call。
	# 参考图"单根草叶级"密度就是靠这层实现的。
	var pscn: PackedScene = load("res://addons/terrain_3d/extras/particle_example/Terrain3DParticles.tscn")
	if pscn == null:
		print("[grass] FAIL: Terrain3DParticles.tscn not found")
		return
	var pt := pscn.instantiate()
	pt.name = "ParticleGrass"
	pt.terrain = terrain
	add_child(pt)
	# 密度/范围微调：0.3m 间距 + 32m 单元 + 7x7 网格 → 相机周围约 4.9 万根草
	pt.instance_spacing = 0.3
	pt.cell_width = 32.0
	pt.grid_width = 7
	# 用项目内参数化草 shader（色相与地表 grass001 统一），不改插件源文件
	var gm := ShaderMaterial.new()
	gm.shader = load("res://assets/shaders/grass_particles.gdshader")
	# 草色与地表 grass001 贴图对齐（实测地表 hue≈118-122/sat≈0.62/val≈0.31）
	gm.set_shader_parameter("grass_color", Color(0.31, 0.38, 0.19))
	pt.mesh_material_override = gm
	# 增强自然随机性：间距抖动 + 高度差异 + 风摆（参考图草叶交错感）
	var pm: ShaderMaterial = pt.process_material
	if pm != null:
		# 成簇分布（参考图"一簇密一簇疏"的天然草甸）：
		# patch 阈值提高 → 只有噪声高的区域长草，形成密簇+空地的明暗斑块；
		# clod_scale_boost 提高 → 簇心草更高，边缘渐低。
		pm.set_shader_parameter("random_spacing", 0.85)
		pm.set_shader_parameter("min_scale", Vector3(0.1, 0.3, 0.1))
		pm.set_shader_parameter("max_scale", Vector3(0.2, 1.5, 0.2))
		pm.set_shader_parameter("wind_strength", 1.35)
		pm.set_shader_parameter("clod_scale_boost", 3.5)
		pm.set_shader_parameter("patch_min_threshold", 0.35)
		pm.set_shader_parameter("patch_max_threshold", 0.75)
		pm.set_shader_parameter("main_noise_scale", 0.006)

func _build_trees() -> void:
	# 热带岛树三物种：独立 StaticBody3D（带碰撞），AABB 底座精确贴地
	var tree_paths: Array[String] = [
		"res://assets/models/polyhaven/island_tree_02/island_tree_02_1k.gltf",  # 最常见
		"res://assets/models/polyhaven/island_tree_01/island_tree_01_1k.gltf",
		"res://assets/models/polyhaven/island_tree_03/island_tree_03_1k.gltf",
		"res://assets/models/polyhaven/tree_small_02/tree_small_02_1k.gltf",  # small tree
		"res://assets/models/polyhaven/quiver_tree_02/quiver_tree_02_2k.gltf",  # quiver tree 02
		"res://assets/models/polyhaven/fir_sapling/fir_sapling_2k.gltf",  # 针叶小树
	]
	var centers := [
		Vector2(35, 15), Vector2(-120, -60), Vector2(180, -140),
		Vector2(-240, 100), Vector2(60, -260), Vector2(300, 260),
	]
	for c in centers:
		for i in 26:
			var ang := rng.randf_range(0.0, TAU)
			var r := rng.randf_range(4.0, 55.0)
			_place_tree(_pick_tree(tree_paths), c + Vector2(cos(ang), sin(ang)) * r,
				rng.randf_range(1.0, 2.0))
	# 密集林斑块：参考图林缘密/空地疏，额外两个密林区
	var groves := [Vector2(-80, 200), Vector2(220, -40), Vector2(-260, -240)]
	for g in groves:
		for i in 24:
			var ang := rng.randf_range(0.0, TAU)
			var r := rng.randf_range(3.0, 30.0)
			_place_tree(_pick_tree(tree_paths), g + Vector2(cos(ang), sin(ang)) * r,
				rng.randf_range(1.0, 2.2))
	# 地图边缘稀疏背景树
	for i in 100:
		_place_tree(_pick_tree(tree_paths),
			Vector2(rng.randf_range(-420, 420), rng.randf_range(-420, 420)),
			rng.randf_range(0.9, 1.7))

func _pick_tree(paths: Array[String]) -> String:
	# 加权：island_tree_02 占 45%，01 / 03 各 20%，fir_sapling 15%
	var r := rng.randf()
	if r < 0.35:
		return paths[0]
	if r < 0.51:
		return paths[1]
	if r < 0.66:
		return paths[2]
	if r < 0.75:
		return paths[3]
	if r < 0.88:
		return paths[4]
	return paths[5]

func _place_tree(path: String, at2: Vector2, scale: float) -> void:
	var h := terrain.data.get_height(Vector3(at2.x, 0, at2.y))
	if h < -35.0 or h > 22.0:
		return
	var body := StaticBody3D.new()
	body.name = "Tree"
	add_child(body)
	var inst: Node = load(path).instantiate()
	body.add_child(inst)
	inst.scale = Vector3.ONE * scale
	inst.rotation.y = rng.randf_range(0.0, TAU)
	var info := _tree_info(path)
	var base: float = info["base"] * scale
	var size: Vector3 = info["size"] * scale
	body.position = Vector3(at2.x, h - base + 0.05, at2.y)
	var col := CollisionShape3D.new()
	var shape := CapsuleShape3D.new()
	shape.radius = 0.8 * scale
	shape.height = maxf(size.y * 0.7, 1.2)
	col.shape = shape
	col.position = Vector3(0, size.y * 0.35, 0)
	body.add_child(col)

func _tree_info(path: String) -> Dictionary:
	if not _tree_cache.has(path):
		var probe: Node = load(path).instantiate()
		add_child(probe)
		var aabb := _scene_aabb(probe)
		remove_child(probe)
		probe.free()
		_tree_cache[path] = {"base": aabb.position.y, "size": aabb.size}
	return _tree_cache[path]

func _scene_aabb(node: Node) -> AABB:
	var aabb := AABB()
	var first := true
	for m in node.find_children("", "MeshInstance3D", true, false):
		if m is MeshInstance3D and m.mesh != null:
			var b := (m as Node3D).global_transform * (m as MeshInstance3D).mesh.get_aabb()
			if first:
				aabb = b
				first = false
			else:
				aabb = aabb.merge(b)
	return aabb

func _place_scene(path: String, at: Vector3, scale: float) -> void:
	var inst: Node = load(path).instantiate()
	add_child(inst)
	inst.scale = Vector3.ONE * scale
	inst.rotation.y = rng.randf_range(0.0, TAU)
	var base := _scene_aabb(inst).position.y
	inst.position = Vector3(at.x, terrain.data.get_height(at) - base + 0.05, at.z)


func _build_player() -> void:
	var spawn := Vector3(0, 0, 40)
	# 出生点在地表上方 2m：Heightfield 碰撞单面，从下方/内部生成会直接掉穿
	var runtime := GameplayPlayerFactory.create(Vector3(spawn.x, terrain.data.get_height(spawn) + 2.0, spawn.z))
	var player: CharacterBody3D = runtime.player
	player.damaged.connect(_on_player_damaged)
	player.died.connect(_on_player_died)
	add_child(player)
	_player = player

func _build_hud() -> void:
	HUD.ensure_for_current_scene()
	call_deferred("_setup_hud_bridge")

## HUD 由 autoload(HUD) 提供（状态栏/快捷栏/背包唯一、数据跨场景保留）；
## 本场景桥接：别名指向 HUD 数据 + NPC 栏/子面板 + 治疗/技能信号。
func _setup_hud_bridge() -> void:
	if HUD.backpack == null:
		# 防递归风暴：backpack 由 autoload 的 _process 兜底初始化，
		# 本场景只做有限次重试（约 5 秒），超时放弃等 autoload 自行接线
		_hud_retries += 1
		if _hud_retries < 300:
			call_deferred("_setup_hud_bridge")
		return
	_hud_retries = 0
	_status_bar = HUD.status_bar
	_item_db = HUD.item_db
	_backpack = HUD.backpack
	_equipment = HUD.equipment
	_player_status = HUD.player_status
	if not HUD.player_healed.is_connected(_on_player_healed):
		HUD.player_healed.connect(_on_player_healed)
	if not HUD.skill_triggered.is_connected(_on_hud_skill):
		HUD.skill_triggered.connect(_on_hud_skill)
	var npc_bar := CanvasLayer.new()
	npc_bar.name = "NpcBar"
	npc_bar.set_script(load("res://ui/npc_bar.gd"))
	add_child(npc_bar)
	npc_bar.option_pressed.connect(_on_npc_option)
	_npc_bar = npc_bar
	_economy = HUD.economy
	_warehouse = HUD.warehouse
	_panels = NpcPanels.build(self, _item_db, _backpack, _equipment, _economy, npc_bar, _warehouse)
	var quest_panel = _panels.get("quest")
	if quest_panel != null:
		quest_panel.teleport_requested.connect(func(_quest_id: String) -> void: _on_teleport_requested())
	var expedition_panel = _panels.get("expedition")
	if expedition_panel != null:
		expedition_panel.depart_requested.connect(_on_depart_requested)
	_equipment.changed.connect(_refresh_weapon_mods)
	_refresh_weapon_mods()

func _on_hud_skill(skill_id: String, _phase: String) -> void:
	if _status_bar != null:
		_status_bar.show_status("技能未移植（%s）" % skill_id, 1.5)

func _on_player_healed(hp: int) -> void:
	if _status_bar != null:
		_status_bar.set_hp(hp, int(_player.get("max_hp")))
	if _player_status != null:
		_player_status.set_hp(hp)

func _build_return_portal() -> void:
	var pos := Vector3(0, 0, 30)
	pos.y = terrain.data.get_height(pos)
	var portal: Node = load("res://scripts/portal.gd").new()
	portal.name = "ReturnPortal"
	portal.target_scene = "res://scenes/main.tscn"
	portal.label_text = "传送门 · 返回基地"
	portal.position = pos + Vector3(0, 1.4, 0)
	add_child(portal)

func _find_crosshair() -> Label:
	if _status_bar == null:
		return null
	for c in _status_bar.find_children("", "Label", true, false):
		if c is Label and c.text == "+":
			return c
	return null

func _on_player_damaged(hp: int) -> void:
	if _status_bar:
		_status_bar.set_hp(hp, int(_player.get("max_hp")))
		_status_bar.damage_flash()

func _on_player_died() -> void:
	if _status_bar:
		_status_bar.show_death()

func _build_mouse_king() -> void:
	var pos := Vector3(2.8, 0, 26.0)
	pos.y = terrain.data.get_height(pos)
	var npc: Node = load("res://scripts/npc_interact.gd").new()
	npc.name = "MouseKingNpc"
	npc.position = pos + Vector3(0, 0.9, 0)
	npc.setup(NpcConfig.NPCS["shop_mouse_king"])
	npc.interacted.connect(_on_npc_interacted)
	add_child(npc)

func _on_npc_interacted(data: Dictionary) -> void:
	if _npc_bar == null:
		return
	if _npc_bar.is_open():
		_npc_bar.close()
	else:
		_npc_bar.open(data)

func _on_npc_option(id: String) -> void:
	if id == "info":
		_npc_bar.set_text("关于各个世界的信息正在收集中……目前可以告诉您的是，时空裂隙的出现频率越来越高，请务必小心。")
		return
	if id == "help":
		_npc_bar.set_text("帮助功能正在开发中，敬请期待。您可以先尝试接受任务前往其他世界探险。")
		return
	if NpcPanels.open(_panels, _npc_bar, id):
		return
	if _status_bar != null:
		_status_bar.show_status("NPC 选项待接入：%s" % id, 1.5)

func _on_teleport_requested() -> void:
	if _status_bar != null:
		_status_bar.show_status("任务场景未迁移，传送暂不可用", 2.0)

func _on_depart_requested(items: Array) -> void:
	if _backpack != null:
		for it in items:
			_backpack.add_item(String(it.get("id", "")), 1)
	if _status_bar != null:
		_status_bar.show_status("地牢世界未迁移，出征暂不可用（祭品已返还）", 2.5)

func _refresh_weapon_mods() -> void:
	var gun := _player.get_node_or_null("Camera3D/Gun") if _player != null else null
	if gun == null or _equipment == null:
		return
	var item: Dictionary = _equipment.get_item("weapon")
	if item.is_empty():
		item = _equipment.get_item("weapon2")
	if item.is_empty():
		gun.clear_item_mods()
		return
	gun.apply_item_mods(WeaponFormula.gun_mods_from_item(item))
