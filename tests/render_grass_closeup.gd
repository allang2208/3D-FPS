extends SceneTree

# 渲染粒子草特写：低机位平视地面，突出单根草叶密度
# 运行：& $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_grass_closeup.gd

var _scene: Node
var _frames := 0
var _cam: Camera3D


func _initialize() -> void:
	_scene = load("res://scenes/demo_terrain.tscn").instantiate()
	root.add_child(_scene)
	_cam = Camera3D.new()
	_cam.name = "GrassCam"
	_cam.current = true
	root.add_child(_cam)
	_cam.fov = 75.0


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames < 40:
		return false
	var t := _scene.get_node("Terrain3D") as Terrain3D
	var at := Vector3(35, 0, 15)
	var h := t.data.get_height(at)
	_cam.global_position = Vector3(at.x, h + 0.9, at.z)
	_cam.look_at(Vector3(at.x, h - 0.05, at.z + 8.0), Vector3.UP)
	var img := root.get_viewport().get_texture().get_image()
	if img == null or img.get_width() == 0:
		print("VIEWPORT EMPTY")
		quit(0)
		return false
	img.save_png("user://grass_closeup.png")
	print("SAVED ", ProjectSettings.globalize_path("user://grass_closeup.png"))
	quit(0)
	return false
