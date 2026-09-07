class_name WildernessTerrainModifier
extends Resource

@export var modifier_id: StringName
@export var priority := 0


func modify_height(_context: RefCounted, _world_position: Vector2, current_height: float) -> float:
	return current_height


func modify_surface(_context: RefCounted, _world_position: Vector2, current_surface: int) -> int:
	return current_surface
