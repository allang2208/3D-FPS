extends Area3D

## 传送门：玩家进入后切换到目标场景。
## 用法：var p = load("res://scripts/portal.gd").new()
##       p.target_scene = "res://scenes/xxx.tscn"
##       p.label_text = "传送门"
##       add_child(p)

@export var target_scene: String = ""
@export var label_text: String = "传送门"
@export var portal_color := Color(0.25, 0.65, 1.0)


func _ready() -> void:
	# 玩家 collision_layer=4（player.gd），mask 全开再用名字过滤，避免层配置变动导致失灵
	collision_mask = 0xFFFFFFFF
	body_entered.connect(_on_body_entered)
	_build_visual()


func _build_visual() -> void:
	var col := CollisionShape3D.new()
	col.name = "Collision"
	var shape := CylinderShape3D.new()
	shape.radius = 1.1
	shape.height = 2.8
	col.shape = shape
	add_child(col)

	var ring := MeshInstance3D.new()
	ring.name = "Ring"
	var torus := TorusMesh.new()
	torus.inner_radius = 0.85
	torus.outer_radius = 1.05
	var rmat := StandardMaterial3D.new()
	rmat.albedo_color = portal_color
	rmat.emission_enabled = true
	rmat.emission = portal_color
	rmat.emission_energy_multiplier = 2.5
	torus.material = rmat
	ring.mesh = torus
	ring.rotation_degrees = Vector3(90, 0, 0)  # TorusMesh 默认平躺，转成立式圆环
	add_child(ring)

	var disc := MeshInstance3D.new()
	disc.name = "Disc"
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.95
	cyl.bottom_radius = 0.95
	cyl.height = 2.6
	var dmat := StandardMaterial3D.new()
	dmat.albedo_color = Color(portal_color, 0.3)
	dmat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	dmat.emission_enabled = true
	dmat.emission = portal_color
	dmat.emission_energy_multiplier = 1.4
	cyl.material = dmat
	disc.mesh = cyl
	add_child(disc)

	var light := OmniLight3D.new()
	light.name = "Light"
	light.light_color = portal_color
	light.omni_range = 8.0
	light.light_energy = 2.0
	add_child(light)

	var label := Label3D.new()
	label.name = "Label"
	label.text = label_text
	label.position = Vector3(0, 2.0, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.font_size = 48
	label.outline_size = 10
	label.modulate = portal_color
	add_child(label)


func _on_body_entered(body: Node3D) -> void:
	if target_scene == "":
		return
	if body is CharacterBody3D and body.name == "Player":
		# 走全局加载界面（进度条），风格统一
		var ls := load("res://ui/loading_screen.gd")
		ls.load_scene(target_scene)
