class_name WildernessWorldSeedStore
extends RefCounted

const DEFAULT_PATH := "user://wilderness-world-v2.save"
const FORMAT_VERSION := 1


static func resolved_path() -> String:
	var override := OS.get_environment("WILDERNESS_WORLD_PATH")
	return override if not override.is_empty() else DEFAULT_PATH


static func ensure_world() -> Dictionary:
	var existing := read_world()
	if not existing.is_empty():
		return existing
	return create_new_world()


static func create_new_world() -> Dictionary:
	var seed_value := int(Time.get_unix_time_from_system() * 1000000.0) ^ int(Time.get_ticks_usec()) ^ OS.get_process_id()
	var data := {
		"format_version": FORMAT_VERSION,
		"generator_version": 2,
		"world_seed": seed_value,
		"created_at": Time.get_datetime_string_from_system(true),
	}
	var error := write_world(data)
	return data if error == OK else {}


static func read_world() -> Dictionary:
	var path := resolved_path()
	if not FileAccess.file_exists(path):
		return {}
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}
	var value = file.get_var(false)
	if value is Dictionary and int(value.get("format_version", 0)) == FORMAT_VERSION:
		return value
	return {}


static func write_world(data: Dictionary) -> Error:
	var path := resolved_path()
	var file := FileAccess.open(path + ".tmp", FileAccess.WRITE)
	if file == null:
		return FileAccess.get_open_error()
	file.store_var(data, false)
	file.flush()
	var error := file.get_error()
	file.close()
	if error != OK:
		return error
	if FileAccess.file_exists(path):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
	return DirAccess.rename_absolute(ProjectSettings.globalize_path(path + ".tmp"), ProjectSettings.globalize_path(path))


static func delete_world() -> Error:
	var path := resolved_path()
	var result := OK
	for candidate in [path, path + ".tmp"]:
		if FileAccess.file_exists(candidate):
			var error := DirAccess.remove_absolute(ProjectSettings.globalize_path(candidate))
			if error != OK:
				result = error
	return result
