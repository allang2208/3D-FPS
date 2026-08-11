extends SceneTree

# 地形碰撞测试：加载旷野场景，等物理运行后检查玩家是否站在地形表面（未掉穿）。

var frames := 0
var _loaded := false


func _init() -> void:
	process_frame.connect(_on_frame)


func _on_frame() -> void:
	# 延迟到第一帧再加载场景：-s 模式下 autoload（如 HUD）在 _init 时尚未注册，
	# 提前 load 会让 demo_terrain.gd 编译失败（Identifier not found: HUD）。
	if not _loaded:
		_loaded = true
		var scene: Node = load("res://scenes/demo_terrain.tscn").instantiate()
		root.add_child(scene)
		current_scene = scene
		return
	frames += 1
	if frames < 20:
		return
	var player := current_scene.get_node_or_null("Player") as Node3D
	var terrain := current_scene.get_node_or_null("Terrain3D") as Terrain3D
	if player == null or terrain == null:
		return
	var ground_h := terrain.data.get_height(player.global_position)
	if frames == 100:
		var delta := player.global_position.y - ground_h
		print("[collision] player_y=", player.global_position.y,
			" terrain_h=", ground_h, " delta=", delta)
		var col_mode := -1
		if terrain.collision != null:
			col_mode = terrain.collision.get_mode()
		print("[collision] terrain_collision_mode=", col_mode)
		print("[collision] collision_enabled=", terrain.collision.is_enabled(),
			" rid_valid=", terrain.collision.get_rid().is_valid())
		print("[collision] collision_layer=", terrain.collision.get_layer(),
			" mask=", terrain.collision.get_mask())
		print("[collision] terrain_children=",
			terrain.get_children().map(func(c): return c.name))
		if player is CharacterBody3D:
			print("[collision] is_on_floor=", player.is_on_floor())
		var space := player.get_world_3d().direct_space_state
		var from := player.global_position + Vector3(0, 60, 0)
		var to := from + Vector3(0, -110, 0)
		var q := PhysicsRayQueryParameters3D.create(from, to)
		var hit := space.intersect_ray(q)
		if hit.is_empty():
			print("[collision] raycast hit: NOTHING")
		else:
			print("[collision] raycast hit: ", hit.get("collider"), " at y=", hit.get("position"))
		quit(0 if absf(delta) < 2.0 else 1)
