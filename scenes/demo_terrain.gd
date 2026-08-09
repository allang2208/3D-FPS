extends Node3D

# 地形演示场景：Terrain3D + 免费 CC0 资产（Poly Haven 热带岛树/岩石、Kenney 灌木草石、AmbientCG 地表纹理、HDRI 天空）

const HDRI := "res://assets/environment/hdri/kloofendal_48d_partly_cloudy_puresky_2k.hdr"
const PREP_TEX := "res://assets/textures/terrain_prepared/%s_%s.png"
const DATA_DIR := "res://assets/terrain_data/demo"
const NpcConfig := preload("res://ui/npc_config.gd")
const NpcPanels := preload("res://ui/npc_panels.gd")
const WeaponFormula := preload("res://ui/weapon_formula.gd")

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
var _tree_cache := {}  # 树模型路径 -> {"base": scale=1 底座偏移, "size": 包围盒尺寸}
var _hud_retries := 0  # HUD 桥接重试计数：backpack 未就绪时有限重试，避免无限 call_deferred 递归崩溃

func _ready() -> void:
	rng.seed = 20260809
	_build_environment()
	_build_light()
	terrain = _build_terrain()
	_build_instanced_nature()
	_build_landmark_rocks()
	_build_river()
	_build_particle_grass()
	_build_trees()
	_build_props()
	_build_player()
	_build_hud()
	_build_return_portal()
	_build_mouse_king()
	print("[demo_terrain] scene ready")

func _build_environment() -> void:
	var env_node := WorldEnvironment.new()
	env_node.name = "WorldEnvironment"
	add_child(env_node)
	var env := Environment.new()
	var sky := Sky.new()
	var mat := PanoramaSkyMaterial.new()
	mat.panorama = load(HDRI)
	mat.energy_multiplier = 2.2  # 阴天 HDRI 提亮，恢复"有天空"的观感
	sky.sky_material = mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.1
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	# 曝光平衡（实测标定）：exposure 1.4 + 天空能量 2.2 + 低太阳/环境光
	# → 天空恢复可见 val≈0.51，地面保持参考图亮度 val≈0.33-0.36
	env.tonemap_exposure = 1.4
	# 热带雨林潮湿氛围：极低密度雾提升景深，避免远树/山体生硬。
	# 注意 fog_height 必须低于地表最低点，否则相机/低洼处会整片泡雾（实测全灰屏）
	env.fog_enabled = true
	env.fog_light_color = Color(0.55, 0.62, 0.58)
	env.fog_density = 0.0008
	env.fog_height = -45.0
	env.fog_height_density = 0.08
	# 关键：fog_sky_affect=1（默认）会让指数雾在无限远的天空上完全雾化，
	# 把 HDRI 天空盖成纯雾色——这就是"天空消失"的真凶（不是贴图/曝光）。
	# 设为 0：雾只影响地形/物体景深，天空恢复 HDRI 云层。
	env.fog_sky_affect = 0.0
	# SSAO/SSIL：给地形与植被接触阴影，消除"平面贴纸感"（参考图质感关键）
	env.ssao_enabled = true
	env.ssao_radius = 1.2
	env.ssao_intensity = 1.6
	env.ssil_enabled = true
	env.ssil_radius = 3.0
	env.ssil_intensity = 1.2
	# SSR：水面/湿润表面反射天空与岸边（参考图溪流反光感）
	env.ssr_enabled = true
	env.ssr_max_steps = 64
	env.ssr_fade_in = 0.12
	env.ssr_fade_out = 1.5
	env.ssr_depth_tolerance = 0.15
	# Glow 实测观感：开启后水面/天空高光泛光过重，画面"一片泛光看不清"，
	# 追求可玩性直接关闭（无辉光也能保持 FILMIC 色调）
	env.glow_enabled = false
	env_node.environment = env

