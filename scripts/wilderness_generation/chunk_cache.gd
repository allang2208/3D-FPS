class_name WildernessChunkCache
extends RefCounted

const Profile := preload("res://scripts/wilderness_generation_profile.gd")
const FORMAT_VERSION := 1
const DEFAULT_ROOT := "user://wilderness_cache/v2"

var root_path := ""


func _init(override_root: String = "") -> void:
	root_path = override_root
	if root_path.is_empty():
		root_path = OS.get_environment("WILDERNESS_CACHE_PATH")
	if root_path.is_empty():
		root_path = DEFAULT_ROOT


func chunk_path(seed_value: int, coord: Vector2i) -> String:
	return root_path.path_join(str(seed_value)).path_join("%d_%d.chunk" % [coord.x, coord.y])


func has_chunk(seed_value: int, coord: Vector2i) -> bool:
	return FileAccess.file_exists(chunk_path(seed_value, coord))


func save_chunk(data: Dictionary) -> Error:
	var seed_value := int(data.get("world_seed", 0))
	var coord: Vector2i = data.get("coord", Vector2i.ZERO)
	var path := chunk_path(seed_value, coord)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(path.get_base_dir()))
	var file := FileAccess.open(path + ".tmp", FileAccess.WRITE)
	if file == null:
		return FileAccess.get_open_error()
	file.store_32(FORMAT_VERSION)
	file.store_var(data, false)
	file.flush()
	var error := file.get_error()
	file.close()
	if error != OK:
		return error
	if FileAccess.file_exists(path):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
	return DirAccess.rename_absolute(ProjectSettings.globalize_path(path + ".tmp"), ProjectSettings.globalize_path(path))


func load_chunk(seed_value: int, coord: Vector2i) -> Dictionary:
	var path := chunk_path(seed_value, coord)
	if not FileAccess.file_exists(path):
		return {}
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null or file.get_32() != FORMAT_VERSION:
		return {}
	var value = file.get_var(false)
	if not value is Dictionary:
		return {}
	if int(value.get("world_seed", 0)) != seed_value or value.get("coord", Vector2i.ZERO) != coord:
		return {}
	if int(value.get("generator_version", 0)) != Profile.GENERATOR_VERSION:
		return {}
	return value
