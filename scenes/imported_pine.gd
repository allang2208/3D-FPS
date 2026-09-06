extends Node3D

@export_range(0, 2) var variant := 0
const BASE = "res://assets/models/lolipop_pines/"
static var templates: Dictionary = {}
var burial_depth := 0.0

func _ready() -> void:
	if templates.is_empty():
		_build_templates()
	burial_depth = templates[variant]["burial"]
	_add_level(0)

func _build_templates() -> void:
	var source = load(BASE + "source/Pine_pack.fbx").instantiate()
	add_child(source)
	var bark = StandardMaterial3D.new()
	bark.resource_name = "pine_bark"
	bark.albedo_texture = load(BASE + "textures/Bark_basecolor.png")
	bark.albedo_color = Color(0.72,0.70,0.65)
	bark.normal_enabled = true
	bark.normal_texture = load(BASE + "textures/Bark_normal.png")
	bark.roughness = 0.95
	var leaves = ShaderMaterial.new()
	leaves.resource_name = "pine_leaves"
	leaves.shader = load(BASE + "needles.gdshader")
	leaves.set_shader_parameter("albedo_texture",load(BASE + "textures/Cluster_full_basecolor.png"))
	leaves.set_shader_parameter("opacity_texture",load(BASE + "textures/Cluster_full_Opacity.png"))
	leaves.set_shader_parameter("normal_texture",load(BASE + "textures/Cluster_full_normal.png"))
	for index in 3:
		var levels = []
		var near = source.get_node("Pine_big_%d/Pine_big_%d_LOD0" % [index+1,index+1])
		var axis: Basis = near.global_basis
		var bounds: AABB = Transform3D(axis,Vector3.ZERO) * near.get_aabb()
		var factor: float = 10.0 / bounds.size.y
		for level in 3:
			var original = source.get_node("Pine_big_%d/Pine_big_%d_LOD%d" % [index+1,index+1,level])
			var mesh = original.mesh.duplicate()
			for surface in mesh.get_surface_count():
				mesh.surface_set_material(surface,bark if original.get_active_material(surface).resource_name == "Bark_Mat" else leaves)
			levels.append({"mesh":mesh,"transform":Transform3D(axis.scaled(Vector3.ONE*factor),Vector3(0,-bounds.position.y*factor,0))})
		templates[index] = {"levels":levels,"burial":[1.2,1.2,1.3][index]*factor}
	source.free()

func _add_level(level: int) -> void:
	var entry = templates[variant]["levels"][level]
	var node = MeshInstance3D.new()
	node.mesh = entry["mesh"]
	node.transform = entry["transform"]
	node.set_meta("scenic_lod",level)
	add_child(node)

func setup_lod() -> void:
	_add_level(1)
	_add_level(2)
	for node in get_children():
		var level: int = node.get_meta("scenic_lod")
		node.visibility_range_begin = [0.0,45.0,105.0][level]
		node.visibility_range_end = [45.0,105.0,450.0][level]
		if level > 0:
			node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
