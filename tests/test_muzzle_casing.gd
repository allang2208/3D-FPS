extends SceneTree
## 无头验证：枪口火光 + 弹壳抛壳优化
## 1) 开火瞬间火光初始化：flash_t=0.08、星形 + 双十字火舌（沿枪管 -Z）+ 柔光晕 + 6 帧火焰动画 + OmniLight/火花就位
## 2) 生命周期同步验证：_process(0.03) 后仍亮，再 _process(0.04) 熄灭
## 3) 弹壳生成 1 颗（Casing，圆柱弹壳）
## 4) 弹壳寿命（1.2~1.8s）到期自毁
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_muzzle_casing.gd

const CasingScript := preload("res://scripts/casing.gd")

var _gun: Node
var _t0 := 0
var _stage := 0
var _ok_flash := false
var _ok_casing := false
var _ok_cleanup := false

func _initialize() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	root.add_child(scene.instantiate())

func _process(_delta: float) -> bool:
	if _gun == null:
		_gun = root.get_node_or_null("Main/Player/Camera3D/Gun")
		if _gun:
			_gun.set("ammo", 30)
			_gun.call("_shoot")
			# 同步验证（不依赖帧时序）：开火瞬间状态
			var flash_mesh: Node = _gun.get("_flash_mesh")
			var tongue: Node = _gun.get("_flash_tongue")
			var tongue_b: Node = _gun.get("_flash_tongue_b")
			var glow: Node = _gun.get("_flash_glow")
			var light: Node = _gun.get("_flash_light")
			var sparks: Node = _gun.get("_sparks")
			var flame_frames: Array = _gun.get("_flame_frames")
			var flash_t: float = _gun.get("_flash_t")
			var scale: float = _gun.get("_flash_scale")
			_ok_flash = flash_t == 0.08 \
				and flash_mesh.mesh is QuadMesh \
				and tongue.mesh is QuadMesh \
				and tongue_b.mesh is QuadMesh \
				and glow.mesh is QuadMesh \
				and flame_frames.size() == 6 \
				and absf(tongue.rotation.x + PI / 2) < 0.01 \
				and absf(tongue_b.rotation.x + PI / 2) < 0.01 \
				and absf(tongue_b.rotation.z - (PI / 2 + tongue.rotation.z)) < 0.01 \
				and sparks is CPUParticles3D \
				and light is OmniLight3D \
				and scale >= 0.85 and scale <= 1.55 \
				and absf((flash_mesh.scale as Vector3).x - scale) < 0.001
			# 生命周期：0.05s 后仍亮（衰减中），再 0.04s 熄灭（总 0.09s > 0.08s）
			_gun.call("_process", 0.05)
			var mid_ok: bool = float(_gun.get("_flash_t")) > 0.0 \
				and flash_mesh.visible and tongue.visible and tongue_b.visible \
				and glow.visible and light.visible \
				and float(light.get("light_energy")) > 0.0
			_gun.call("_process", 0.04)
			var end_ok: bool = float(_gun.get("_flash_t")) <= 0.0 \
				and not flash_mesh.visible and not tongue.visible and not tongue_b.visible \
				and not glow.visible and not light.visible
			_ok_flash = _ok_flash and mid_ok and end_ok
			_ok_casing = _count_casings() == 1
			print("TEST flash=", _ok_flash, " casing=", _ok_casing, " mid=", mid_ok, " end=", end_ok)
			_t0 = Time.get_ticks_msec()
		return false
	var now := Time.get_ticks_msec()
	if _stage == 0 and now - _t0 >= 2300:
		# 2.3s > 弹壳最长寿命 1.8s：应已自毁
		_ok_cleanup = _count_casings() == 0
		print("TEST casing_cleaned=", _ok_cleanup)
		quit(0 if _ok_flash and _ok_casing and _ok_cleanup else 1)
		return false
	return false

func _count_casings() -> int:
	var n := 0
	for c in root.find_children("*", "", true, false):
		if c.get_script() == CasingScript:
			n += 1
	return n
