extends Node
## Existing enemies consume speed buffs but some older controllers read raw contact_damage.
var _base := 0
var _applied := false
func refresh(multiplier: float = 1.5) -> void:
	if not _applied:
		_base = get_parent().contact_damage
		_applied = true
	get_parent().contact_damage = roundi(_base*multiplier)
func _process(_delta: float) -> void:
	if _applied and not get_parent()._buffs.has("inspire"):
		get_parent().contact_damage = _base
		_applied = false
		queue_free()
