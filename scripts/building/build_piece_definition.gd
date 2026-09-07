class_name BuildPieceDefinition
extends Resource

@export var stable_id: StringName
@export var display_name := ""
@export var category := "构件"
@export var form_label := "构件"
@export_multiline var description := ""
@export_file("*.png") var thumbnail_path := ""
@export var cost_item := ""
@export_range(1,99,1) var cost_amount := 1
@export var geometry_kind := "cube"
@export var material_key := "wood"
@export var footprint_cells := Vector3i.ONE
@export var collision_size := Vector3(.5,.5,.5)
@export var collision_center := Vector3.ZERO
@export_range(1,10000,1) var max_health := 100
@export var impact_surface := "wood"
@export var supports_weight := true
@export var requires_full_base_support := false
@export var snaps_to_same_kind := false
@export var rotatable := true
