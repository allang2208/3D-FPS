class_name WildernessRule
extends Resource

@export var rule_id: StringName
@export var enabled := true
@export_range(1, 1000, 1) var introduced_version := 1
@export_range(-1000, 1000, 1) var priority := 0


func snapshot() -> Dictionary:
	return {
		"rule_id": rule_id,
		"enabled": enabled,
		"introduced_version": introduced_version,
		"priority": priority,
	}
