extends "res://scripts/modern_zombie.gd"
## Preserve the existing authored zombie animation/combat controller.
var damage_multiplier := 1.0
func take_damage(d: int, damage_type := "physical", source: Node3D = null) -> bool:
	return super.take_damage(roundi(d * damage_multiplier), damage_type, source)
