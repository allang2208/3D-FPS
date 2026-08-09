extends Node3D
## 无尽轮回 · 3D FPS（Godot 4.7）
## 场景代码搭建：环境 / 光照 / 地面 / 墙体 / 玩家 / HUD / 三只敌人（黑狼 GLB + 僵尸犬 + 蜘蛛）

const WOLF_GLB := "res://assets/models/black_wolf_trellis.glb"  # 骨架烘焙源（tools/bake_wolf_rig.gd）
const WOLF_RIGGED := "res://assets/models/black_wolf_rigged.scn"  # 烘焙产物：18骨骼+蒙皮黑狼
const FireballScript := preload("res://scripts/fireball.gd")
const IceSpikeScript := preload("res://scripts/ice_spike.gd")
const LightningScript := preload("res://scripts/lightning.gd")
const AreaSkillScript := preload("res://scripts/area_skill.gd")
const ThunderLanceScript := preload("res://scripts/thunder_lance.gd")
const LoadingScreenScript := preload("res://ui/loading_screen.gd")

var _player: Node3D
var _gun: Node3D
var _status_bar: CanvasLayer
var _npc_bar: CanvasLayer
var _item_db
var _economy
var _shop_panel
var _enhance_panel
var _craft_panel
var _enchant_panel
var _quest_panel
var _fusion_panel
var _expedition_panel
var _panels := {}
var _backpack_hud: Control
var _backpack
var _equipment
var _player_status
var _skillbar
var _skills_db
var _skill_progress
var _hover_fireball: Node3D
var _hover_ice_spike: Node3D
var _player_dead := false
var _kills := 0

func _ready() -> void:
	add_child(LoadingScreenScript.new())  # 注册全局加载界面（进度条）
	_build_environment()
	_build_ground()
	_build_walls()
	_build_hud()
	_build_player()
	_build_enemies()
	_build_portal()

func _process(_delta: float) -> void:
	if _player_dead and Input.is_key_pressed(KEY_R):
		LoadingScreenScript.reload_scene()

func _build_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var proc := ProceduralSkyMaterial.new()
	proc.sky_top_color = Color(0.16, 0.22, 0.38)
	proc.sky_horizon_color = Color(0.28, 0.32, 0.44)
	proc.ground_horizon_color = Color(0.08, 0.10, 0.16)
	proc.ground_bottom_color = Color(0.03, 0.04, 0.06)
	sky.sky_material = proc
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.7
	env.fog_enabled = true
	env.fog_light_color = Color(0.35, 0.4, 0.55)
	env.fog_density = 0.006
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-48, -28, 0)
	sun.light_energy = 1.2
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 60.0
	add_child(sun)

func _build_ground() -> void:
	var ground := StaticBody3D.new()
	ground.name = "Ground"
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(30, 1, 30)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.12, 0.14, 0.18)
	mat.roughness = 0.95
	box.material = mat
	mesh.mesh = box
	mesh.position = Vector3(0, -0.5, 0)
	ground.add_child(mesh)
	var col := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(30, 1, 30)
	col.shape = shape
	col.position = Vector3(0, -0.5, 0)
	ground.add_child(col)
	add_child(ground)

func _build_walls() -> void:
	_build_wall(Vector3(0, 1.5, -15), Vector3(30, 3, 1), Color(0.22, 0.16, 0.12))
	_build_wall(Vector3(0, 1.5, 15), Vector3(30, 3, 1), Color(0.22, 0.16, 0.12))
	_build_wall(Vector3(-15, 1.5, 0), Vector3(1, 3, 30), Color(0.22, 0.16, 0.12))
	_build_wall(Vector3(15, 1.5, 0), Vector3(1, 3, 30), Color(0.22, 0.16, 0.12))
	_build_wall(Vector3(4, 0.75, -2), Vector3(2, 1.5, 2), Color(0.18, 0.2, 0.24))
	_build_wall(Vector3(-5, 0.75, 3), Vector3(2, 1.5, 2), Color(0.18, 0.2, 0.24))
	_build_wall(Vector3(-1, 0.75, -7), Vector3(2, 1.5, 2), Color(0.18, 0.2, 0.24))

func _build_wall(pos: Vector3, size: Vector3, color: Color) -> void:
	var body := StaticBody3D.new()
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.92
	box.material = mat
	mesh.mesh = box
	mesh.position = pos
	body.add_child(mesh)
	var col := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	col.shape = shape
	col.position = pos
	body.add_child(col)
	add_child(body)

