extends SceneTree
func _initialize() -> void:
	var scene = load("res://scenes/enemies/foreman_zombie.tscn").instantiate()
	var ok: bool = scene.get_node("Model").scene_file_path == "res://assets/models/foreman_zombie/foreman_v11.glb"
	ok = ok and not FileAccess.file_exists("res://scenes/foreman_demo.tscn")
	ok = ok and not FileAccess.get_file_as_string("res://scripts/main.gd").contains("foreman_portal.gd")
	ok = ok and ResourceLoader.exists("res://scenes/wilderness_combat_study.tscn")
	print("FOREMAN_ENTRY current_model_and_retired_demo=",ok)
	scene.free()
	quit(0 if ok else 1)
