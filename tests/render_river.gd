extends SceneTree

# 渲染溪流视角：沿河道取 3 个机位（俯视河道 + 平视河岸 + 远景河湾）
# 运行：& $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_river.gd

var _scene: Node
var _frames := 0
var _shots := 0
var _cam: Camera3D


func _initialize() -> void:
	_scene = load("res://scenes/demo_terrain.tscn").instantiate()
	root.add_child(_scene)
	_cam = Camera3D.new()
	_cam.name = "RiverCam"
	_cam.current = true
	root.add_child(_cam)
	_cam.fov = 70.0


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 25:
		_cam.current = true  # 场景 ready 后夺回相机（Player 相机 ready 时会抢 current）
	if _frames < 26:
		return false
	var t := _scene.get_node("Terrain3D") as Terrain3D
	var spots := [
		[Vector3(0, 0, 40.0 * sin(0.0 / 90.0) + 18.0), Vector3(0, 0, 40.0 * sin(0.0 / 90.0) - 4.0)],
		[Vector3(150, 0, 40.0 * sin(150.0 / 90.0) - 14.0), Vector3(150, 0, 40.0 * sin(150.0 / 90.0) + 8.0)],
		[Vector3(-150, 0, 40.0 * sin(-150.0 / 90.0) + 16.0), Vector3(-150, 0, 40.0 * sin(-150.0 / 90.0) - 5.0)],
	]
	if _shots < spots.size():
		var s: Array = spots[_shots]
		var from: Vector3 = s[0]
		var to: Vector3 = s[1]
		from.y = t.data.get_height(from) + 6.0
		to.y = t.data.get_height(to) + 0.3
		_cam.global_position = from
		_cam.look_at(to, Vector3.UP)
	if _frames < 42:
		return false
	var img := root.get_viewport().get_texture().get_image()
	if img == null or img.get_width() == 0:
		print("VIEWPORT EMPTY")
		quit(0)
		return false
	var out := "user://river_view_%d.png" % _shots
	img.save_png(out)
	print("SAVED ", ProjectSettings.globalize_path(out))
	_shots += 1
	if _shots >= 3:
		quit(0)
		return false
	_frames = 20  # 给地形 clipmap 几帧重新以相机为中心
	return false
