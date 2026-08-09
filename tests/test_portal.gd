extends SceneTree

# 传送门触发测试：加载主场景，把玩家移到传送门位置，确认 body_entered 触发并切换场景。

var frames := 0
var entered := false


func _init() -> void:
	var main: Node = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
	current_scene = main
	process_frame.connect(_on_frame)


func _on_frame() -> void:
	frames += 1
	if frames == 15:
		var portal := current_scene.get_node_or_null("Portal") as Area3D
		var player := current_scene.get_node_or_null("Player") as Node3D
		print("[test] portal=", portal, " player=", player)
		if portal != null:
			print("[test] portal layer=", portal.collision_layer, " mask=", portal.collision_mask,
				" monitoring=", portal.monitoring, " monitorable=", portal.monitorable)
			var col := portal.get_node_or_null("Collision") as CollisionShape3D
			print("[test] col=", col, " shape=", col.shape if col else null)
			portal.body_entered.connect(func(body: Node3D) -> void:
				entered = true
				print("[test] body_entered: ", body.name, " is_player=", body.name == "Player"))
		if player != null:
			print("[test] player layer=", player.collision_layer)
			player.global_position = Vector3(0, 0.2, 0)
	if frames == 50:
		var portal := current_scene.get_node_or_null("Portal") as Area3D
		if portal != null:
			var bodies: Array[Node3D] = portal.get_overlapping_bodies()
			print("[test] overlapping_bodies=", bodies.size(), " ", bodies.map(func(b): return b.name))
		var path := ""
		if current_scene != null:
			path = current_scene.scene_file_path
		print("[test] frames=", frames, " entered=", entered, " current_scene=", path)
		quit(0)
