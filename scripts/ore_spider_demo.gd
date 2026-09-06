extends Node3D
## F6 sandbox: real player/gun, isolated from concurrently edited main UI.
var _player: CharacterBody3D
var _gun: Node3D
var _info: Label
var kills := 0
func _ready() -> void:
	# Existing HUD opt-out contract: a scene with BackpackHud owns its display.
	# Practice ammo stays on this gun, never in the account equipment inventory.
	var layer := CanvasLayer.new()
	add_child(layer)
	var local_hud := Control.new()
	local_hud.name = "BackpackHud"
	layer.add_child(local_hud)
	_info = Label.new()
	_info.position = Vector2(24, 24)
	_info.add_theme_font_size_override("font_size", 20)
	local_hud.add_child(_info)
	var world := WorldEnvironment.new()
	world.environment = Environment.new()
	world.environment.background_mode = Environment.BG_COLOR
	world.environment.background_color = Color(.24,.29,.36)
	world.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	world.environment.ambient_light_color = Color(.7,.75,.8)
	world.environment.ambient_light_energy = .7
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50,-30,0)
	sun.shadow_enabled = true
	add_child(sun)
	var ground := StaticBody3D.new()
	var collision := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(40, 1, 40)
	collision.shape = box
	ground.add_child(collision)
	var visual := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = box.size
	var floor_material := StandardMaterial3D.new()
	floor_material.albedo_color = Color(.26,.28,.30)
	mesh.material = floor_material
	visual.mesh = mesh
	ground.add_child(visual)
	ground.position.y = -.5
	add_child(ground)
	_player = CharacterBody3D.new()
	_player.name = "Player"
	_player.set_script(load("res://scripts/player.gd"))
	_player.position = Vector3(0, .1, 9)
	var col := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = .35
	capsule.height = 1.7
	col.shape = capsule
	_player.add_child(col)
	var camera := Camera3D.new()
	camera.name = "Camera3D"
	camera.position.y = 1.62
	camera.fov = 75
	_player.add_child(camera)
	camera.add_child(AudioListener3D.new())
	var cfx := Node3D.new()
	cfx.name = "CameraFx"
	cfx.set_script(load("res://scripts/camera_fx.gd"))
	camera.add_child(cfx)
	var gun := Node3D.new()
	gun.name = "Gun"
	gun.position = Vector3(.28, -.26, -.5)
	gun.set_script(load("res://scripts/gun.gd"))
	camera.add_child(gun)
	add_child(_player)
	_gun = gun

	var spider := preload("res://scenes/enemies/ore_spider.tscn").instantiate()
	spider.position = Vector3(0, 0, 0)
	add_child(spider)
	spider.setup(_player, func(): kills += 1)

func _process(_delta: float) -> void:
	_info.text = "矿石蜘蛛试玩  HP %d  弹药 %d / %d  击杀 %d\nWASD 移动 · 鼠标射击 · R 换弹 · F8 重开" % [_player.hp, _gun.ammo, _gun.reserve, kills]

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_pressed() and event is InputEventKey and event.keycode == KEY_F8:
		get_tree().reload_current_scene()
