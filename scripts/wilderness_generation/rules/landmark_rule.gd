class_name WildernessLandmarkRule
extends "res://scripts/wilderness_generation/rules/wilderness_rule.gd"

@export var scene_path := ""
@export var allowed_biomes: Array[StringName] = []
@export var height_range := Vector2(-100.0, 180.0)
@export var slope_max := 10.0
@export var water_distance_range := Vector2(15.0, 10000.0)
@export var footprint := Vector2(24.0, 24.0)
@export var clearance_radius := 40.0
@export_range(0.0, 1.0, 0.001) var chunk_chance := 0.08
@export_range(1, 100, 1) var max_per_world := 5
@export var flatten_terrain := false


func snapshot() -> Dictionary:
	var data := super.snapshot()
	data.merge({
		"kind": &"landmark",
		"scene_path": scene_path,
		"allowed_biomes": allowed_biomes.duplicate(),
		"height_range": height_range,
		"slope_max": slope_max,
		"water_distance_range": water_distance_range,
		"footprint": footprint,
		"clearance_radius": clearance_radius,
		"chunk_chance": chunk_chance,
		"max_per_world": max_per_world,
		"flatten_terrain": flatten_terrain,
	})
	return data
