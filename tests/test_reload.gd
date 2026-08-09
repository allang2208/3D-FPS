extends SceneTree
## 无头验证换弹（按真实时间）：场景 A 空仓自动换弹，场景 B R 键手动换弹
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_reload.gd

var _gun: Node
var _reload_done := 0
var _auto_started := false
var _stage := 0
var _stage_start := 0

func _initialize() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	root.add_child(scene.instantiate())

func _process(delta: float) -> bool:
	if _gun == null:
		_gun = root.get_node_or_null("Main/Player/Camera3D/Gun")
		if _gun:
			# 测试期间不让玩家被敌人咬死，避免 R 触发重生干扰换弹验证
			var player: Node = root.get_node_or_null("Main/Player")
			if player:
				player.set("hp", 99999)
			_gun.reloading.connect(func() -> void: _auto_started = true)
			_gun.reloaded.connect(func(_a: int, _r: int) -> void: _reload_done += 1)
			_gun.set("ammo", 0)
			_gun.set("reserve", 10)
			_stage_start = Time.get_ticks_msec()
			print("TEST stageA ammo=0 reserve=10")
		return false
	var now := Time.get_ticks_msec()
	if _stage == 0 and now - _stage_start > 2500:
		var auto_ok: bool = _auto_started and _reload_done >= 1 and _gun.get("ammo") == 10
		print("TEST auto_reload ammo=", _gun.get("ammo"), " started=", _auto_started, " done=", _reload_done, " ok=", auto_ok)
		_stage = 1
		_stage_start = now
		_gun.set("ammo", 5)
		_gun.set("reserve", 10)
		var ev := InputEventKey.new()
		ev.keycode = KEY_R
		ev.physical_keycode = KEY_R
		ev.pressed = true
		Input.parse_input_event(ev)
		_reload_done = 0
		_auto_started = false
		print("TEST stageB ammo=5 reserve=10 + R")
	if _stage == 1 and now - _stage_start > 2500:
		var r_ok: bool = _reload_done >= 1 and _gun.get("ammo") == 15
		print("TEST r_reload ammo=", _gun.get("ammo"), " done=", _reload_done, " ok=", r_ok)
		quit(0 if r_ok else 1)
		return false
	return false
