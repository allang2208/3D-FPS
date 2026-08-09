extends Node3D

# 地形演示场景：Terrain3D + 免费 CC0 资产（Poly Haven 岩石、Kenney 植被/掩体、AmbientCG 地表纹理、HDRI 天空）

const HDRI := "res://assets/environment/hdri/kloofendal_48d_partly_cloudy_puresky_2k.hdr"
const PREP_TEX := "res://assets/textures/terrain_prepared/%s_%s.png"
const DATA_DIR := "res://assets/terrain_data/demo"

var terrain: Terrain3D
var rng := RandomNumberGenerator.new()
var _player: Node3D
var _status_bar: CanvasLayer


func _ready() -> void:
	rng.seed = 20260809
	_build_environment()
	_build_light()
	terrain = _build_terrain()
	_build_instanced_nature()
	_build_landmark_rocks()
	_build_props()
	_build_player()
	_build_hud()
	_build_return_portal()
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
	env.ambient_light_energy = 0.6
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env_node.environment = env


func _build_light() -> void:
	var light := DirectionalLight3D.new()
	light.name = "Sun"
	light.rotation_degrees = Vector3(-50, 30, 0)
	light.light_energy = 1.2
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
	var tex_ids := ["grass001", "ground037", "rock063", "ground080"]
	var uv_scales := [0.08, 0.08, 0.05, 0.05]
	for i in tex_ids.size():
		var ta := Terrain3DTextureAsset.new()
		ta.name = tex_ids[i]
		ta.albedo_texture = load(PREP_TEX % [tex_ids[i], "alb_ht"])
		ta.normal_texture = load(PREP_TEX % [tex_ids[i], "nrm_rgh"])
		ta.normal_depth = 1.0
		ta.ao_strength = 2.0
		ta.uv_scale = uv_scales[i]
		ta.detiling_rotation = 0.12
		t.assets.set_texture(i, ta)

	# 程序化高度图（ridged noise，1024x1024，region 512 -> 2x2 区块，约 1km 见方）
	t.region_size = 512
	var noise := FastNoiseLite.new()
	noise.noise_type = FastNoiseLite.TYPE_PERLIN
	noise.frequency = 0.0035
	noise.fractal_octaves = 4
	var img := Image.create_empty(1024, 1024, false, Image.FORMAT_RF)
	for x in img.get_width():
		for y in img.get_height():
			img.set_pixel(x, y, Color(noise.get_noise_2d(x, y), 0.0, 0.0, 1.0))
	t.data.import_images([img, null, null], Vector3(-512, 0, -512), 0.0, 45.0)
	t.data.save_directory(DATA_DIR)
	t.collision.set_mode(Terrain3DCollision.FULL_GAME)  # 全量运行时碰撞（1km 地图性能足够）
	t.collision.build()

	# 植被/岩石 instancer 网格资产（顺序即 instancer id，须与 _build_instanced_nature 的 specs 对应）
	var mesh_specs: Array[String] = [
		"res://assets/models/kenney_nature/tree_default.glb",
		"res://assets/models/kenney_nature/tree_cone.glb",
		"res://assets/models/kenney_nature/tree_detailed.glb",
		"res://assets/models/kenney_nature/tree_oak.glb",
		"res://assets/models/kenney_nature/tree_small.glb",
		"res://assets/models/kenney_nature/tree_tall.glb",
		"res://assets/models/kenney_nature/tree_pineTallA.glb",
		"res://assets/models/kenney_nature/plant_bush.glb",
		"res://assets/models/kenney_nature/plant_bushLarge.glb",
		"res://assets/models/kenney_nature/plant_bushSmall.glb",
		"res://assets/models/kenney_nature/grass.glb",
		"res://assets/models/kenney_nature/grass_large.glb",
		"res://assets/models/kenney_nature/grass_leafs.glb",
		"res://assets/models/kenney_nature/flower_yellowA.glb",
		"res://assets/models/kenney_nature/flower_redA.glb",
		"res://assets/models/kenney_nature/flower_purpleA.glb",
		"res://assets/models/kenney_nature/mushroom_red.glb",
		"res://assets/models/kenney_nature/mushroom_tan.glb",
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
	]
	for i in mesh_specs.size():
		var ma := Terrain3DMeshAsset.new()
		ma.name = "mesh_%02d" % i
		ma.scene_file = load(mesh_specs[i])
		ma.height_offset = 0.5
		t.assets.set_mesh_asset(i, ma)
	return t


