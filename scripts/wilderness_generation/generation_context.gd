class_name WildernessGenerationContext
extends RefCounted

const Profile := preload("res://scripts/wilderness_generation_profile.gd")
const CHUNK_SIZE_M := 256.0

var world_seed: int
var generator_version: int
var chunk_coord: Vector2i
var profile: RefCounted


func _init(seed_value: int, coord: Vector2i, version: int = Profile.GENERATOR_VERSION) -> void:
	world_seed = seed_value
	chunk_coord = coord
	generator_version = version
	profile = Profile.new(world_seed)


func chunk_origin() -> Vector2:
	return Vector2(chunk_coord) * CHUNK_SIZE_M


func height_at(p: Vector2) -> float:
	return profile.height_at(p)


func slope_at(p: Vector2) -> float:
	return profile.slope_at(p)


func moisture_at(p: Vector2) -> float:
	return profile.moisture_at(p)


func temperature_at(p: Vector2) -> float:
	return profile.temperature_at(p)


func biome_at(p: Vector2) -> StringName:
	return profile.biome_at(p)


func geology_at(p: Vector2) -> StringName:
	return profile.geology_at(p)


func water_distance(p: Vector2) -> float:
	return profile.water_distance(p)


func stable_float(cell: Vector2i, salt: int = 0) -> float:
	return Profile.hash_float(world_seed, cell, salt)


func feature_id(rule_id: StringName, candidate_index: int) -> String:
	return "%s:%d:%d:%d:%d" % [rule_id, world_seed, chunk_coord.x, chunk_coord.y, candidate_index]
