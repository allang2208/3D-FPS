extends Node
## 场景通用 HUD（autoload：HUD）：
## 任何场景自动检测——若场景已自建 BackpackHud（main/demo_terrain 旧路径）则不重复挂；
## 否则自动构建 状态栏 + 快捷栏 + 背包面板 + NPC 基础，并接线当前场景的 Player/Gun。
## 数据（背包/装备/属性/技能）挂在 autoload 上，跨场景保留。
## 场景可通过 HUD.skill_triggered / HUD.player_healed 信号接入技能施放与治疗逻辑。

signal skill_triggered(skill_id: String, phase: String)
signal player_healed(hp: int)

var item_db: RefCounted
var backpack
var equipment
var player_status: RefCounted
var skillbar
var skills_db: RefCounted
var skill_progress: RefCounted
var status_bar: CanvasLayer
var backpack_hud: Control
var warehouse
var economy
var _save_queued := false
var _pending_panels: Dictionary = {}
var _ground_items: Array = []
var _inventory_panels: Dictionary = {}
var game_clock := preload("res://ui/game_clock.gd").new()
const Save := preload("res://ui/inventory_save.gd")

var _built := false
var _last_scene: Node
var _bound_player: Node
var _bound_gun: Node
var _bind_gun_retries := 0


func _process(_delta: float) -> void:
	if get_tree().current_scene != null and not get_tree().paused:
		game_clock.advance(_delta)
	var scene := get_tree().current_scene
	if scene == null or scene == _last_scene:
		return
	_last_scene = scene
	if scene.find_child("BackpackHud", true, false) != null:
		return
	_ensure_built()
	_bind_scene(scene)


## 场景可在 _ready 中同步调用：立即为当前场景构建/接线（未就绪则交给 _process 兜底）
func ensure_for_current_scene() -> void:
	var scene := get_tree().current_scene
	if scene == null:
		return
	_last_scene = scene
	if scene.find_child("BackpackHud", true, false) != null:
		return
	_ensure_built()
	_bind_scene(scene)


