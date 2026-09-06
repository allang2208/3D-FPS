extends Node3D
## 无尽轮回 · 3D FPS（Godot 4.7）
## 场景代码搭建：环境 / 光照 / 地面 / 墙体 / 玩家 / HUD / 三只敌人（黑狼 GLB + 僵尸犬 + 蜘蛛）

const WOLF_GLB := "res://assets/models/black_wolf_trellis.glb"  # 骨架烘焙源（tools/bake_wolf_rig.gd）
const WOLF_RIGGED := "res://assets/models/black_wolf_rigged.scn"  # 烘焙产物：18骨骼+蒙皮黑狼（备用管线）
const WOLF_QUATERNIUS := "res://assets/models/wolf_quaternius.gltf"  # CC0 动画狼（现役）
const FireballScript := preload("res://scripts/fireball.gd")
const IceSpikeScript := preload("res://scripts/ice_spike.gd")
const LightningScript := preload("res://scripts/lightning.gd")
const WeaponFormula := preload("res://ui/weapon_formula.gd")
const AreaSkillScript := preload("res://scripts/area_skill.gd")
const ThunderLanceScript := preload("res://scripts/thunder_lance.gd")
const LoadingScreenScript := preload("res://ui/loading_screen.gd")

var _player: Node3D
var _gun: Node3D
var _status_bar: CanvasLayer
var _npc_bar: CanvasLayer
var _item_db
var _economy
var _warehouse
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
var _hud_retries := 0

func _ready() -> void:
	add_child(LoadingScreenScript.new())  # 注册全局加载界面（进度条）
	_build_environment()
	_build_ground()
	_build_walls()
	HUD.ensure_for_current_scene()
	call_deferred("_setup_hud_bridge")
	_build_player()
	_build_enemies()
	_build_portal()
	_build_voxel_lab_portal()

func _process(_delta: float) -> void:
	if _player_dead and Input.is_key_pressed(KEY_R):
		LoadingScreenScript.reload_scene()

func _build_environment() -> void:
	var lighting := preload("res://scripts/world_lighting.gd")
	add_child(lighting.create_environment())
	add_child(lighting.create_sun())

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
	# 3D 音效监听点（技能/枪声以玩家相机为听点）
	var listener := AudioListener3D.new()
	cam.add_child(listener)
	var cfx := Node3D.new()
	cfx.name = "CameraFx"
	cfx.set_script(load("res://scripts/camera_fx.gd"))
	cam.add_child(cfx)
	var gun := Node3D.new()
	gun.name = "Gun"
	gun.position = Vector3(0.28, -0.26, -0.5)
	gun.set_script(load("res://scripts/gun.gd"))
	cam.add_child(gun)
	_gun = gun
	add_child(player)
	_player = player
	_refresh_weapon_mods()

## 装备武器强化/改造/附魔 -> 枪械与玩家攻击生效（weapon_formula 计算）
func _refresh_weapon_mods() -> void:
	if _gun == null or _equipment == null:
		return
	var item: Dictionary = _equipment.get_item("weapon")
	if item.is_empty():
		item = _equipment.get_item("weapon2")
	if item.is_empty():
		_gun.clear_item_mods()
		if _player_status != null:
			_player_status.set_weapon_atk(0)
		return
	_gun.apply_item_mods(WeaponFormula.gun_mods_from_item(item))
	if _player_status != null:
		var attrs := {}
		for k in ["str", "dex", "con", "wis", "luck"]:
			attrs[k] = int(_player_status.get(k))
		attrs["int"] = int(_player_status.get("intt"))
		_player_status.set_weapon_atk(WeaponFormula.compute_weapon_atk(
			item, int(item.get("enhanceLevel", 0)), attrs))

## HUD 由 autoload(HUD) 全局提供（状态栏/快捷栏/背包唯一、数据跨场景保留）；
## 本场景只做桥接：本地数据别名指向 HUD + NPC 栏/子面板 + 技能/治疗信号。
func _setup_hud_bridge() -> void:
	if HUD.backpack == null:
		# 防递归风暴：backpack 由 autoload 的 _process 兜底初始化，限次重试后放弃等待 autoload 自行接线
		_hud_retries += 1
		if _hud_retries < 300:
			call_deferred("_setup_hud_bridge")
		return
	_hud_retries = 0
	if not HUD.skill_triggered.is_connected(_on_skill_triggered):
		HUD.skill_triggered.connect(_on_skill_triggered)
	if not HUD.player_healed.is_connected(_on_player_healed):
		HUD.player_healed.connect(_on_player_healed)
	_status_bar = HUD.status_bar
	_item_db = HUD.item_db
	_backpack = HUD.backpack
	_equipment = HUD.equipment
	_player_status = HUD.player_status
	_skillbar = HUD.skillbar
	_skills_db = HUD.skills_db
	_skill_progress = HUD.skill_progress
	_backpack_hud = HUD.backpack_hud
	var npc_bar := CanvasLayer.new()
	npc_bar.name = "NpcBar"
	npc_bar.set_script(load("res://ui/npc_bar.gd"))
	add_child(npc_bar)
	npc_bar.option_pressed.connect(_on_npc_option)
	npc_bar.close_requested.connect(_on_npc_closed)
	_npc_bar = npc_bar
	_build_npc_panels()
	_refresh_weapon_mods()

