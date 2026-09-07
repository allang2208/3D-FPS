extends RefCounted
const PATH := "user://inventory-cold-steel-v1.save"

static func resolved_path(path := PATH) -> String:
	if OS.has_environment("INVENTORY_SAVE_PATH") and path == PATH:
		return OS.get_environment("INVENTORY_SAVE_PATH")
	return path

static func read_snapshot(path := PATH) -> Dictionary:
	path = resolved_path(path)
	if not FileAccess.file_exists(path):
		return {}
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}
	var value = file.get_var(false)
	if value is Dictionary and value.get("version", 0) == 1:
		return value
	return {}

static func has_snapshot(path := PATH) -> bool:
	return not read_snapshot(path).is_empty()

## New game owns both the inventory snapshot and its procedural-world identity.
## Continue-game leaves both files intact, so the same seed reproduces the map.
static func delete_snapshot(path := PATH) -> Error:
	path = resolved_path(path)
	for candidate in [path, path + ".tmp", path + ".previous", path + ".wilderness-building"]:
		if not FileAccess.file_exists(candidate):
			continue
		var error := DirAccess.remove_absolute(ProjectSettings.globalize_path(candidate))
		if error != OK:
			return error
	return preload("res://scripts/wilderness_generation/world_seed_store.gd").delete_world()

static func write_snapshot(data: Dictionary, path := PATH) -> Error:
	path = resolved_path(path)
	var file := FileAccess.open(path + ".tmp", FileAccess.WRITE)
	if file == null:
		return FileAccess.get_open_error()
	file.store_var(data, false)
	file.flush()
	var error := file.get_error()
	file.close()
	if error != OK:
		return error
	return DirAccess.rename_absolute(ProjectSettings.globalize_path(path + ".tmp"), ProjectSettings.globalize_path(path))