func _ensure_built() -> void:
	if _built:
		return
	_built = true
	item_db = load("res://ui/item_db.gd").new()
	backpack = load("res://ui/backpack.gd").new(item_db)
	backpack.add_item("hp_potion", 5)
	equipment = load("res://ui/equipment.gd").new(backpack)
	player_status = load("res://ui/player_status.gd").new()
	skillbar = load("res://ui/skillbar.gd").new()
	skills_db = load("res://ui/skills_db.gd").new()
	var sb_skills := {}
	for id in ["fireball", "iceSpike", "lightningStrike", "blizzard"]:
		if skills_db.has_skill(id):
			var def: Dictionary = skills_db.get_def(id).duplicate(true)
			var eff: Dictionary = skills_db.effect(id, player_status.level)
			def["cooldown_s"] = eff.cooldown_s
			def["mp_cost"] = eff.mp_cost
			def["tier"] = 1
			def["two_stage"] = id in ["fireball", "iceSpike"]
			sb_skills[id] = def
	for id in ["stormDomain", "thunderLance", "holyLight", "iceWall", "meteor", "flameArmor", "droneSkill"]:
		if skills_db.has_skill(id):
			var sd: Dictionary = skills_db.get_def(id).duplicate(true)
			var sd_eff: Dictionary = skills_db.effect(id, player_status.level)
			sd["cooldown_s"] = sd_eff.cooldown_s
			sd["mp_cost"] = sd_eff.mp_cost
			sd["tier"] = 1
			sb_skills[id] = sd
	skillbar.setup(sb_skills)
	skillbar.assign(0, "fireball")
	skillbar.assign(1, "iceSpike")
	skillbar.assign(2, "lightningStrike")
	skillbar.assign(3, "blizzard")
	backpack.add_item("mp_potion", 3)
	equipment.slots["weapon"] = item_db.create_instance("rusty_sword")
	equipment.slots["offhand"] = item_db.create_instance("small_shield")
	warehouse = load("res://ui/warehouse.gd").new()
	economy = load("res://ui/economy.gd").new()
	var saved := Save.read_snapshot()
	if not saved.is_empty():
		game_clock.restore(saved.get("game_clock", {}))
		backpack.restore(saved.get("backpack", {}))
		equipment.restore(saved.get("equipment", {}))
		warehouse.restore(saved.get("warehouse", {}))
		economy.gold = int(saved.get("gold", economy.gold))
		_pending_panels = saved.get("pending", {}).duplicate(true)
		_ground_items = saved.get("ground_items", []).duplicate(true)
		for key in saved.get("status", {}):
			player_status.set(key, saved.status[key])
		if saved.has("skills"):
			skillbar.assignments = saved.skills.duplicate(true)
	backpack.changed.connect(request_inventory_save)
	equipment.changed.connect(request_inventory_save)
	warehouse.changed.connect(request_inventory_save)
	economy.changed.connect(func(_gold): request_inventory_save())
	skill_progress = load("res://ui/skill_progress.gd").new(skills_db)
	status_bar = CanvasLayer.new()
	status_bar.name = "StatusBar"
	status_bar.set_script(load("res://ui/status_bar.gd"))
	add_child(status_bar)
	status_bar.set_weapon_name("AK-74")
	status_bar.set_stamina(int(player_status.stamina), player_status.max_stamina())
	status_bar.set_exp(int(player_status.exp), player_status.max_exp())
	backpack_hud = load("res://ui/backpack_hud.gd").new()
	backpack_hud.name = "BackpackHud"
	backpack_hud.player_healed.connect(_on_hud_healed)
	backpack_hud.skill_triggered.connect(func(id: String, phase: String) -> void:
		skill_triggered.emit(id, phase))
	backpack_hud.backpack = backpack
	backpack_hud.equipment = equipment
	status_bar.add_child(backpack_hud)
	backpack_hud.setup(backpack, equipment, player_status, skillbar)
	var skill_page: Node = backpack_hud.find_child("SkillPage", true, false)
	if skill_page != null and skill_page.has_method("set_progress"):
		skill_page.set_progress(skill_progress)
		if skill_page.has_method("set_db"):
			skill_page.set_db(skills_db)


func _bind_scene(scene: Node) -> void:
	if _bound_player != null and is_instance_valid(_bound_player):
		if _bound_player.damaged.is_connected(_on_player_damaged):
			_bound_player.damaged.disconnect(_on_player_damaged)
		if _bound_player.died.is_connected(_on_player_died):
			_bound_player.died.disconnect(_on_player_died)
	if _bound_gun != null and is_instance_valid(_bound_gun):
		if _bound_gun.shot.is_connected(_on_ammo):
			_bound_gun.shot.disconnect(_on_ammo)
		if _bound_gun.reloaded.is_connected(_on_ammo):
			_bound_gun.reloaded.disconnect(_on_ammo)
		if _bound_gun.reloading.is_connected(_on_gun_reloading):
			_bound_gun.reloading.disconnect(_on_gun_reloading)
		if _bound_gun.empty.is_connected(_on_gun_empty):
			_bound_gun.empty.disconnect(_on_gun_empty)
		if _bound_gun.hit.is_connected(_on_gun_hit):
			_bound_gun.hit.disconnect(_on_gun_hit)
		if _bound_gun.ads_changed.is_connected(_on_ads_changed):
			_bound_gun.ads_changed.disconnect(_on_ads_changed)
	_bound_player = null
	var player := scene.get_node_or_null("Player")
	if player == null:
		player = scene.find_child("Player", true, false)
	if player != null:
		_bound_player = player
		player.damaged.connect(_on_player_damaged)
		player.died.connect(_on_player_died)
	for record in _ground_items:
		if record.scene == scene.scene_file_path:
			_spawn_ground_item(record)
	_bind_gun(scene)
	if _bound_gun == null:
		# 枪通常在 HUD 绑定后才加入场景（main._ready 先调 ensure 后建枪），延迟重试直到出现
		_bind_gun_retries = 0
		call_deferred("_retry_bind_gun", scene)