func _build_light() -> void:
	var light := DirectionalLight3D.new()
	light.name = "Sun"
	light.rotation_degrees = Vector3(-50, 30, 0)
	light.light_energy = 0.28
	light.shadow_enabled = true
	add_child(light)

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
		"ground020", "ground030", "ground037", "ground080", "rock063"]
	var uv_scales := [0.08, 0.08, 0.09, 0.09, 0.08, 0.06, 0.08, 0.06, 0.05]
	for i in tex_ids.size():
		var ta := Terrain3DTextureAsset.new()
		ta.name = tex_ids[i]
		ta.albedo_texture = load(PREP_TEX % [tex_ids[i], "alb_ht"])
		ta.normal_texture = load(PREP_TEX % [tex_ids[i], "nrm_rgh"])
		# 参考图地面更"厚实"：法线强度略提、AO 更强，配合新 alpha 高度混合
		ta.normal_depth = 1.1
		ta.ao_strength = 2.5
		ta.uv_scale = uv_scales[i]
		ta.detiling_rotation = 0.12
		t.assets.set_texture(i, ta)

	# 程序化高度图：低频山体 + 高频微起伏（避免地面过平），
	# 并沿蛇形路径刻一条溪流河道（低洼带，供后续水体 shader 使用）
	t.region_size = 512
	var macro := FastNoiseLite.new()
	macro.noise_type = FastNoiseLite.TYPE_PERLIN
	macro.frequency = 0.0035
	macro.fractal_octaves = 4
	var micro := FastNoiseLite.new()
	micro.noise_type = FastNoiseLite.TYPE_PERLIN
	micro.frequency = 0.028
	micro.fractal_octaves = 2
	var img := Image.create_empty(1024, 1024, false, Image.FORMAT_RF)
	for x in img.get_width():
		for y in img.get_height():
			var wx := x - 512.0
			var wz := y - 512.0
			# 宏观起伏：±30m 实际高度（系数 2.0，import scale=45 → 2.0*45=90m 全幅？实测 ±30m 量级）
			var h := macro.get_noise_2d(x, y) * 2.0
			# 高频微起伏：±2.5m 实际高度（import scale=45，噪声系数=2.5/45）
			h += micro.get_noise_2d(x, y) * 0.056
			# 溪流河道：蛇形路径 z = 40*sin(x/90)，沿路径 26m 内逐渐挖低
			var cx := wx
			var cz := 40.0 * sin(wx / 90.0)
			var dist := absf(wz - cz)
			if dist < 26.0:
				var fall := (1.0 - dist / 26.0)
				fall = fall * fall
				# 河道中心低约 6m（实测校准：系数 0.01 ≈ 5-8m），边缘平滑过渡
				h -= fall * 0.01
				h += micro.get_noise_2d(x + 512, y + 512) * 0.03
			img.set_pixel(x, y, Color(h, 0.0, 0.0, 1.0))
	t.data.import_images([img, null, null], Vector3(-512, 0, -512), 0.0, 45.0)
	t.data.save_directory(DATA_DIR)
	t.collision.set_mode(Terrain3DCollision.FULL_GAME)  # 全量运行时碰撞（1km 地图性能足够）
	t.collision.build()

	# 植被/岩石 instancer 网格资产（顺序即 instancer id，须与 _build_instanced_nature 的 specs 对应）
	var mesh_specs: Array[String] = [
		"res://assets/models/kenney_nature/plant_bush.glb",
		"res://assets/models/kenney_nature/plant_bushLarge.glb",
		"res://assets/models/kenney_nature/plant_bushSmall.glb",
		"res://assets/models/kenney_nature/grass.glb",
		"res://assets/models/kenney_nature/grass_large.glb",
		"res://assets/models/kenney_nature/grass_leafs.glb",
		"res://assets/models/kenney_nature/flower_yellowA.glb",
		"res://assets/models/kenney_nature/flower_redA.glb",
		"res://assets/models/kenney_nature/flower_purpleA.glb",
		"res://assets/models/kenney_nature/stump_old.glb",
		"res://assets/models/kenney_nature/stump_round.glb",
		"res://assets/models/kenney_nature/log.glb",
		"res://assets/models/kenney_nature/log_stack.glb",
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
		"res://assets/models/kenney_nature/crops_bambooStageB.glb",
		"res://assets/models/kenney_nature/hanging_moss.glb",
		"res://assets/models/kenney_nature/plant_flatTall.glb",
		"res://assets/models/kenney_nature/grass_leafsLarge.glb",
		"res://assets/models/kenney_nature/plant_bushDetailed.glb",
		"res://assets/models/polyhaven/fir_sapling/fir_sapling_2k.gltf",
		"res://assets/models/polyhaven/moss_01/moss_01_2k.gltf",
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
		[0, 60, -460, 460, -35.0, 24.0, 0.8, 1.4],   # plant_bush
		[1, 55, -460, 460, -35.0, 24.0, 0.8, 1.5],   # plant_bushLarge
		[2, 55, -460, 460, -35.0, 24.0, 0.8, 1.3],   # plant_bushSmall
		[3, 150, -460, 460, -40.0, 30.0, 0.8, 1.4],  # grass
		[4, 140, -460, 460, -40.0, 30.0, 0.8, 1.4],  # grass_large
		[5, 130, -460, 460, -40.0, 30.0, 0.8, 1.4],  # grass_leafs
		[6, 25, -460, 460, -38.0, 26.0, 0.8, 1.2],   # flower_yellowA
		[7, 25, -460, 460, -38.0, 26.0, 0.8, 1.2],   # flower_redA
		[8, 25, -460, 460, -38.0, 26.0, 0.8, 1.2],   # flower_purpleA
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
		[24, 45, -460, 460, -38.0, 24.0, 0.8, 1.4],   # kenney bamboo 竹丛
		[25, 55, -460, 460, -40.0, 28.0, 0.8, 1.3],   # kenney hanging_moss 垂藤丛
		[26, 65, -460, 460, -40.0, 28.0, 0.8, 1.4],   # kenney plant_flatTall 宽叶
		[27, 85, -460, 460, -40.0, 30.0, 0.8, 1.4],   # kenney grass_leafsLarge 大草
		[28, 60, -460, 460, -40.0, 28.0, 0.8, 1.4],   # kenney plant_bushDetailed 细节灌木
		[29, 40, -460, 460, -38.0, 26.0, 1.2, 2.2],   # ph fir_sapling 小针叶树（放大）
		[30, 60, -460, 460, -40.0, 30.0, 1.5, 3.0],   # ph moss_01 地面苔藓斑
	]
	for spec in specs:
		_scatter(spec[0], spec[1], spec[2], spec[3], spec[4], spec[5], spec[6], spec[7])

