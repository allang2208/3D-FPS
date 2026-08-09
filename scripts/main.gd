extends Node3D
## 无尽轮回 · 3D FPS（Godot 4.7）
## 场景代码搭建：环境 / 光照 / 地面 / 墙体 / 玩家 / HUD / 三只敌人（黑狼 GLB + 僵尸犬 + 蜘蛛）

const WOLF_GLB := "res://assets/models/black_wolf_trellis.glb"

var _player: Node3D
var _gun: Node3D
var _status_bar: CanvasLayer
var _backpack_hud: Control
var _backpack
var _player_dead := false
var _kills := 0

func _ready() -> void:
	_build_environment()
	_build_ground()
	_build_walls()
	_build_hud()
	_build_player()
	_build_enemies()

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
	var hud = load("res://ui/backpack_hud.gd").new()
	hud.name = "BackpackHud"
	hud.setup(_backpack)
	hud.player_healed.connect(_on_player_healed)
	parent.add_child(hud)
	_backpack_hud = hud

func _build_enemies() -> void:
	var wolf_model: Node3D = load(WOLF_GLB).instantiate()
	wolf_model.scale = Vector3.ONE * 1.9
	_build_enemy("WolfEnemy", wolf_model, Vector3(3, 0, -4), {
		"hp": 85, "chase": 3.5, "dmg": 15, "radius": 0.55, "height": 1.0,
		"offset_y": 0.41, "bob": 0.05,
	})
	_build_enemy("ZombieDog", EnemyModels.build_zombie_dog(), Vector3(-5, 0, 2), {
		"hp": 60, "chase": 3.7, "dmg": 12, "radius": 0.5, "height": 1.0,
		"offset_y": -0.1, "bob": 0.04, "scale": 1.5,
	})
	_build_enemy("Spider", EnemyModels.build_spider(), Vector3(7, 0, 5), {
		"hp": 50, "chase": 3.1, "dmg": 10, "radius": 0.55, "height": 0.9,
		"offset_y": -0.1, "bob": 0.04, "scale": 1.25,
	})

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

func _on_ammo(ammo: int, reserve_left: int) -> void:
	_status_bar.set_ammo(ammo, reserve_left)

func _on_hit() -> void:
	_status_bar.hitmark()

func _on_reloading() -> void:
	_status_bar.show_status("换弹中…", 1.5)

func _on_empty() -> void:
	_status_bar.show_status("没子弹 · 按 R 换弹", 1.2)

func _on_reloaded(_ammo: int, _reserve: int) -> void:
	_status_bar.clear_status()

func _on_player_damaged(hp: int) -> void:
	_status_bar.set_hp(hp, int(_player.get("max_hp")))
	_status_bar.damage_flash()

func _on_player_healed(hp: int) -> void:
	_status_bar.set_hp(hp, int(_player.get("max_hp")))

func _on_player_died() -> void:
	_player_dead = true
	_status_bar.show_death()

func _on_enemy_killed() -> void:
	_kills += 1
	_status_bar.set_kills(_kills)