func _bind_gun(scene: Node) -> void:
	var gun := scene.find_child("Gun", true, false)
	if gun == null:
		return
	_bound_gun = gun
	status_bar.reset_ammo_feedback()
	gun.shot.connect(_on_ammo)
	gun.reloaded.connect(_on_ammo)
	gun.reloading.connect(_on_gun_reloading)
	gun.empty.connect(_on_gun_empty)
	gun.hit.connect(_on_gun_hit)
	gun.ads_changed.connect(_on_ads_changed)
	# 同步初始弹药（gun._ready 的首枪发生在绑定前，这里补一次显示）
	_on_ammo(int(gun.get("ammo")), int(gun.get("reserve")))


func _retry_bind_gun(scene: Node) -> void:
	if _bound_gun != null or not is_instance_valid(scene):
		return
	_bind_gun(scene)
	if _bound_gun == null and _bind_gun_retries < 300:
		_bind_gun_retries += 1
		call_deferred("_retry_bind_gun", scene)


## ---- 信号转发 / HUD 更新 ----

func _on_player_damaged(hp: int) -> void:
	if status_bar != null:
		var m := int(_bound_player.get("max_hp")) if _bound_player != null else 100
		status_bar.set_hp(hp, m)
	if player_status != null:
		player_status.set_hp(hp)


func _on_player_died() -> void:
	if status_bar != null:
		status_bar.show_death()


func _on_hud_healed(hp: int) -> void:
	if player_status != null:
		player_status.set_hp(hp)
	player_healed.emit(hp)


func _on_ammo(ammo: int, reserve: int) -> void:
	if status_bar != null:
		status_bar.set_ammo(ammo, reserve)


func _on_gun_reloading() -> void:
	if status_bar != null:
		status_bar.show_status("换弹中…", 1.5)


func _on_gun_empty() -> void:
	if status_bar != null:
		status_bar.show_status("没子弹 · 按 R 换弹", 1.2)


func _on_gun_hit() -> void:
	if status_bar != null:
		status_bar.hitmark()


func _on_ads_changed(active: bool) -> void:
	if status_bar != null and status_bar.has_method("set_crosshair_visible"):
		status_bar.set_crosshair_visible(not active)

func request_inventory_save() -> void:
	if _save_queued or not _built or warehouse == null:
		return
	_save_queued = true
	call_deferred("save_inventory")

func register_inventory_panel(key: String, panel: Node) -> void:
	_inventory_panels[key] = weakref(panel)
	if _pending_panels.has(key):
		panel.restore_inventory_state(_pending_panels[key])
	panel.tree_exiting.connect(func():
		_pending_panels[key] = panel.inventory_state()
		_inventory_panels.erase(key)
		request_inventory_save())

func save_inventory() -> Error:
	_save_queued = false
	if warehouse == null:
		return ERR_UNCONFIGURED
	for key in _inventory_panels:
		var panel: Node = _inventory_panels[key].get_ref()
		if panel != null:
			_pending_panels[key] = panel.inventory_state()
	var status := {}
	for key in ["level", "exp", "str", "dex", "intt", "con", "wis", "luck", "attr_points"]:
		status[key] = player_status.get(key)
	var snapshot := {"game_clock": game_clock.serialize(), "version": 1, "backpack": backpack.serialize(), "equipment": equipment.serialize(),
		"warehouse": warehouse.serialize(), "gold": economy.gold, "pending": _pending_panels.duplicate(true),
		"status": status, "skills": skillbar.assignments.duplicate(true), "ground_items": _ground_items.duplicate(true)}
	var error := Save.write_snapshot(snapshot)
	if error != OK:
		push_error("Inventory save failed: %s" % error_string(error))
	return error

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		if warehouse != null:
			save_inventory()

