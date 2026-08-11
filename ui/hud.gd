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

var _built := false
var _last_scene: Node
var _bound_player: Node
var _bound_gun: Node
var _bind_gun_retries := 0


func _process(_delta: float) -> void:
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
	for id in ["rusty_sword", "g18_pistol", "small_shield", "lunar_helmet", "ring_oracle"]:
		backpack.add_item(id, 1)
	# NPC 面板测试物资（商店/强化/改造/附魔/祭坛），与旧 main 种子一致
	backpack.add_item("enhancement_stone", 3)
	backpack.add_item("reforge_ticket", 2)
	backpack.add_item("magic_dust", 150)
	backpack.add_item("enchant_scroll_heavy", 1)
	backpack.add_item("enchant_scroll_sharp", 1)
	backpack.add_item("enchant_scroll_tarantula", 1)
	backpack.add_item("enchant_scroll_skeleton", 1)
	backpack.add_item("tribute_common", 4)
	backpack.add_item("tribute_uncommon", 2)
	for i in backpack.slots.size():
		if backpack.slots[i] != null and String(backpack.slots[i].get("id", "")) == "rusty_sword":
			equipment.equip_from_backpack(i)
			break
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
	status_bar.add_child(backpack_hud)
	backpack_hud.setup(backpack, equipment, player_status, skillbar)
	var skill_page: Node = backpack_hud.find_child("SkillPage", true, false)
	if skill_page != null and skill_page.has_method("set_progress"):
		skill_page.set_progress(skill_progress)
		if skill_page.has_method("set_db"):
			skill_page.set_db(skills_db)
	# 左侧竖排导航（参考图组件：常驻，点击打开对应面板页签）
	var nav: PanelContainer = load("res://ui/left_nav.gd").new()
	nav.name = "LeftNav"
	nav.set_anchors_and_offsets_preset(Control.PRESET_CENTER_LEFT)
	nav.offset_left = 12
	nav.grow_vertical = Control.GROW_DIRECTION_BOTH
	nav.setup([["status", "角色"], ["equip", "背包"], ["skill", "技能"],
			["codex", "图鉴"], ["quest", "任务"]])
	nav.item_activated.connect(func(id: String) -> void:
		var bph: Control = backpack_hud
		if bph == null:
			return
		if id in ["status", "equip", "skill", "codex"]:
			bph.set_panel_open(true)
			bph.set_tab(id)
		elif status_bar != null:
			status_bar.show_status("任务系统未移植", 1.5))
	status_bar.add_child(nav)


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
	var player := scene.get_node_or_null("Player")
	if player == null:
		player = scene.find_child("Player", true, false)
	if player != null:
		_bound_player = player
		player.damaged.connect(_on_player_damaged)
		player.died.connect(_on_player_died)
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
