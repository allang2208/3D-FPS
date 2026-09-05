extends SceneTree

var scene: Node3D
var camera: Camera3D
var frames := 0
var shot := 0
var elapsed := 0.0
var timings: Array[float] = []


func _initialize() -> void:
	call_deferred("_load_scene")


func _load_scene() -> void:
	scene = load("res://scenes/scenic_valley.tscn").instantiate()
	root.add_child(scene)
	current_scene = scene
	scene.get_node("Player").set_process_unhandled_input(false)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	camera = Camera3D.new()
	camera.fov = 70
	camera.far = 2500
	root.add_child(camera)
	# Capture the actual arrival eye position after the player settles first.


func _process(delta: float) -> bool:
	if scene == null or camera == null:
		return false
	frames += 1
	elapsed += delta
	if frames == 20:
		var player: Node3D = scene.get_node("Player")
		var player_cam: Camera3D = player.get_node("Camera3D")
		camera.global_transform = player_cam.global_transform
		camera.make_current()
		player.set_physics_process(false)
		player.hide()
		for node in root.find_children("", "CanvasLayer", true, false):
			node.hide()
	if frames > 30:
		timings.append(delta)
	if frames == 65:
		RenderingServer.force_draw()
		var path := "res://docs/preview/valley_after_%d.png" % shot if shot < 3 else "res://docs/preview/valley_grounding_%d.png" % (shot - 3)
		var result := root.get_texture().get_image().save_png(path)
		print("[capture] ", path, " error=", result)
		shot += 1
		if shot == (6 if OS.get_cmdline_user_args().has("--grounding") else 3):
			timings.sort()
			print("[capture] median_frame_ms=", timings[timings.size() / 2] * 1000)
			quit()
			return false
		var p := Vector3(-95, 0, 17) if shot == 1 else Vector3(-135, 105, 140)
		if shot == 1:
			p.y = scene.terrain.data.get_height(p) + 2.1
		camera.position = p
		camera.look_at(Vector3(-230, 3.0, 0))
		if shot >= 3:
			var kind: String = ["plant", "tree", "rock"][shot - 3]
			var nearest := INF
			var target := Vector3.ZERO
			var target_box := AABB()
			for record in scene.grounding_records:
				if record["kind"] != kind:
					continue
				var xf: Transform3D = record["transform"]
				var point: Vector3 = xf * record["geometry"]["bounds"].get_center()
				var distance := Vector2(point.x, point.z).distance_to(scene.ARRIVAL)
				if distance < nearest:
					nearest = distance
					target = point
					target_box = xf * record["geometry"]["bounds"]
			if kind == "rock":
				target.z = target_box.end.z
			target.y = scene.terrain.data.get_height(target) + (0.2 if kind == "plant" else 0.45)
			camera.position = target + Vector3(1.5, 0.55, 1.5) * (1 if kind == "plant" else 2)
			camera.position.y = maxf(camera.position.y, scene.terrain.data.get_height(camera.position) + 0.5)
			camera.look_at(target)
		frames = 21
	return false