func _build_player() -> void:
	var player := CharacterBody3D.new()
	player.name = "Player"
	player.position = Vector3(0, 0.2, 8)
	player.set_script(load("res://scripts/player.gd"))
	player.damaged.connect(_on_player_damaged)
	player.died.connect(_on_player_died)
	var col := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.35
	cap.height = 1.7
	col.shape = cap
	player.add_child(col)
	var cam := Camera3D.new()
	cam.name = "Camera3D"
	cam.position = Vector3(0, 1.62, 0)
	cam.fov = 75.0
	player.add_child(cam)
	var cfx := Node3D.new()
	cfx.name = "CameraFx"
	cfx.set_script(load("res://scripts/camera_fx.gd"))
	cam.add_child(cfx)
	var gun := Node3D.new()
	gun.name = "Gun"
	gun.position = Vector3(0.28, -0.26, -0.5)
	gun.set_script(load("res://scripts/gun.gd"))
	gun.shot.connect(_on_ammo)
	gun.reloaded.connect(_on_ammo)
	gun.reloading.connect(_on_reloading)
	gun.empty.connect(_on_empty)
	gun.hit.connect(_on_hit)
	gun.ads_changed.connect(_on_ads_changed)
	cam.add_child(gun)
	_gun = gun
	add_child(player)
	_player = player

func _build_hud() -> void:
	var bar := CanvasLayer.new()
	bar.name = "StatusBar"
	bar.set_script(load("res://ui/status_bar.gd"))
	add_child(bar)
	_status_bar = bar
	_status_bar.set_weapon_name("AK-74")
	_build_backpack_hud(bar)
	var npc_bar := CanvasLayer.new()
	npc_bar.name = "NpcBar"
	npc_bar.set_script(load("res://ui/npc_bar.gd"))
	add_child(npc_bar)
	npc_bar.option_pressed.connect(_on_npc_option)
	npc_bar.close_requested.connect(_on_npc_closed)
	_npc_bar = npc_bar
	_build_npc_panels()

