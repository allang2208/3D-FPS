class_name WildernessDepositRule
extends "res://scripts/wilderness_generation/rules/wilderness_rule.gd"

@export var scene_paths: Array[String] = []
@export var allowed_geology: Array[StringName] = []
@export var allowed_biomes: Array[StringName] = []
@export var height_range := Vector2(-120.0, 180.0)
@export var slope_range := Vector2(0.0, 65.0)
@export var water_distance_range := Vector2(5.0, 10000.0)
@export_range(0.0, 1.0, 0.001) var vein_threshold := 0.72
@export_range(0.5, 100.0, 0.5) var minimum_spacing := 18.0
@export var scale_range := Vector2(0.7, 1.4)
@export var harvest_item: StringName
@export_range(0, 20, 1) var required_tool_level := 0


func snapshot() -> Dictionary:
	var data := super.snapshot()
	data.merge({
		"kind": &"deposit",
		"scene_paths": scene_paths.duplicate(),
		"allowed_geology": allowed_geology.duplicate(),
		"allowed_biomes": allowed_biomes.duplicate(),
		"height_range": height_range,
		"slope_range": slope_range,
		"water_distance_range": water_distance_range,
		"vein_threshold": vein_threshold,
		"minimum_spacing": minimum_spacing,
		"scale_range": scale_range,
		"harvest_item": harvest_item,
		"required_tool_level": required_tool_level,
	})
	return data