func _build_instanced_nature() -> void:
	# [mesh_id, count, lo, hi, h_min, h_max, scale_min, scale_max]
	var specs: Array = [
		[0, 45, -460, 460, -30.0, 18.0, 0.8, 1.3],   # tree_default
		[1, 40, -460, 460, -30.0, 18.0, 0.8, 1.3],   # tree_cone
		[2, 40, -460, 460, -30.0, 18.0, 0.8, 1.2],   # tree_detailed
		[3, 35, -460, 460, -28.0, 16.0, 0.9, 1.4],   # tree_oak
		[4, 40, -460, 460, -32.0, 20.0, 0.8, 1.3],   # tree_small
		[5, 35, -460, 460, -28.0, 15.0, 0.9, 1.4],   # tree_tall
		[6, 40, -460, 460, -26.0, 14.0, 0.9, 1.4],   # tree_pineTallA
		[7, 60, -460, 460, -35.0, 24.0, 0.8, 1.4],   # plant_bush
		[8, 55, -460, 460, -35.0, 24.0, 0.8, 1.5],   # plant_bushLarge
		[9, 55, -460, 460, -35.0, 24.0, 0.8, 1.3],   # plant_bushSmall
		[10, 140, -460, 460, -40.0, 30.0, 0.8, 1.4], # grass
		[11, 130, -460, 460, -40.0, 30.0, 0.8, 1.4], # grass_large
		[12, 120, -460, 460, -40.0, 30.0, 0.8, 1.4], # grass_leafs
		[13, 55, -460, 460, -38.0, 26.0, 0.8, 1.3],  # flower_yellowA
		[14, 55, -460, 460, -38.0, 26.0, 0.8, 1.3],  # flower_redA
		[15, 55, -460, 460, -38.0, 26.0, 0.8, 1.3],  # flower_purpleA
		[16, 35, -460, 460, -36.0, 22.0, 0.8, 1.3],  # mushroom_red
		[17, 35, -460, 460, -36.0, 22.0, 0.8, 1.3],  # mushroom_tan
		[18, 25, -460, 460, -38.0, 26.0, 0.8, 1.4],  # stump_old
		[19, 25, -460, 460, -38.0, 26.0, 0.8, 1.4],  # stump_round
		[20, 30, -460, 460, -38.0, 26.0, 0.8, 1.4],  # log
		[21, 30, -460, 460, -38.0, 26.0, 0.8, 1.4],  # log_stack
		[22, 70, -460, 460, -42.0, 32.0, 0.6, 1.5],  # rock_largeA
		[23, 70, -460, 460, -42.0, 32.0, 0.6, 1.5],  # rock_smallA
		[24, 45, -460, 460, -40.0, 30.0, 0.8, 1.4],  # ph grass_medium_01
		[25, 45, -460, 460, -40.0, 30.0, 0.8, 1.4],  # ph grass_bermuda_01
		[26, 18, -460, 460, -36.0, 24.0, 0.7, 1.2],  # ph tree_stump_01
		[27, 18, -460, 460, -36.0, 24.0, 0.7, 1.2],  # ph dead_tree_trunk_02
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


func _place_scene(path: String, at: Vector3, scale: float) -> void:
	var inst: Node = load(path).instantiate()
	add_child(inst)
	inst.position = Vector3(at.x, terrain.data.get_height(at) + 0.5, at.z)
	inst.scale = Vector3.ONE * scale
	inst.rotation.y = rng.randf_range(0.0, TAU)


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
		inst.position = pos
		inst.rotation.y = rng.randf_range(0.0, TAU)


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