## 背包栏迁移：底部快捷栏（1~4）+ Tab/B 背包面板
func _build_backpack_hud(parent: Node) -> void:
	_item_db = load("res://ui/item_db.gd").new()
	_backpack = load("res://ui/backpack.gd").new(_item_db)
	# 初始背包沿用旧版默认（治疗药水 ×5）；MP 系统未实装，暂不发放魔力药水
	_backpack.add_item("hp_potion", 5)
	# 装备栏 + 演示种子（沿用旧版初始装备：主手生锈长剑；背包放 G18/小圆盾/铁盔/戒指）
	_equipment = load("res://ui/equipment.gd").new(_backpack)
	_player_status = load("res://ui/player_status.gd").new()
	_skillbar = load("res://ui/skillbar.gd").new()
	# 技能库：火球 Q / 冰锥 E / 闪电 X，defs 补 skillbar 需要的 cooldown_s/mp_cost/tier
	var skills_db = load("res://ui/skills_db.gd").new()
	_skills_db = skills_db
	_skill_progress = load("res://ui/skill_progress.gd").new(skills_db)
	var sb_skills := {}
	if skills_db.has_skill("fireball"):
		var fb: Dictionary = skills_db.get_def("fireball").duplicate(true)
		var eff: Dictionary = skills_db.effect("fireball", _player_status.level)
		fb["cooldown_s"] = eff.cooldown_s
		fb["mp_cost"] = eff.mp_cost
		fb["tier"] = 1
		fb["two_stage"] = true  # 原版火球：凝聚绕身 → 第二次投掷
		sb_skills["fireball"] = fb
	if skills_db.has_skill("iceSpike"):
		var ic: Dictionary = skills_db.get_def("iceSpike").duplicate(true)
		var ice_eff: Dictionary = skills_db.effect("iceSpike", _player_status.level)
		ic["cooldown_s"] = ice_eff.cooldown_s
		ic["mp_cost"] = ice_eff.mp_cost
		ic["tier"] = 1
		ic["two_stage"] = true  # 原版冰锥：凝聚环绕 → 第二次齐射
		sb_skills["iceSpike"] = ic
	if skills_db.has_skill("lightningStrike"):
		var ls: Dictionary = skills_db.get_def("lightningStrike").duplicate(true)
		var ls_eff: Dictionary = skills_db.effect("lightningStrike", _player_status.level)
		ls["cooldown_s"] = ls_eff.cooldown_s
		ls["mp_cost"] = ls_eff.mp_cost
		ls["tier"] = 1
		sb_skills["lightningStrike"] = ls
	for id in ["stormDomain", "thunderLance", "holyLight", "iceWall", "blizzard", "meteor", "flameArmor", "droneSkill"]:
		if skills_db.has_skill(id):
			var sd: Dictionary = skills_db.get_def(id).duplicate(true)
			var sd_eff: Dictionary = skills_db.effect(id, _player_status.level)
			sd["cooldown_s"] = sd_eff.cooldown_s
			sd["mp_cost"] = sd_eff.mp_cost
			sd["tier"] = 1
			sb_skills[id] = sd
	_skillbar.setup(sb_skills)
	_skillbar.assign(0, "fireball")
	_skillbar.assign(1, "iceSpike")
	_skillbar.assign(2, "lightningStrike")
	_skillbar.assign(3, "blizzard")
	_backpack.add_item("rusty_sword", 1)
	_backpack.add_item("g18_pistol", 1)
	_backpack.add_item("small_shield", 1)
	_backpack.add_item("lunar_helmet", 1)
	_backpack.add_item("ring_oracle", 1)
	# NPC 面板测试物资（商店/强化/改造/附魔/祭坛）
	_backpack.add_item("enhancement_stone", 3)
	_backpack.add_item("reforge_ticket", 2)
	_backpack.add_item("magic_dust", 150)
	_backpack.add_item("enchant_scroll_heavy", 1)
	_backpack.add_item("enchant_scroll_sharp", 1)
	_backpack.add_item("enchant_scroll_tarantula", 1)
	_backpack.add_item("enchant_scroll_skeleton", 1)
	_backpack.add_item("tribute_common", 4)
	_backpack.add_item("tribute_uncommon", 2)
	for i in _backpack.slots.size():
		if _backpack.slots[i] != null and String(_backpack.slots[i].get("id", "")) == "rusty_sword":
			_equipment.equip_from_backpack(i)
			break
	var hud = load("res://ui/backpack_hud.gd").new()
	hud.name = "BackpackHud"
	hud.player_healed.connect(_on_player_healed)
	hud.skill_triggered.connect(_on_skill_triggered)
	parent.add_child(hud)
	hud.setup(_backpack, _equipment, _player_status, _skillbar)
	# 修炼进度注入技能面板（不改 UI 线文件的 setup 签名）
	var skill_page: Node = hud.get_node_or_null("SkillPage")
	if skill_page != null and skill_page.has_method("set_progress"):
		skill_page.set_progress(_skill_progress)
		if skill_page.has_method("set_db"):
			skill_page.set_db(_skills_db)
	_backpack_hud = hud

## 技能触发分发（火球/冰锥二段式 + 闪电单段）
func _on_skill_triggered(skill_id: String, phase: String) -> void:
	if _player == null:
		return
	match skill_id:
		"fireball":
			_on_fireball_trigger(phase)
		"iceSpike":
			_on_ice_spike_trigger(phase)
		"lightningStrike":
			_on_lightning_trigger()
		"stormDomain", "thunderLance", "holyLight", "iceWall", "meteor", "flameArmor", "droneSkill":
			_on_area_skill_trigger(skill_id)
		"blizzard":
			_on_area_skill_trigger(skill_id)
		_:
			_flash_skill_missing(skill_id)

func _on_fireball_trigger(phase: String) -> void:
	if phase == "launch":
		if _hover_fireball != null and is_instance_valid(_hover_fireball):
			var cam := _player.get_node_or_null("Camera3D") as Camera3D
			if cam != null:
				_hover_fireball.launch(-cam.global_transform.basis.z)
		return
	# spawn：生成绕身火球
	_hover_fireball = FireballScript.spawn_hover(get_tree().current_scene, _player,
		_player_status.level, _player_status.matk(), _player_status.intt)
	if _hover_fireball != null:
		_hover_fireball.consumed.connect(_on_fireball_consumed)
		_hover_fireball.cast_finished.connect(_on_skill_exp.bind("fireball"))

func _on_fireball_consumed() -> void:
	_hover_fireball = null
	if _skillbar != null:
		_skillbar.consume_active("fireball")

