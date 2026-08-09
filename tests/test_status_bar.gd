extends SceneTree
## 无头冒烟：状态栏（HUD）接线 —— 受伤/弹药/换弹/命中/击杀/死亡更新 UI
## 运行： $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_status_bar.gd

var _frames := 0
var _main: Node
var _bar: Node
var _player: Node
var _gun: Node

func _initialize() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	_main = scene.instantiate()
	root.add_child(_main)

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		_bar = _main.get_node_or_null("StatusBar")
		_player = _main.get_node_or_null("Player")
		_gun = _main.get_node_or_null("Player/Camera3D/Gun")
		if _bar == null or _player == null or _gun == null:
			push_error("缺少 StatusBar / Player / Gun")
			quit(1)
			return false
		_player.set("hp", 100000)  # 避免敌人咬死干扰测试
		var ammo0: bool = String(_bar.get("_ammo_label").text).contains("30/90")
		var hp0: bool = String(_bar.get("_hp_label").text).contains("100/100")
		print("TEST init ammo0=", ammo0, " hp0=", hp0)
	if _frames == 3:
		_player.set("hp", 100)
		_player.take_damage(30)
		var hp_ok: bool = String(_bar.get("_hp_label").text).contains("70/100")
		var flash_ok: bool = float(_bar.get("_dmgflash_t")) > 0.0
		print("TEST damaged hp=", _bar.get("_hp_label").text, " flash_ok=", flash_ok)
	if _frames == 5:
		_gun.set("ammo", 5)
		_gun.set("reserve", 3)
		_gun.shot.emit(5, 3)
		var ammo_ok: bool = String(_bar.get("_ammo_label").text).contains("5/3")
		_gun.reloading.emit()
		var reload_ok: bool = bool(_bar.get("_status_label").visible) \
			and String(_bar.get("_status_label").text).contains("换弹中")
		_gun.hit.emit()
		var hit_ok: bool = bool(_bar.get("_hitmarker").visible)
		print("TEST ammo=", _bar.get("_ammo_label").text, " reload_ok=", reload_ok, " hit_ok=", hit_ok)
	if _frames == 10:
		var wolf: Node3D = _main.get_node_or_null("WolfEnemy") as Node3D
		if wolf != null:
			wolf.take_damage(9999)
	if _frames == 12:
		var kill_ok: bool = String(_bar.get("_kill_label").text).contains("击杀: 1")
		_player.set("hp", 100)
		_player.take_damage(200)
		var death_ok: bool = bool(_bar.get("_death_panel").visible)
		print("TEST kill=", _bar.get("_kill_label").text, " death_ok=", death_ok)
		var all_ok: bool = kill_ok and death_ok
		quit(0 if all_ok else 1)
		return false
	return false
