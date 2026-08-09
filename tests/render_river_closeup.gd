extends SceneTree

# River close-ups: near-water level views along the stream + one top-down
# check that the water ribbon is continuous along the valley.
# Run: $godot --path 'E:\3d\3-dfps' --script res://tests/render_river_closeup.gd

var _scene: Node
var _frames := 0
var _shots := 0
var _cam: Camera3D
var _terrain: Terrain3D


func _initialize() -> void:
	_scene = load("res://scenes/demo_terrain.tscn").instantiate()
	root.add_child(_scene)
	_cam = Camera3D.new()
	_cam.name = "RiverCam"
	_cam.current = true
	root.add_child(_cam)
	_cam.fov = 70.0


func _river_center_z(wx: float) -> float:
	return 40.0 * sin(wx / 90.0)


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 25:
		_cam.current = true  # 场景 ready 后夺回相机
	if _frames < 26:
		return false
	_terrain = _scene.get_node_or_null("Terrain3D") as Terrain3D
	var spots := [
		# [wx, eye_offset_z, look_offset_z, eye_height_above_water, label]
		[0.0, 9.0, -1.0, 1.0, "eye"],
		[150.0, -8.0, 1.0, 0.9, "eye"],
		[80.0, 0.0, 0.0, 60.0, "top"],
	]
	if _shots < spots.size() and _terrain != null:
		var s: Array = spots[_shots]
		var wx: float = s[0]
		var cz := _river_center_z(wx)
		var water_h := _terrain.data.get_height(Vector3(wx, 0, cz)) + 0.55
		var from: Vector3
		var to: Vector3
		if s[4] == "top":
			from = Vector3(wx, water_h + s[3], cz)
			to = Vector3(wx, water_h - 1.0, cz)
		else:
			from = Vector3(wx + 0.0, water_h + s[3], cz + s[1])
			to = Vector3(wx, water_h + 0.1, cz + s[2])
		_cam.global_position = from
		_cam.look_at(to, Vector3.UP)
		print("[cam] shot=", _shots, " from=", from, " to=", to)
	if _frames < 36:
		return false
	var img := root.get_viewport().get_texture().get_image()
	if img == null or img.get_width() == 0:
		print("VIEWPORT EMPTY")
		quit(0)
		return false
	var out := "user://river_close_%d.png" % _shots
	img.save_png(out)
	print("SAVED ", ProjectSettings.globalize_path(out))
	_shots += 1
	if _shots >= 3:
		quit(0)
		return false
	_frames = 20
	return false