## 技能触发分发（火球/冰锥二段式 + 闪电单段）
func _on_skill_triggered(skill_id: String, phase: String) -> void:
	if _player == null or _player_status == null or _skills_db == null:
		# HUD 桥接未就绪时静默忽略（避免 Nil 崩溃；桥接重试完成后自然可用）
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
	# 黑狼换用 CC0 Quaternius 动画狼（关键帧动画，scripts/wolf_anim.gd 驱动）；
	# 旧 TRELLIS/UniRig 烘焙管线保留（WOLF_RIGGED），可回退
	var wolf_model: Node3D = load(WOLF_QUATERNIUS).instantiate()
	wolf_model.set_script(load("res://scripts/wolf_anim.gd"))
	_build_enemy("WolfEnemy", wolf_model, Vector3(3, 0, -4), {
		"hp": 85, "chase": 3.5, "dmg": 15, "radius": 0.55, "height": 1.0,
		"offset_y": 0.0, "bob": 0.0, "scale": 0.3,  # 原模脚底 y=0，走路起伏由动画负责
	})
	# 测试期：只保留黑狼，僵尸犬/蜘蛛暂时移除（EnemyModels 保留供后续恢复）
	var zombie: Node3D = load("res://scenes/enemies/ordinary_zombie.tscn").instantiate()
	zombie.position = Vector3(-3, 0, -4)
	add_child(zombie)
	zombie.setup(_player, _on_enemy_killed)

	var ore_spider: Node3D = load("res://scenes/enemies/ore_spider.tscn").instantiate()
	ore_spider.position = Vector3(9, 0, -5)
	add_child(ore_spider)
	ore_spider.setup(_player, _on_enemy_killed)

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
	_economy = HUD.economy
	_warehouse = HUD.warehouse
	var NpcPanels := load("res://ui/npc_panels.gd")
	_panels = NpcPanels.build(self, _item_db, _backpack, _equipment, _economy, _npc_bar, _warehouse, _player_status)
	_shop_panel = _panels.get("shop")
	_enhance_panel = _panels.get("enhance")
	_craft_panel = _panels.get("craft")
	_enchant_panel = _panels.get("enchant")
	_quest_panel = _panels.get("quest")
	_fusion_panel = _panels.get("fusion")
	_expedition_panel = _panels.get("expedition")
	_quest_panel.teleport_requested.connect(func(_quest_id: String) -> void: _on_teleport_requested())
	_expedition_panel.depart_requested.connect(_on_depart_requested)
	_equipment.changed.connect(_refresh_weapon_mods)
	_refresh_weapon_mods()

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
	if _status_bar != null:
		_status_bar.set_hp(hp, int(_player.get("max_hp")))
		_status_bar.damage_flash()
	if _player_status != null:
		_player_status.set_hp(hp)

func _on_player_healed(hp: int) -> void:
	if _status_bar != null:
		_status_bar.set_hp(hp, int(_player.get("max_hp")))
	if _player_status != null:
		_player_status.set_hp(hp)

func _on_player_died() -> void:
	_player_dead = true
	if _status_bar != null:
		_status_bar.show_death()

func _on_enemy_killed() -> void:
	_kills += 1
	if _status_bar != null:
		_status_bar.set_kills(_kills)
	if _player_status != null:
		_player_status.set_kills(_kills)

func _build_voxel_lab_portal() -> void:
	var portal := preload("res://scripts/voxel_lab/lab_portal.gd").new()
	portal.name = "VoxelLabPortal"
	portal.target_scene = "res://scenes/voxel_lab.tscn"
	portal.label_text = "体素试验场\n走入测试挖掘 / 建造"
	portal.portal_color = Color(0.3, 0.9, 0.5)
	portal.position = Vector3(4.5, 1.4, 3.5)
	add_child(portal)
