extends SceneTree

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	var scene: Node3D = load("res://scenes/scenic_valley.tscn").instantiate()
	root.add_child(scene)
	current_scene = scene
	for i in 30:
		await process_frame
	var player: Node3D = scene.get_node("Player")
	var camera := Camera3D.new()
	root.add_child(camera)
	camera.global_transform = player.get_node("Camera3D").global_transform
	camera.fov = 70
	camera.far = 2500
	camera.make_current()
	player.set_physics_process(false)
	player.hide()
	for canvas in root.find_children("", "CanvasLayer", true, false):
		canvas.hide()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	for i in 90:
		await process_frame
	var timings: Array[float] = []
	var last := Time.get_ticks_usec()
	for i in 240:
		await process_frame
		var now := Time.get_ticks_usec()
		timings.append((now - last) / 1000.0)
		last = now
	timings.sort()
	var tag := "optimized" if OS.get_cmdline_user_args().is_empty() else OS.get_cmdline_user_args()[0]
	print("[benchmark] ", tag, " device=", RenderingServer.get_video_adapter_name(),
		" resolution=", root.size, " median_ms=", timings[120], " p95_ms=", timings[228],
		" primitives=", Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
		" draws=", Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/valley_perf_" + tag + ".png")
	quit()