## 冰锥二段式：第一次凝聚 N 颗环绕，第二次齐射
func _on_ice_spike_trigger(phase: String) -> void:
	if phase == "launch":
		if _hover_ice_spike != null and is_instance_valid(_hover_ice_spike):
			var cam := _player.get_node_or_null("Camera3D") as Camera3D
			if cam != null:
				_hover_ice_spike.launch(-cam.global_transform.basis.z)
		return
	var eff: Dictionary = _skills_db.effect("iceSpike", _player_status.level)
	_hover_ice_spike = IceSpikeScript.spawn_hover(get_tree().current_scene, _player,
		_player_status.level, _player_status.matk(), _player_status.intt, int(eff.spike_count))
	if _hover_ice_spike != null:
		_hover_ice_spike.consumed.connect(_on_ice_spike_consumed)
		_hover_ice_spike.cast_finished.connect(_on_skill_exp.bind("iceSpike"))

func _on_ice_spike_consumed() -> void:
	_hover_ice_spike = null
	if _skillbar != null:
		_skillbar.consume_active("iceSpike")

## 闪电单段：锁定 + 传导；失败回滚 MP/冷却（旧版"无目标不消耗"语义）
func _on_lightning_trigger() -> void:
	var eff: Dictionary = _skills_db.effect("lightningStrike", _player_status.level)
	var res: Dictionary = LightningScript.cast(get_tree().current_scene, _player,
		_player_status.level, _player_status.matk(), _player_status.intt, eff)
	if bool(res.get("ok", false)):
		if _skill_progress != null:
			_skill_progress.award("lightningStrike", int(res.get("hits", 0)), int(res.get("kills", 0)))
		return
	_player_status.set_mp(_player_status.mp + int(eff.mp_cost))
	if _skillbar != null:
		_skillbar.set_cooldown("lightningStrike", 0.0)
	if _backpack_hud != null and _backpack_hud.has_method("flash_status"):
		_backpack_hud.flash_status("闪电：范围内无目标！")

## 技能修炼经验上报（cast_finished(hits, kills) → award）
func _on_skill_exp(hits: int, kills: int, skill_id: String) -> void:
	if _skill_progress != null:
		_skill_progress.award(skill_id, hits, kills)

## 区域/持续型技能 + 贯穿雷枪触发
func _on_area_skill_trigger(skill_id: String) -> void:
	var eff: Dictionary = _skills_db.effect_raw(skill_id, _player_status.level)
	var on_done := _on_skill_exp.bind(skill_id)
	if skill_id == "thunderLance":
		ThunderLanceScript.cast(get_tree().current_scene, _player,
			_player_status.level, _player_status.matk(), _player_status.intt, eff, on_done)
	else:
		AreaSkillScript.cast(get_tree().current_scene, _player,
			_player_status.level, _player_status.matk(), _player_status.intt, skill_id, eff, on_done)

func _flash_skill_missing(skill_id: String) -> void:
	if _backpack_hud != null and _backpack_hud.has_method("flash_status"):
		_backpack_hud.flash_status("技能未移植（%s）" % skill_id)

func _build_enemies() -> void:
	# 黑狼用烘焙好的骨骼模型（WolfRig），原 GLB 是静态网格，烘焙见 tools/bake_wolf_rig.gd
	var wolf_model: Node3D = load(WOLF_RIGGED).instantiate()
	_build_enemy("WolfEnemy", wolf_model, Vector3(3, 0, -4), {
		"hp": 85, "chase": 3.5, "dmg": 15, "radius": 0.55, "height": 1.0,
		"offset_y": 0.25, "bob": 0.05,  # CuMesh 新狼脚底 y=-0.246，offset 0.25 落地
	})
	# 测试期：只保留黑狼，僵尸犬/蜘蛛暂时移除（EnemyModels 保留供后续恢复）

func _build_enemy(enemy_name: String, model: Node3D, pos: Vector3, cfg: Dictionary) -> void:
	var enemy := CharacterBody3D.new()
	enemy.name = enemy_name
	enemy.position = pos
	enemy.set_script(load("res://scripts/enemy.gd"))
	enemy.set("max_hp", int(cfg["hp"]))
	enemy.set("chase_speed", float(cfg["chase"]))
	enemy.set("contact_damage", int(cfg["dmg"]))
	enemy.set("model_offset_y", float(cfg["offset_y"]))
	enemy.set("walk_bob_amp", float(cfg["bob"]))
	var col := CollisionShape3D.new()
	col.name = "Collision"
	var cap := CapsuleShape3D.new()
	cap.radius = float(cfg["radius"])
	cap.height = float(cfg["height"])
	col.shape = cap
	col.position = Vector3(0, float(cfg["height"]) * 0.5, 0)
	enemy.add_child(col)
	model.name = "Model"
	model.scale = Vector3.ONE * float(cfg.get("scale", 1.0))
	model.position.y = float(cfg["offset_y"])
	enemy.add_child(model)
	add_child(enemy)
	enemy.setup(_player, _on_enemy_killed)

