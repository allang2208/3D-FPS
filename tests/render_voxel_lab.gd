extends SceneTree
var lab: Node3D
var frames := 0
var frame_times: Array[float] = []
var previous_usec := 0

func _initialize() -> void:
	call_deferred("start")

func start() -> void:
	lab = load("res://scenes/voxel_lab.tscn").instantiate()
	root.add_child(lab)
	current_scene = lab
	lab.set_process_input(false)
	lab.player.set_process_unhandled_input(false)
	lab.player.set_physics_process(false)
	lab.player.position = Vector3(-12, 8, 17)
	lab.player.look_at(Vector3(5, 8, 0))
	lab.camera.set_as_top_level(true)
	lab.camera.global_position = Vector3(-16, 10, 19)
	lab.camera.look_at(Vector3(3, 2, 0))
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	# 用正式接口搭建一面带门洞的墙；材料扣除保存在本次独立试验中。
	for y in range(1, 4):
		for x in range(-9, -3):
			if x == -7 and y < 3:
				continue
			lab.world.place(Vector3i(x, y, 5), 4, AABB(Vector3(100, 100, 100), Vector3.ONE))
	# 从山坡侧面向内部开挖一条两格高的短通道。
	for x in range(-5, 6):
		for y in range(1, 3):
			lab.world.mine(Vector3i(x, y, 0))

func _process(_delta: float) -> bool:
	if lab == null:
		return false
	frames += 1
	var now := Time.get_ticks_usec()
	if frames > 350:
		frame_times.append((now - previous_usec) / 1000.0)
	previous_usec = now
	if frames == 450:
		var path := OS.get_environment("VOXEL_LAB_SCREENSHOT")
		if not path.is_empty():
			await RenderingServer.frame_post_draw
			print("CAPTURE_CAMERA position=",lab.camera.global_position," rotation=",lab.camera.global_rotation_degrees)
			print("VOXEL_SCREENSHOT error=", root.get_texture().get_image().save_png(path))
		frame_times.sort()
		print("VOXEL_RENDER_BENCH frames=", frame_times.size(), " median_ms=", frame_times[50], " p95_ms=", frame_times[95], " triangles=", lab.world.triangle_count)
		quit()
	return false
