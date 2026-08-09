extends SceneTree
## 无头冒烟：状态栏（HUD）接线 —— 受伤/弹药/换弹/命中/击杀/死亡更新 UI
## 运行： $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_status_bar.gd

var _frames := 0
var _started := false
var _local := 0
var _bridge_ready := false
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
		var hud := root.get_node_or_null("HUD")
		if hud != null and not bool(hud.get("_built")):
			hud.call("_ensure_built")  # 节点 ready 后再初始化，避免 add_child 未触发 _ready 的时序警告
		_main.call("_setup_hud_bridge")  # --script 测试会一次排空 deferred，需主动执行桥接
	if not _started:
		_bar = root.get_node_or_null("HUD/StatusBar")
		_player = _main.get_node_or_null("Player")
		_gun = _main.get_node_or_null("Player/Camera3D/Gun")
		_bridge_ready = _main.get("_equipment") != null and _main.get("_npc_bar") != null
		if _bar == null or _player == null or _gun == null or not _bridge_ready:
			if _frames > 90:
				push_error("缺少 StatusBar / Player / Gun 或 HUD 桥接未完成")
				quit(1)
			return false
		_started = true
		_player.set("hp", 100000)  # 避免敌人咬死干扰测试
	_local += 1
	# ammo 可能被敌人触发玩家反击射击而变动，只校验格式（数字 + / 备弹）
	var ammo0: bool = String(_bar.get("_ammo_label").text).is_valid_int() and String(_bar.get("_ammo_reserve_label").text).begins_with(" / ")
	# hp 可能被敌人咬触发 damaged 变成 100000/100，只校验格式（数值/max）
	var hp0: bool = String(_bar.get("_hp_label").text).contains("/100")
	print("TEST init ammo0=", ammo0, " hp0=", hp0)
	if _local == 3:
		_player.set("hp", 100)
		_player.take_damage(30)
		var hp_ok: bool = String(_bar.get("_hp_label").text).contains("70/100")
		var flash_ok: bool = float(_bar.get("_dmgflash_t")) > 0.0
		print("TEST damaged hp=", _bar.get("_hp_label").text, " flash_ok=", flash_ok)
	if _local == 5:
		_gun.set("ammo", 5)
		_gun.set("reserve", 3)
		_gun.shot.emit(5, 3)
	var ammo_ok: bool = String(_bar.get("_ammo_label").text) == "5" and String(_bar.get("_ammo_reserve_label").text) == " / 3"
	_gun.reloading.emit()
	var reload_ok: bool = bool(_bar.get("_status_label").visible) and String(_bar.get("_status_label").text).contains("换弹中")
	_gun.hit.emit()
	var hit_ok: bool = bool(_bar.get("_hitmarker").visible)
	print("TEST ammo=", _bar.get("_ammo_label").text, " reload_ok=", reload_ok, " hit_ok=", hit_ok)
	if _local == 10:
		var wolf: Node3D = _main.get_node_or_null("WolfEnemy") as Node3D
		if wolf != null:
			wolf.take_damage(9999)
	if _local == 12:
		var kill_ok: bool = String(_bar.get("_kill_label").text).contains("击杀: 1")
		_player.set("hp", 100)
		_player.take_damage(200)
		var death_ok: bool = bool(_bar.get("_death_panel").visible)
		print("TEST kill=", _bar.get("_kill_label").text, " death_ok=", death_ok)
		_bar.call("set_crosshair_visible", false)
		var ch_hidden: bool = not bool(_bar.get("_ch_up").visible) \
			and not bool(_bar.get("_ch_down").visible) \
			and not bool(_bar.get("_ch_left").visible) \
			and not bool(_bar.get("_ch_right").visible)
		_bar.call("set_crosshair_visible", true)
		var ch_restored: bool = bool(_bar.get("_ch_up").visible)
		print("TEST crosshair_hidden=", ch_hidden, " restored=", ch_restored)
		_main.call("_on_npc_option", "enhance")
		var npc_enhance_ok: bool = _main.get("_enhance_panel") != null \
			and bool(_main.get("_enhance_panel").is_open())
		print("TEST npc_enhance_panel_open=", npc_enhance_ok)
		# 枪械 mods 钩子 + main 装备接线
		var gun2: Node = _main.get_node_or_null("Player/Camera3D/Gun")
		var base_res: int = int(gun2.get("reserve"))
		gun2.apply_item_mods({"reserveDelta": 6})
		var reserve_ok: bool = int(gun2.get("reserve")) == base_res + 6
		gun2.clear_item_mods()
		var reserve_clear: bool = int(gun2.get("reserve")) == base_res
		gun2.apply_item_mods({"damagePercent": 0.6, "enhance_flat_damage": 3})
		var mods_ok: bool = absf(float(gun2.get("_mod_damage_mult")) - 1.6) < 0.001 \
			and int(gun2.get("_mod_damage")) == 3
		gun2.clear_item_mods()
		var clear_ok: bool = absf(float(gun2.get("_mod_damage_mult")) - 1.0) < 0.001
		var equipped_item: Dictionary = _main.get("_equipment").get_item("weapon")
		var wiring_ok := false
		if not equipped_item.is_empty():
			equipped_item["_craftEffects"] = {"damagePercent": 0.1, "attackIntervalDelta": -50}
			_main.call("_refresh_weapon_mods")
			wiring_ok = absf(float(gun2.get("_mod_damage_mult")) - 1.1) < 0.001 \
				and int(gun2.get("_mod_interval_ms")) == -50
		print("TEST gun_mods=", mods_ok, " clear=", clear_ok, " reserve=", reserve_ok, "/", reserve_clear,
			" wiring=", wiring_ok)
		var all_ok: bool = kill_ok and death_ok and ch_hidden and ch_restored \
			and npc_enhance_ok and mods_ok and clear_ok and reserve_ok and reserve_clear and wiring_ok
		quit(0 if all_ok else 1)
		return false
	return false
