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
