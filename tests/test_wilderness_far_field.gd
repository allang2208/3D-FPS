extends Node

var failures: Array[String] = []


func _check(condition: bool, label: String) -> void:
	print("[wilderness-far-test] ", "PASS " if condition else "FAIL ", label)
	if not condition:
		failures.append(label)


func _ready() -> void:
	var far_field := preload("res://scripts/wilderness_far_field.gd").new()
	far_field.world_seed = 424242
	add_child(far_field)
	await get_tree().process_frame
	await get_tree().process_frame
	var meshes := far_field.find_children("", "MeshInstance3D", true, false)
	var bodies := far_field.find_children("", "CollisionObject3D", true, false)
	_check(meshes.size() == 4, "far field is four batched render patches")
	_check(bodies.is_empty(), "far field creates no collision or gameplay entities")
	_check(float(far_field.generation_stats.get("world_size_m", 0.0)) == 10240.0, "far field is ten times the authored terrain width")
	_check(int(far_field.generation_stats.get("far_triangles", 0)) <= 30000, "far terrain stays within 30k triangle budget")
	_check(int(far_field.generation_stats.get("far_texture_px", 0)) == 512, "far details are baked into one mipmapped macro texture")
	get_tree().quit(0 if failures.is_empty() else 1)
