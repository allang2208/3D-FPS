extends SceneTree
## 无头渲染第一人称枪械视角截图，验证 AI AKM 朝向/位置
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/render_gun_view.gd

var _main: Node
var _frames := 0

func _initialize() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	_main = scene.instantiate()
	root.add_child(_main)

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames < 8:
		return false
	# 用主相机渲染一帧
	var cam := root.get_node("Main/Player/Camera3D") as Camera3D
	var img := cam.get_viewport().get_texture().get_image()
	var out := "user://gun_view.png"
	img.save_png(out)
	print("SAVED ", ProjectSettings.globalize_path(out))
	quit(0)
	return false
