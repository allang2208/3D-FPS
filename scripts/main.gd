extends Node3D
## 无尽轮回 · 3D FPS（Godot 4.7）
## 场景代码搭建：环境 / 光照 / 地面 / 墙体 / 玩家 / HUD / 三只敌人（黑狼 GLB + 僵尸犬 + 蜘蛛）

const WOLF_GLB := "res://assets/models/black_wolf_trellis.glb"

var _player: Node3D
var _gun: Node3D
var _hp_label: Label
var _ammo_label: Label
var _kill_label: Label
var _hitmarker: Label
var _death_label: Label
var _status_label: Label
var _dmgflash: ColorRect
var _player_dead := false
var _hitmark_t := 0.0
var _dmgflash_t := 0.0
var _status_t := 0.0
var _kills := 0

func _ready() -> void:
	_build_environment()
	_build_ground()
	_build_walls()
	_build_hud()
	_build_player()
	_build_enemies()

func _process(delta: float) -> void:
	_hitmark_t = maxf(0.0, _hitmark_t - delta)
	_hitmarker.visible = _hitmark_t > 0.0
	_dmgflash_t = maxf(0.0, _dmgflash_t - delta)
	_dmgflash.color.a = 0.25 * (_dmgflash_t / 0.18)
	_status_t = maxf(0.0, _status_t - delta)
	_status_label.visible = _status_t > 0.0
	if _player_dead and Input.is_key_pressed(KEY_R):
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
	var layer := CanvasLayer.new()
	layer.name = "HUD"
	add_child(layer)
	_hp_label = _make_label(layer, "生命: 100", Vector2(16, 12), 18, Color(0.92, 0.92, 0.96))
	_kill_label = _make_label(layer, "击杀: 0", Vector2(16, 38), 18, Color(0.96, 0.9, 0.7))
	_ammo_label = _make_label(layer, "弹药: 30/90", Vector2.ZERO, 22, Color(0.92, 0.92, 0.96))
	_ammo_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	_ammo_label.position = Vector2(-170, -42)
	_ammo_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_status_label = _make_label(layer, "", Vector2.ZERO, 16, Color(0.98, 0.75, 0.4))
	_status_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	_status_label.position = Vector2(-170, -68)
	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_status_label.visible = false
	_hitmarker = _make_label(layer, "✕", Vector2.ZERO, 30, Color(0.98, 0.98, 0.95))
	_hitmarker.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_hitmarker.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_hitmarker.grow_vertical = Control.GROW_DIRECTION_BOTH
	_hitmarker.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_hitmarker.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_hitmarker.visible = false
	var cross := _make_label(layer, "＋", Vector2.ZERO, 26, Color(0.95, 0.95, 0.9))
	cross.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	cross.grow_horizontal = Control.GROW_DIRECTION_BOTH
	cross.grow_vertical = Control.GROW_DIRECTION_BOTH
	cross.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	cross.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_death_label = _make_label(layer, "你死了\n按 R 重来", Vector2.ZERO, 40, Color(0.95, 0.4, 0.35))
	_death_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_death_label.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_death_label.grow_vertical = Control.GROW_DIRECTION_BOTH
	_death_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_death_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_death_label.visible = false
	_dmgflash = ColorRect.new()
	_dmgflash.color = Color(0.8, 0, 0, 0)
	_dmgflash.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_dmgflash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(_dmgflash)

func _make_label(parent: Node, text: String, pos: Vector2, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.position = pos
	l.add_theme_color_override("font_color", color)
	l.add_theme_font_size_override("font_size", size)
	parent.add_child(l)
	return l

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
	_ammo_label.text = "弹药: %d/%d" % [ammo, reserve_left]

func _on_hit() -> void:
	_hitmark_t = 0.12

func _on_reloading() -> void:
	_status_label.text = "换弹中…"
	_status_t = 1.5

func _on_empty() -> void:
	_status_label.text = "没子弹 · 按 R 换弹"
	_status_t = 1.2

func _on_reloaded(_ammo: int, _reserve: int) -> void:
	_status_t = 0.0

func _on_player_damaged(hp: int) -> void:
	_hp_label.text = "生命: %d" % hp
	_dmgflash_t = 0.18

func _on_player_died() -> void:
	_player_dead = true
	_death_label.visible = true

func _on_enemy_killed() -> void:
	_kills += 1
	_kill_label.text = "击杀: %d" % _kills
