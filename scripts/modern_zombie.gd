extends "res://scripts/ordinary_zombie.gd"
## Denys native zombie attacks and limp, with UAL death retargeted to the same rig.
## Defaults also survive dungeon_zombie's scene-time script replacement.
func _init() -> void:
	attack_active_start = 0.60
	attack_active_end = 0.77
	attack_duration = 47.0 / 30.0
	death_duration = 2.4
	walk_reference_speed = 1.021683
	attack_clip_choices = ["Attack", "AttackRight"]
	head_hitbox_offset = Vector3(9.465928, 2.306772, -0.000078)

const ZombieSkins := preload("res://scripts/zombie_skin_variants.gd")
## -1 randomly selects original/new skin; 0/1 pins a skin for authored scenes/previews.
@export_range(-1, 1, 1) var appearance_choice: int = -1
var chosen_appearance: int = -1

func _ready() -> void:
	# Apply before enemy._ready caches the flash material; dungeon script swaps inherit this.
	if chosen_appearance < 0:
		chosen_appearance = ZombieSkins.apply(get_node_or_null("Model") as Node3D, appearance_choice)
	super._ready()
