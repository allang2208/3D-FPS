extends SceneTree

# 地形细节回归：不依赖枪械（规避并行线 akm 导入问题），验证
# 1) 地形碰撞 RID 有效且射线可命中；2) 新增林下资产均可加载。

var frames := 0


func _init() -> void:
	# --script 模式不加载 project.godot 的 autoload，手动挂载 HUD 让 demo_terrain.gd 可编译
	var hud: Node = load("res://ui/hud.gd").new()
	hud.name = "HUD"
	root.add_child(hud)
	var scene: Node = load("res://scenes/demo_terrain.tscn").instantiate()
	root.add_child(scene)
	current_scene = scene
	process_frame.connect(_on_frame)


func _on_frame() -> void:
	frames += 1
	if frames < 150:
		return
	var terrain := current_scene.get_node_or_null("Terrain3D") as Terrain3D
	if terrain == null or terrain.collision == null:
		print("[details] FAIL: terrain/collision missing")
		quit(1)
		return
	var bad := 0
	print("[details] collision_enabled=", terrain.collision.is_enabled(),
		" rid_valid=", terrain.collision.get_rid().is_valid())
	var space := root.world_3d.direct_space_state
	var from := Vector3(0, 120, 0)
	var q := PhysicsRayQueryParameters3D.create(from, Vector3(0, -130, 0))
	var hit := space.intersect_ray(q)
	if hit.is_empty():
		print("[details] FAIL: raycast hit nothing at origin")
		bad += 1
	else:
		print("[details] raycast hit y=", hit.get("position"))
	# 新增林下资产的加载
	var new_paths := [
		"res://assets/models/polyhaven/fern_02/fern_02_2k.gltf",
		"res://assets/models/polyhaven/leafy_grass/leafy_grass_2k.gltf",
		"res://assets/models/polyhaven/nettle_plant/nettle_plant_2k.gltf",
		"res://assets/models/polyhaven/weed_plant_02/weed_plant_02_2k.gltf",
		"res://assets/models/polyhaven/rock_moss_set_01/rock_moss_set_01_2k.gltf",
		"res://assets/models/polyhaven/searsia_burchellii/searsia_burchellii_2k.gltf",
		"res://assets/models/polyhaven/shrub_01/shrub_01_2k.gltf",
		"res://assets/models/polyhaven/flower_gazania/flower_gazania_2k.gltf",
		"res://assets/models/polyhaven/flower_heliophila/flower_heliophila_2k.gltf",
		"res://assets/models/polyhaven/dandelion_01/dandelion_01_2k.gltf",
		"res://assets/models/polyhaven/grass_medium_02/grass_medium_02_2k.gltf",
		"res://assets/models/polyhaven/tree_small_02/tree_small_02_1k.gltf",
		"res://assets/models/kenney_nature/hanging_moss.glb",
		"res://assets/models/kenney_nature/plant_flatTall.glb",
		"res://assets/models/kenney_nature/grass_leafsLarge.glb",
		"res://assets/models/kenney_nature/plant_bushDetailed.glb",
	]
	var load_fail := 0
	for p in new_paths:
		if load(p) == null:
			print("[details] FAIL load: ", p)
			load_fail += 1
	print("[details] new_assets_ok=", new_paths.size() - load_fail, "/", new_paths.size())
	quit(0 if bad == 0 and load_fail == 0 else 1)
