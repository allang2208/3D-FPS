extends SceneTree
## 无头回归：开火脉冲 → 相机镜像弹簧同步起振（枪/镜头同源信号）
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_jitter_sync.gd

var _frames := 0
var _main: Node
var _gun: Node
var _cfx: Node
var _ok := false

func _initialize() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	_main = scene.instantiate()
	root.add_child(_main)

func _process(delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		_gun = root.get_node_or_null("Main/Player/Camera3D/Gun")
		_cfx = root.get_node_or_null("Main/Player/Camera3D/CameraFx")
		if _gun == null or _cfx == null:
			push_error("缺少 Gun 或 CameraFx")
			quit(1)
			return false
	if _frames == 2:
		# 模拟一次开火脉冲：枪械 jitter 弹簧 + 相机镜像弹簧都应获得动量
		_gun.call("_apply_gun_kick")
		_gun.call("_process", delta)
		_cfx.call("_process", delta)
		var g: Vector3 = _gun.get("_jitter_rot")
		var c: Vector3 = _cfx.get("_cam_jitter_rot")
		_ok = (g as Vector3).length_squared() > 0.0 and (c as Vector3).length_squared() > 0.0
		print("TEST gun_jitter=", g, " cam_jitter=", c)
	if _frames == 3:
		print("TEST jitter_sync=", _ok)
		quit(0 if _ok else 1)
		return false
	return false
