extends Node3D
## 无尽轮回 · 3D FPS（Godot 4.7）
## 场景代码搭建：环境 / 光照 / 地面 / 墙体 / 玩家 / HUD / 三只敌人（黑狼 GLB + 僵尸犬 + 蜘蛛）

const WOLF_GLB := "res://assets/models/black_wolf_trellis.glb"  # 骨架烘焙源（tools/bake_wolf_rig.gd）
const WOLF_RIGGED := "res://assets/models/black_wolf_rigged.scn"  # 烘焙产物：18骨骼+蒙皮黑狼
const FireballScript := preload("res://scripts/fireball.gd")

var _player: Node3D
var _gun: Node3D
var _status_bar: CanvasLayer
var _backpack_hud: Control
var _backpack
var _equipment
var _player_status
var _skillbar
var _player_dead := false
var _kills := 0

func _ready() -> void:
	_build_environment()
	_build_ground()
	_build_walls()
	_build_hud()
	_build_player()
	_build_enemies()
	_build_portal()

func _process(_delta: float) -> void:
	if _player_dead and Input.is_key_pressed(KEY_R):
		if get_tree().current_scene != null:
			get_tree().reload_current_scene()

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
	_build_backpack_hud(bar)

## 背包栏迁移：底部快捷栏（1~4）+ Tab/B 背包面板
func _build_backpack_hud(parent: Node) -> void:
	var item_db = load("res://ui/item_db.gd").new()
	_backpack = load("res://ui/backpack.gd").new(item_db)
	# 初始背包沿用旧版默认（治疗药水 ×5）；MP 系统未实装，暂不发放魔力药水
	_backpack.add_item("hp_potion", 5)
	# 装备栏 + 演示种子（沿用旧版初始装备：主手生锈长剑；背包放 G18/小圆盾/铁盔/戒指）
	_equipment = load("res://ui/equipment.gd").new(_backpack)
	_player_status = load("res://ui/player_status.gd").new()
	_skillbar = load("res://ui/skillbar.gd").new()
	# 技能库：先迁火球（Q 默认绑定），defs 补 skillbar 需要的 cooldown_s/mp_cost/tier
	var skills_db = load("res://ui/skills_db.gd").new()
	var sb_skills := {}
	if skills_db.has_skill("fireball"):
		var fb: Dictionary = skills_db.get_def("fireball").duplicate(true)
		var eff: Dictionary = skills_db.effect("fireball", _player_status.level)
		fb["cooldown_s"] = eff.cooldown_s
		fb["mp_cost"] = eff.mp_cost
		fb["tier"] = 1
		sb_skills["fireball"] = fb
	_skillbar.setup(sb_skills)
	_skillbar.assign(0, "fireball")
	_backpack.add_item("rusty_sword", 1)
	_backpack.add_item("g18_pistol", 1)
	_backpack.add_item("small_shield", 1)
	_backpack.add_item("lunar_helmet", 1)
	_backpack.add_item("ring_oracle", 1)
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
	_backpack_hud = hud

## 技能触发（火球先迁）：从玩家相机方向发射
func _on_skill_triggered(skill_id: String) -> void:
	if skill_id != "fireball" or _player == null:
		_flash_skill_missing(skill_id)
		return
	var cam := _player.get_node_or_null("Camera3D") as Camera3D
	if cam == null:
		return
	var origin := _player.global_position + Vector3(0, 1.5, 0)
	var dir := -cam.global_transform.basis.z
	FireballScript.fire(get_tree().current_scene, origin, dir,
		_player_status.level, _player_status.matk(), _player_status.intt)

func _flash_skill_missing(skill_id: String) -> void:
	if _backpack_hud != null and _backpack_hud.has_method("flash_status"):
		_backpack_hud.flash_status("技能未移植（%s）" % skill_id)

func _build_enemies() -> void:
	# 黑狼用烘焙好的骨骼模型（WolfRig），原 GLB 是静态网格，烘焙见 tools/bake_wolf_rig.gd
	var wolf_model: Node3D = load(WOLF_RIGGED).instantiate()
	_build_enemy("WolfEnemy", wolf_model, Vector3(3, 0, -4), {
		"hp": 85, "chase": 3.5, "dmg": 15, "radius": 0.55, "height": 1.0,
		"offset_y": 0.41, "bob": 0.05,
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
	var cross := _find_crosshair()
	if cross:
		cross.visible = not active

func _find_crosshair() -> Label:
	if _status_bar == null:
		return null
	for c in _status_bar.find_children("", "Label", true, false):
		if c is Label and c.text == "+":
			return c
	return null

func _on_reloading() -> void:
	_status_bar.show_status("换弹中…", 1.5)

func _on_empty() -> void:
	_status_bar.show_status("没子弹 · 按 R 换弹", 1.2)

func _on_reloaded(_ammo: int, _reserve: int) -> void:
	_status_bar.clear_status()

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
