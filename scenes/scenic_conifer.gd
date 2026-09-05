extends Node3D

@export var variant := 0
static var templates: Dictionary = {}
static var medium_templates: Dictionary = {}
static var impostor_templates: Dictionary = {}

func _ready() -> void:
	if not templates.has(variant):
		templates[variant] = _make_meshes(variant)
	for mesh in templates[variant]:
		var node := MeshInstance3D.new()
		node.mesh = mesh
		add_child(node)


## Called after ground fitting: visual LODs must never enter collision fitting.
func setup_lod() -> void:
	var shared_bounds := AABB(Vector3(-8, -1, -8), Vector3(16, 12, 16))
	for node in get_children():
		node.set_meta("scenic_lod", 0)
		node.custom_aabb = shared_bounds
		node.visibility_range_end = 45.0
	if not medium_templates.has(variant):
		medium_templates[variant] = _make_meshes(variant, true)
	for mesh in medium_templates[variant]:
		var node := MeshInstance3D.new()
		node.mesh = mesh
		node.set_meta("scenic_lod", 1)
		node.custom_aabb = shared_bounds
		node.visibility_range_begin = 45.0
		node.visibility_range_end = 105.0
		add_child(node)
	if not impostor_templates.has(variant):
		var quad := QuadMesh.new()
		quad.size = Vector2(12, 12)
		quad.center_offset.y = 5
		var mat := ShaderMaterial.new()
		mat.resource_name = "conifer_leaves_impostor"
		mat.shader = load("res://assets/shaders/valley_tree_impostor.gdshader")
		mat.set_shader_parameter("atlas", load("res://assets/textures/scenic_valley/natural_pine_impostor_%d.png" % variant))
		quad.material = mat
		impostor_templates[variant] = quad
	var far_tree := MeshInstance3D.new()
	far_tree.mesh = impostor_templates[variant]
	far_tree.set_meta("scenic_lod", 2)
	far_tree.custom_aabb = shared_bounds
	far_tree.visibility_range_begin = 105.0
	far_tree.visibility_range_end = 450.0
	far_tree.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(far_tree)


static func _make_meshes(seed_offset: int, simplified: bool = false) -> Array[ArrayMesh]:
	return preload("res://scenes/scenic_pine_geometry.gd").make_meshes(seed_offset, simplified)
