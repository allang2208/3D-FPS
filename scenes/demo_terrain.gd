extends Node3D

# 地形演示场景：Terrain3D + 免费 CC0 资产（Poly Haven 热带岛树/岩石、Kenney 灌木草石、AmbientCG 地表纹理、HDRI 天空）

const HDRI := "res://assets/environment/hdri/kloofendal_48d_partly_cloudy_puresky_2k.hdr"
const PREP_TEX := "res://assets/textures/terrain_prepared/%s_%s.png"
const DATA_DIR := "res://assets/terrain_data/demo"
const NpcConfig := preload("res://ui/npc_config.gd")

var terrain: Terrain3D
var rng := RandomNumberGenerator.new()
var _player: Node3D
var _status_bar: CanvasLayer
var _npc_bar: CanvasLayer
var _tree_cache := {}  # 树模型路径 -> {"base": scale=1 底座偏移, "size": 包围盒尺寸}


func _ready() -> void:
	rng.seed = 20260809
	_build_environment()
	_build_light()
	terrain = _build_terrain()
	_build_instanced_nature()
	_build_landmark_rocks()
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
	sky.sky_material = mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.35
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	# 过曝修复：FILMIC 默认 exposure=1.0 会把地表压到发白（实测 val≈0.90），
	# 降到 0.35 后地面回到参考图质感（val≈0.6-0.7、绿色饱和、层次分明）
	env.tonemap_exposure = 0.35
	# 热带雨林潮湿氛围：极低密度雾提升景深，避免远树/山体生硬。
	# 注意 fog_height 必须低于地表最低点，否则相机/低洼处会整片泡雾（实测全灰屏）
	env.fog_enabled = true
	env.fog_light_color = Color(0.55, 0.62, 0.58)
	env.fog_density = 0.0008
	env.fog_height = -45.0
	env.fog_height_density = 0.08
	env_node.environment = env


func _build_light() -> void:
	var light := DirectionalLight3D.new()
	light.name = "Sun"
	light.rotation_degrees = Vector3(-50, 30, 0)
	light.light_energy = 0.8
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
		remove_child(probe)
		probe.free()
		t.assets.set_mesh_asset(i, ma)
	return t


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
	gun.shot.connect(_on_ammo)
	gun.reloaded.connect(_on_ammo)
	gun.reloading.connect(_on_reloading)
	gun.empty.connect(_on_empty)
	gun.hit.connect(_on_hit)
	gun.ads_changed.connect(_on_ads_changed)
	cam.add_child(gun)
	add_child(player)
	_player = player


func _build_hud() -> void:
	var bar := CanvasLayer.new()
	bar.name = "StatusBar"
	bar.set_script(load("res://ui/status_bar.gd"))
	add_child(bar)
	_status_bar = bar
	var npc_bar := CanvasLayer.new()
	npc_bar.name = "NpcBar"
	npc_bar.set_script(load("res://ui/npc_bar.gd"))
	add_child(npc_bar)
	npc_bar.option_pressed.connect(_on_npc_option)
	_npc_bar = npc_bar


func _build_return_portal() -> void:
	var pos := Vector3(0, 0, 30)
	pos.y = terrain.data.get_height(pos)
	var portal: Node = load("res://scripts/portal.gd").new()
	portal.name = "ReturnPortal"
	portal.target_scene = "res://scenes/main.tscn"
	portal.label_text = "传送门 · 返回基地"
	portal.position = pos + Vector3(0, 1.4, 0)
	add_child(portal)


func _on_ammo(ammo: int, reserve: int) -> void:
	if _status_bar:
		_status_bar.set_ammo(ammo, reserve)


func _on_hit() -> void:
	if _status_bar:
		_status_bar.hitmark()


func _on_reloading() -> void:
	if _status_bar:
		_status_bar.show_status("换弹中…", 1.5)


func _on_empty() -> void:
	if _status_bar:
		_status_bar.show_status("没子弹 · 按 R 换弹", 1.2)


func _on_ads_changed(active: bool) -> void:
	var cross := _find_crosshair()
	if cross:
		cross.visible = not active


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
	if _status_bar == null:
		return
	match id:
		"shop":
			_status_bar.show_status("商店面板在基地开放（主场景 F8 可测）", 2.0)
		"enhance":
			_status_bar.show_status("强化面板在基地开放", 2.0)
		"craft":
			_status_bar.show_status("改造面板在基地开放", 2.0)
		"enchant":
			_status_bar.show_status("附魔面板在基地开放", 2.0)
		"quest", "teleport":
			_status_bar.show_status("任务面板在基地开放", 2.0)
		"expedition", "fusion":
			_status_bar.show_status("祭坛面板在基地开放", 2.0)
		"info":
			_npc_bar.set_text("关于各个世界的信息正在收集中……目前可以告诉您的是，时空裂隙的出现频率越来越高，请务必小心。")
		"help":
			_npc_bar.set_text("帮助功能正在开发中，敬请期待。您可以先尝试接受任务前往其他世界探险。")
