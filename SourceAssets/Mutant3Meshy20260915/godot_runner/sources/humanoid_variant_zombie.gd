extends "res://scripts/modern_zombie.gd"
## Shared authored motion contract; each scene provides its own mesh and stats.
@export var variant_id := "miner"
var damage_multiplier := 1.0

func _ready() -> void:
	super._ready()
	# Flash feedback belongs to this instance; the packed asset is shared.
	if _mat:
		var unique_material := _mat.duplicate() as StandardMaterial3D
		_apply_instance_material(_model, _mat, unique_material)
		_mat = unique_material

func _apply_instance_material(node: Node, source: Material, replacement: Material) -> void:
	if node is MeshInstance3D and node.mesh:
		for surface in node.mesh.get_surface_count():
			if node.get_active_material(surface) == source:
				node.set_surface_override_material(surface, replacement)
	for child in node.get_children():
		_apply_instance_material(child, source, replacement)

func take_damage(d: int, damage_type := "physical", source: Node3D = null) -> bool:
	return super.take_damage(roundi(d * damage_multiplier), damage_type, source)
