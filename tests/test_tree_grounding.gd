extends SceneTree

# 树木贴地与碰撞测试：每棵 Tree 静态体的底部应贴在地表，且必须带 CollisionShape3D。

var frames := 0
var checked := false


func _init() -> void:
	var scene: Node = load("res://scenes/demo_terrain.tscn").instantiate()
	root.add_child(scene)
	current_scene = scene
	process_frame.connect(_on_frame)


func _on_frame() -> void:
	frames += 1
	if frames < 20 or checked:
		return
	checked = true
	var terrain := current_scene.get_node_or_null("Terrain3D") as Terrain3D
	var all_bodies: Array = current_scene.find_children("", "StaticBody3D", true, false)
	# 场景中 StaticBody3D 即树木（同名会被 Godot 自动改名为 @StaticBody3D@N，按类过滤）
	var trees: Array = all_bodies
	print("[trees] count=", trees.size())
	var bad := 0
	var no_col := 0
	for t in trees:
		var body := t as StaticBody3D
		var h := terrain.data.get_height(body.global_position)
		var delta := body.global_position.y - h
		if absf(delta) > 1.0:
			bad += 1
			print("[trees] FLOAT body=", body.global_position, " h=", h, " delta=", delta)
		if body.find_children("", "CollisionShape3D", true, false).is_empty():
			no_col += 1
	print("[trees] floating=", bad, " no_collision=", no_col)
	quit(0 if bad == 0 and no_col == 0 else 1)
