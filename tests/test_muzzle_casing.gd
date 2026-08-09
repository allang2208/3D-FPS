extends SceneTree
## 无头验证：粒子枪口火光 + 弹壳抛壳
## 1) 开火瞬间三层粒子（主闪光/火舌/火星）restart 后 emitting，且均为 one_shot、带 QuadMesh 与颜色渐变
## 2) 点光源生命周期同步验证：_process(0.05) 后仍亮，再 _process(0.04) 熄灭
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
			var pop: Node = _gun.get("_flash_pop")
			var flame: Node = _gun.get("_flash_flame")
			var sparks: Node = _gun.get("_flash_sparks")
			var light: Node = _gun.get("_flash_light")
			var flash_t: float = _gun.get("_flash_t")
			var flame_dir: Vector3 = flame.get("direction")
			_ok_flash = flash_t == 0.08 \
				and pop is CPUParticles3D and flame is CPUParticles3D and sparks is CPUParticles3D \
				and pop.get("emitting") and flame.get("emitting") and sparks.get("emitting") \
				and pop.get("one_shot") and flame.get("one_shot") and sparks.get("one_shot") \
				and pop.get("mesh") is QuadMesh and flame.get("mesh") is QuadMesh and sparks.get("mesh") is QuadMesh \
				and pop.get("color_ramp") != null and flame.get("color_ramp") != null and sparks.get("color_ramp") != null \
				and flame_dir.normalized().dot(Vector3(0, 0, -1)) > 0.99 \
				and int(flame.get("amount")) > 0 and int(pop.get("amount")) > 0 \
				and light is OmniLight3D
			# 生命周期：0.05s 后仍亮（衰减中），再 0.04s 熄灭（总 0.09s > 0.08s）
			_gun.call("_process", 0.05)
			var mid_ok: bool = float(_gun.get("_flash_t")) > 0.0 \
				and light.visible \
				and float(light.get("light_energy")) > 0.0
			_gun.call("_process", 0.04)
			var end_ok: bool = float(_gun.get("_flash_t")) <= 0.0 \
				and not light.visible
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
