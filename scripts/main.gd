extends Node3D
## 无尽轮回 · 3D FPS（Godot 4.7 最小原型）
## 场景全部用代码搭建：环境 / 光照 / 地面 / 墙体 / 玩家 / 枪 / 黑狼 GLB

const WOLF_GLB := "res://assets/models/black_wolf_trellis.glb"

var _wolf: Node3D
var _t := 0.0

func _ready() -> void:
	_build_environment()
	_build_ground()
	_build_walls()
	_build_player()
	_build_wolf()

func _process(delta: float) -> void:
	_t += delta
	# 占位待机动画：轻微起伏（后续换成骨骼动画 / IK）
	if _wolf:
		_wolf.position.y = 0.41 + sin(_t * 2.2) * 0.05

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
	cam.add_child(gun)
	add_child(player)

func _build_wolf() -> void:
	var wolf_scene := load(WOLF_GLB)
	if not wolf_scene:
		push_warning("黑狼 GLB 未导入，请先运行 --import 或打开一次编辑器")
		return
	_wolf = wolf_scene.instantiate()
	_wolf.name = "BlackWolf"
	_wolf.scale = Vector3.ONE * 1.9
	# 原始 GLB：脚底 y≈-0.21，头朝 +z；抬高让脚落在地面
	_wolf.position = Vector3(3, 0.41, -4)
	add_child(_wolf)
