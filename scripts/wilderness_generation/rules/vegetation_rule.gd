class_name WildernessVegetationRule
extends "res://scripts/wilderness_generation/rules/wilderness_rule.gd"

@export var scene_paths: Array[String] = []
@export var impostor_paths: Array[String] = []
@export var allowed_biomes: Array[StringName] = []
@export var height_range := Vector2(-100.0, 180.0)
@export var slope_range := Vector2(0.0, 35.0)
@export var moisture_range := Vector2(0.0, 1.0)
@export var water_distance_range := Vector2(4.0, 10000.0)
@export_range(0.0, 1.0, 0.001) var density := 0.1
@export_range(0.5, 100.0, 0.5) var minimum_spacing := 6.0
@export var scale_range := Vector2(0.8, 1.2)
@export var collision_distance := 450.0
@export var shadow_distance := 80.0
@export var harvest_item: StringName = &"wood"


func snapshot() -> Dictionary:
	var data := super.snapshot()
	data.merge({
		"kind": &"vegetation",
		"scene_paths": scene_paths.duplicate(),
		"impostor_paths": impostor_paths.duplicate(),
		"allowed_biomes": allowed_biomes.duplicate(),
		"height_range": height_range,
		"slope_range": slope_range,
		"moisture_range": moisture_range,
		"water_distance_range": water_distance_range,
		"density": density,
		"minimum_spacing": minimum_spacing,
		"scale_range": scale_range,
		"collision_distance": collision_distance,
		"shadow_distance": shadow_distance,
		"harvest_item": harvest_item,
	})
	return data
