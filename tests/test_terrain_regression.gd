extends Node

# 地形回归 runner（场景模式运行，autoload 正常加载）：
#   godot --headless --path <project> res://tests/test_terrain_regression.tscn
# 断言：① 树贴地且带碰撞 ② 地形碰撞 RID 有效+射线命中 ③ 新资产可加载

var frames := 0
var _scene: Node


func _ready() -> void:
	_scene = load("res://scenes/demo_terrain.tscn").instantiate()
	add_child(_scene)
	await get_tree().process_frame
	await get_tree().create_timer(1.5).timeout
	_run()
	get_tree().quit(0 if _ok() else 1)


func _ok() -> bool:
	return _trees_ok and _terrain_ok and _assets_ok


var _trees_ok := false
var _terrain_ok := false
var _assets_ok := false


func _run() -> void:
	var terrain := _scene.get_node_or_null("Terrain3D") as Terrain3D
	# 1. 树贴地与碰撞
	var bad := 0
	var no_col := 0
	for t in _scene.find_children("", "StaticBody3D", true, false):
		var body := t as StaticBody3D
		var h := terrain.data.get_height(body.global_position)
		if absf(body.global_position.y - h) > 1.0:
			bad += 1
		if body.find_children("", "CollisionShape3D", true, false).is_empty():
			no_col += 1
	print("[regression] trees=", _scene.find_children("", "StaticBody3D", true, false).size(),
		" floating=", bad, " no_collision=", no_col)
	_trees_ok = bad == 0 and no_col == 0
	# 2. 地形碰撞
	if terrain != null and terrain.collision != null:
		var space: PhysicsDirectSpaceState3D = _scene.get_world_3d().direct_space_state
		var q := PhysicsRayQueryParameters3D.create(Vector3(0, 120, 0), Vector3(0, -130, 0))
		var hit: Dictionary = space.intersect_ray(q)
		print("[regression] collision_enabled=", terrain.collision.is_enabled(),
			" rid=", terrain.collision.get_rid().is_valid(),
			" raycast=", not hit.is_empty())
		_terrain_ok = terrain.collision.get_rid().is_valid() and not hit.is_empty()
	# 3. 新资产
	var paths := [
		"res://assets/models/polyhaven/fern_02/fern_02_2k.gltf",
		"res://assets/models/polyhaven/leafy_grass/leafy_grass_2k.gltf",
		"res://assets/models/polyhaven/fir_sapling/fir_sapling_2k.gltf",
		"res://assets/models/polyhaven/moss_01/moss_01_2k.gltf",
	]
	var fail := 0
	for p in paths:
		if load(p) == null:
			fail += 1
	print("[regression] assets_ok=", paths.size() - fail, "/", paths.size())
	_assets_ok = fail == 0