func drop_inventory_item(slot: int, item: Dictionary) -> bool:
	if not is_instance_valid(_bound_player) or not is_instance_valid(get_tree().current_scene):
		return false
	if slot < 0 or slot >= backpack.slots.size() or backpack.slots[slot] == null or backpack.slots[slot].instance_id != item.instance_id:
		return false
	var pos: Vector3 = _bound_player.global_position
	var record := {"item": item.duplicate(true), "scene": get_tree().current_scene.scene_file_path, "position": pos}
	_ground_items.append(record)
	backpack.slots[slot] = null
	_spawn_ground_item(record)
	backpack.changed.emit()
	return true

func drop_equipped_item(key: String, item: Dictionary) -> bool:
	if not is_instance_valid(_bound_player) or not is_instance_valid(get_tree().current_scene):
		return false
	var current: Dictionary = equipment.get_item(key)
	if current.is_empty() or current != item or equipment.is_locked(key):
		return false
	var record := {"item": current.duplicate(true), "scene": get_tree().current_scene.scene_file_path, "position": _bound_player.global_position}
	_ground_items.append(record)
	equipment.slots[key] = null
	_spawn_ground_item(record)
	equipment.changed.emit()
	return true

func _spawn_ground_item(record: Dictionary) -> void:
	var node := preload("res://ui/inventory_ground_item.gd").new()
	node.record = record
	node.inventory_host = self
	get_tree().current_scene.add_child(node)
	node.global_position = record.position

func pickup_inventory_item(record: Dictionary) -> bool:
	if not _ground_items.has(record) or not backpack.add_instance(record.item):
		backpack_hud.flash_status("背包已满")
		return false
	_ground_items.erase(record)
	request_inventory_save()
	return true

func _ready() -> void:
	get_window().gui_embed_subwindows = true
	get_window().size_changed.connect(_sync_ui_resolution)
	_sync_ui_resolution()
	get_viewport().gui_drag_threshold = 6
	if DisplayServer.get_name() != "headless":
		for entry in [["normal-pointer", Input.CURSOR_ARROW, Vector2(3, 2)], ["click-hand", Input.CURSOR_POINTING_HAND, Vector2(20, 2)], ["grab-hand", Input.CURSOR_DRAG, Vector2(27, 33)], ["grabbing-hand", Input.CURSOR_CAN_DROP, Vector2(25, 29)]]:
			var path: String = "res://assets/original_ui/assets/ui/cursors/%s-cold-steel.png" % entry[0]
			Input.set_custom_mouse_cursor(load(path), entry[1], entry[2])

func _sync_ui_resolution() -> void:
	get_window().content_scale_size = get_window().size

func _exit_tree() -> void:
	preload("res://ui/style.gd").release_fonts()
	if DisplayServer.get_name() != "headless":
		for shape in [Input.CURSOR_ARROW, Input.CURSOR_POINTING_HAND, Input.CURSOR_DRAG, Input.CURSOR_CAN_DROP]:
			Input.set_custom_mouse_cursor(null, shape)

func _input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:
		return
	if event.physical_keycode != KEY_ALT or event.location != KEY_LOCATION_LEFT:
		return
	if not is_instance_valid(_bound_player) or bool(_bound_player.get("is_dead")):
		return
	get_viewport().set_input_as_handled()
	if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		return
	# Keep the cursor available while a modal panel or drag operation owns it.
	if get_viewport().gui_is_dragging() or (is_instance_valid(backpack_hud) and backpack_hud._panel_open):
		return
	for ref in _inventory_panels.values():
		var panel = ref.get_ref()
		if panel != null and panel.is_open():
			return
	if is_instance_valid(status_bar) and is_instance_valid(status_bar.event_timeline):
		status_bar.event_timeline.close_popover()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
