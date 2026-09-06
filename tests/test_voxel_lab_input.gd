extends SceneTree
var failures := 0

func _initialize() -> void:
	call_deferred("run")

func check(ok: bool, label: String) -> void:
	print("PASS " if ok else "FAIL ", label)
	if not ok:
		failures += 1

func key(code: Key, ctrl := false) -> void:
	var event := InputEventKey.new()
	event.keycode = code
	event.ctrl_pressed = ctrl
	event.pressed = true
	Input.parse_input_event(event)
	Input.flush_buffered_events()
	event = InputEventKey.new()
	event.keycode = code
	Input.parse_input_event(event)
	Input.flush_buffered_events()

func click(button: MouseButton, pressed: bool) -> void:
	var event := InputEventMouseButton.new()
	event.button_index = button
	event.pressed = pressed
	Input.parse_input_event(event)
	Input.flush_buffered_events()

func run() -> void:
	if DisplayServer.get_name() == "headless":
		print("This mouse-capture integration test requires a rendered window; omit --headless.")
		quit(2)
		return
	var path := "user://voxel-lab-input-" + str(OS.get_process_id()) + ".json"
	OS.set_environment("VOXEL_LAB_SAVE_PATH", path)
	var lab = load("res://scenes/voxel_lab.tscn").instantiate()
	root.add_child(lab)
	current_scene = lab
	lab.player.set_physics_process(false)
	lab.player.position = Vector3(-7.5, 3, 10.5)
	lab.camera.look_at(Vector3(-7.5, 0, 10.5), Vector3.FORWARD)
	await physics_frame
	await physics_frame
	var hit: Dictionary = lab.target()
	check(not hit.is_empty(), "camera aims at terrain cell")
	var target_cell: Vector3i = hit.mine
	click(MOUSE_BUTTON_LEFT, true)
	await physics_frame
	await physics_frame
	click(MOUSE_BUTTON_LEFT, false)
	check(lab.world.get_cell(target_cell) == 0, "left mouse excavates through scene input")
	key(KEY_4)
	await physics_frame
	check(lab.selected == 4, "number key selects building material")
	click(MOUSE_BUTTON_RIGHT, true)
	click(MOUSE_BUTTON_RIGHT, false)
	await physics_frame
	await physics_frame
	var placed_cell: Vector3i = lab.target().mine
	check(lab.world.get_cell(placed_cell) == 4, "right mouse places selected building material")
	await create_timer(0.65).timeout
	check(FileAccess.file_exists(path), "editing autosaves without pressing F5")
	key(KEY_F5)
	await process_frame
	check(FileAccess.file_exists(path), "F5 writes independent world save")
	key(KEY_Z,true)
	await physics_frame
	check(lab.world.get_cell(placed_cell)==0,"Ctrl+Z undoes placed brick through scene input")
	key(KEY_F9)
	await physics_frame
	check(lab.world.get_cell(placed_cell) == 4, "F9 restores placed building")
	check(lab.player.position.y >= 1.0 and lab.player.position.x == -12.5, "reload returns player to safe surface")
	lab.player.set_physics_process(true)
	for frame in 90:
		await physics_frame
	check(lab.player.is_on_floor(), "existing player controller stands on voxel collision")
	lab.queue_free()
	await process_frame
	DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
	print("VOXEL_INPUT_ACCEPTANCE failures=", failures)
	quit(0 if failures == 0 else 1)