## 传送门：从基地进入地形演示旷野
func _build_portal() -> void:
	var portal: Node = load("res://scripts/portal.gd").new()
	portal.name = "Portal"
	portal.target_scene = "res://scenes/demo_terrain.tscn"
	portal.label_text = "传送门 · 进入旷野"
	portal.position = Vector3(0, 1.4, 0)
	add_child(portal)

func _on_ammo(ammo: int, reserve_left: int) -> void:
	_status_bar.set_ammo(ammo, reserve_left)

func _on_hit() -> void:
	_status_bar.hitmark()

func _on_ads_changed(active: bool) -> void:
	if _status_bar != null and _status_bar.has_method("set_crosshair_visible"):
		_status_bar.set_crosshair_visible(not active)

func _on_reloading() -> void:
	_status_bar.show_status("换弹中…", 1.5)

func _on_empty() -> void:
	_status_bar.show_status("没子弹 · 按 R 换弹", 1.2)

func _on_reloaded(_ammo: int, _reserve: int) -> void:
	_status_bar.clear_status()

## NPC 栏选项分发：子面板系统未迁移前先给状态提示；info/help 沿用旧版就地回话
func _on_npc_option(id: String) -> void:
	if _npc_bar == null or _status_bar == null:
		return
	match id:
		"shop":
			_open_npc_panel(_shop_panel)
		"enhance":
			_open_npc_panel(_enhance_panel)
		"craft":
			_open_npc_panel(_craft_panel)
		"enchant":
			_open_npc_panel(_enchant_panel)
		"quest":
			_open_npc_panel(_quest_panel)
		"teleport":
			_on_teleport_requested()
		"expedition":
			_open_npc_panel(_expedition_panel)
		"fusion":
			_open_npc_panel(_fusion_panel)
		"info":
			_npc_bar.set_text("关于各个世界的信息正在收集中……目前可以告诉您的是，时空裂隙的出现频率越来越高，请务必小心。")
		"help":
			_npc_bar.set_text("帮助功能正在开发中，敬请期待。您可以先尝试接受任务前往其他世界探险。")
		_:
			_status_bar.show_status("NPC 选项待接入：%s" % id, 1.5)

func _on_npc_closed() -> void:
	if _status_bar != null:
		_status_bar.clear_status()

## NPC 子面板：打开时收起对话框，关闭后回到对话框（旧版 exitCompactMode）
func _build_npc_panels() -> void:
	_economy = load("res://ui/economy.gd").new()
	var NpcPanels := load("res://ui/npc_panels.gd")
	_panels = NpcPanels.build(self, _item_db, _backpack, _equipment, _economy, _npc_bar)
	_shop_panel = _panels.get("shop")
	_enhance_panel = _panels.get("enhance")
	_craft_panel = _panels.get("craft")
	_enchant_panel = _panels.get("enchant")
	_quest_panel = _panels.get("quest")
	_fusion_panel = _panels.get("fusion")
	_expedition_panel = _panels.get("expedition")
	_quest_panel.teleport_requested.connect(func(_quest_id: String) -> void: _on_teleport_requested())
	_expedition_panel.depart_requested.connect(_on_depart_requested)

func _open_npc_panel(panel) -> void:
	if panel == null:
		return
	_npc_bar.close()
	panel.open_panel()

func _on_teleport_requested() -> void:
	if _status_bar != null:
		_status_bar.show_status("任务场景未迁移，传送暂不可用", 2.0)

func _on_depart_requested(items: Array) -> void:
	if _backpack != null:
		for it in items:
			_backpack.add_item(String(it.get("id", "")), 1)
	if _status_bar != null:
		_status_bar.show_status("地牢世界未迁移，出征暂不可用（祭品已返还）", 2.5)

func _on_player_damaged(hp: int) -> void:
	_status_bar.set_hp(hp, int(_player.get("max_hp")))
	_status_bar.damage_flash()
	if _player_status != null:
		_player_status.set_hp(hp)

func _on_player_healed(hp: int) -> void:
	_status_bar.set_hp(hp, int(_player.get("max_hp")))
	if _player_status != null:
		_player_status.set_hp(hp)

func _on_player_died() -> void:
	_player_dead = true
	_status_bar.show_death()

func _on_enemy_killed() -> void:
	_kills += 1
	_status_bar.set_kills(_kills)
	if _player_status != null:
		_player_status.set_kills(_kills)
