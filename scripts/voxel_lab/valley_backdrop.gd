extends "res://scenes/scenic_valley.gd"
const PATCH_CENTER := Vector2(-245,65)
func _build_player() -> void:
	pass
func _build_hud() -> void:
	pass
func _build_mouse_king() -> void:
	pass
func _build_return_portal() -> void:
	pass
func _build_landmark_rocks() -> void:
	_occupied.append(AABB(Vector3(PATCH_CENTER.x-15,-100,PATCH_CENTER.y-15),Vector3(30,200,30)))
	super._build_landmark_rocks()
func _batch_model(path: String, p: Vector2, extent: float, rock: bool) -> void:
	if absf(p.x-PATCH_CENTER.x)<15 and absf(p.y-PATCH_CENTER.y)<15:
		return
	super._batch_model(path,p,extent,rock)
func _place_valley_tree(p: Vector2, scale_factor: float, path: String = FIR) -> void:
	if absf(p.x-PATCH_CENTER.x)<18 and absf(p.y-PATCH_CENTER.y)<18:
		return
	super._place_valley_tree(p,scale_factor,path)