func _scatter(mesh_id: int, count: int, lo: float, hi: float, h_min: float, h_max: float,
		scale_min: float, scale_max: float) -> void:
	var xforms: Array[Transform3D] = []
	var placed := 0
	var guard := 0
	while placed < count and guard < count * 30:
		guard += 1
		var pos := Vector3(rng.randf_range(lo, hi), 0.0, rng.randf_range(lo, hi))
		pos.y = terrain.data.get_height(pos)
		if pos.y < h_min or pos.y > h_max:
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

func _build_river() -> void:
	# 沿蛇形河道生成一张"贴合地形的带状水面"：
	# 用 ArrayMesh 沿路径 + 宽度方向采样地形高度，每个顶点 y = 地形高度 + 水深，
	# 彻底消除分段平面造成的悬浮/接缝问题。
	var mat := ShaderMaterial.new()
	mat.shader = load("res://assets/shaders/river_water.gdshader")
	var river := Node3D.new()
	river.name = "River"
	add_child(river)
	var half_w := 6.5      # 半宽（m）
	var depth := 0.55      # 水面到河床的高度（m）
	var step := 3.0        # 沿路径采样步长（m）
	var pts: Array[Vector3] = []
	for wx in range(-430.0, 431.0, step):
		var cz := 40.0 * sin(wx / 90.0)
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
		var left := p + side * half_w
		var right := p - side * half_w
		left.y = terrain.data.get_height(left) + depth
		right.y = terrain.data.get_height(right) + depth
		verts.append(right)
		verts.append(left)
	for v in verts:
		st.add_vertex(v)
	for i in pts.size() - 1:
		var a := i * 2
		var b := (i + 1) * 2
		# 四边形 (a右,a左,b右,b左) 拆两个三角形
		st.add_index(a)
		st.add_index(a + 1)
		st.add_index(b)
		st.add_index(a + 1)
		st.add_index(b + 1)
		st.add_index(b)
	var mesh := st.commit()
	mesh.surface_set_material(0, mat)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	river.add_child(mi)
	# 河岸装饰：沿河道放一些碎石（复用 rock_smallA）
	var rock: PackedScene = load("res://assets/models/kenney_nature/rock_smallA.glb")
	for i in 30:
		var wx := rng.randf_range(-420.0, 420.0)
		var cz := 40.0 * sin(wx / 90.0)
		var at := Vector3(wx + rng.randf_range(-12.0, 12.0), 0.0, cz + rng.randf_range(-9.0, 9.0))
		at.y = terrain.data.get_height(at)
		var inst: Node = rock.instantiate()
		river.add_child(inst)
		inst.scale = Vector3.ONE * rng.randf_range(0.8, 1.8)
		inst.rotation.y = rng.randf_range(0.0, TAU)
		var base := _scene_aabb(inst).position.y
		inst.position = Vector3(at.x, at.y - base + 0.05, at.z)

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
	gm.set_shader_parameter("grass_color", Color(0.54, 0.67, 0.53))
	pt.mesh_material_override = gm
	# 增强自然随机性：间距抖动 + 高度差异 + 风摆（参考图草叶交错感）
	var pm: ShaderMaterial = pt.process_material
	if pm != null:
		pm.set_shader_parameter("random_spacing", 0.8)
		pm.set_shader_parameter("min_scale", Vector3(0.1, 0.35, 0.1))
		pm.set_shader_parameter("max_scale", Vector3(0.18, 1.35, 0.18))
		pm.set_shader_parameter("wind_strength", 1.25)
		pm.set_shader_parameter("clod_scale_boost", 2.5)
		pm.set_shader_parameter("patch_min_threshold", 0.05)
		pm.set_shader_parameter("patch_max_threshold", 0.3)

