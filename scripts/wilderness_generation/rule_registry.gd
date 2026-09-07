class_name WildernessRuleRegistry
extends RefCounted

const DEFAULT_RULE_DIRECTORY := "res://assets/data/wilderness/rules"

var rules: Array[Resource] = []
var terrain_modifiers: Array[Resource] = []


func load_directory(path: String = DEFAULT_RULE_DIRECTORY) -> void:
	rules.clear()
	if not DirAccess.dir_exists_absolute(ProjectSettings.globalize_path(path)):
		return
	var files := DirAccess.get_files_at(path)
	files.sort()
	for file in files:
		if not file.ends_with(".tres"):
			continue
		var rule = ResourceLoader.load(path.path_join(file))
		if rule != null and rule.has_method("snapshot") and bool(rule.get("enabled")):
			rules.append(rule)
	rules.sort_custom(func(a: Resource, b: Resource) -> bool:
		if int(a.get("priority")) == int(b.get("priority")):
			return String(a.get("rule_id")) < String(b.get("rule_id"))
		return int(a.get("priority")) < int(b.get("priority")))


func register_rule(rule: Resource) -> void:
	if rule != null and rule.has_method("snapshot"):
		rules.append(rule)


func register_terrain_modifier(modifier: Resource) -> void:
	if modifier != null and modifier.has_method("modify_height"):
		terrain_modifiers.append(modifier)
		terrain_modifiers.sort_custom(func(a: Resource, b: Resource) -> bool: return int(a.get("priority")) < int(b.get("priority")))


func snapshot_rules() -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for rule in rules:
		var data: Dictionary = rule.snapshot()
		if bool(data.get("enabled", true)):
			result.append(data)
	return result