func _build_trees() -> void:
	# 热带岛树三物种：独立 StaticBody3D（带碰撞），AABB 底座精确贴地
	var tree_paths: Array[String] = [
		"res://assets/models/polyhaven/island_tree_02/island_tree_02_1k.gltf",  # 最常见
		"res://assets/models/polyhaven/island_tree_01/island_tree_01_1k.gltf",
		"res://assets/models/polyhaven/island_tree_03/island_tree_03_1k.gltf",
		"res://assets/models/polyhaven/fir_sapling/fir_sapling_2k.gltf",  # 针叶小树
	]
	var centers := [
		Vector2(35, 15), Vector2(-120, -60), Vector2(180, -140),
		Vector2(-240, 100), Vector2(60, -260), Vector2(300, 260),
	]
	for c in centers:
		for i in 8:
			var ang := rng.randf_range(0.0, TAU)
			var r := rng.randf_range(4.0, 55.0)
			_place_tree(_pick_tree(tree_paths), c + Vector2(cos(ang), sin(ang)) * r,
				rng.randf_range(1.0, 2.0))
	# 地图边缘稀疏背景树
	for i in 25:
		_place_tree(_pick_tree(tree_paths),
			Vector2(rng.randf_range(-420, 420), rng.randf_range(-420, 420)),
			rng.randf_range(0.9, 1.7))

func _pick_tree(paths: Array[String]) -> String:
	# 加权：island_tree_02 占 45%，01 / 03 各 20%，fir_sapling 15%
	var r := rng.randf()
	if r < 0.45:
		return paths[0]
	if r < 0.65:
		return paths[1]
	if r < 0.85:
		return paths[2]
	return paths[3]

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

func _build_props() -> void:
	var props := [
		"res://assets/models/kenney_tower_defense/wood-structure.glb",
		"res://assets/models/kenney_tower_defense/wood-structure-high.glb",
		"res://assets/models/kenney_tower_defense/weapon-ammo-bullet.glb",
		"res://assets/models/kenney_tower_defense/tower-round-base.glb",
	]
	for i in 14:
		var path: String = props[i % props.size()]
		var pos := Vector3(rng.randf_range(-400, 400), 0.0, rng.randf_range(-400, 400))
		pos.y = terrain.data.get_height(pos)
		if pos.y < -30.0 or pos.y > 25.0:
			continue
		var inst: Node = load(path).instantiate()
		add_child(inst)
		inst.rotation.y = rng.randf_range(0.0, TAU)
		var base := _scene_aabb(inst).position.y
		inst.position = Vector3(pos.x, pos.y - base + 0.05, pos.z)

func _build_player() -> void:
	var player := CharacterBody3D.new()
	player.name = "Player"
	var spawn := Vector3(0, 0, 40)
	# 出生点在地表上方 2m：Heightfield 碰撞单面，从下方/内部生成会直接掉穿
	player.position = Vector3(spawn.x, terrain.data.get_height(spawn) + 2.0, spawn.z)
	player.set_script(load("res://scripts/player.gd"))
	player.damaged.connect(_on_player_damaged)
	player.died.connect(_on_player_died)
	var col := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.35
	cap.height = 1.7
	col.shape = cap
	player.add_child(col)
	var cam := Camera3D.new()
	cam.name = "Camera3D"
	cam.position = Vector3(0, 1.62, 0)
	cam.fov = 75.0
	cam.current = true  # Terrain3D 需要活动相机，否则报错并停止物理进程
	player.add_child(cam)
	var cfx := Node3D.new()
	cfx.name = "CameraFx"
	cfx.set_script(load("res://scripts/camera_fx.gd"))
	cam.add_child(cfx)
	var gun := Node3D.new()
	gun.name = "Gun"
	gun.position = Vector3(0.28, -0.26, -0.5)
	gun.set_script(load("res://scripts/gun.gd"))
	cam.add_child(gun)
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
	_economy = load("res://ui/economy.gd").new()
	_warehouse = load("res://ui/warehouse.gd").new()
	_warehouse.add_item(_item_db.create_instance("enhancement_stone", 2))
	_warehouse.add_item(_item_db.create_instance("reforge_ticket", 1))
	_warehouse.add_item(_item_db.create_instance("magic_dust", 50))
	NpcPanels.seed_materials(_backpack)
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
