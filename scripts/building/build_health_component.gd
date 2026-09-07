extends Node

signal health_changed(current: int, maximum: int)
signal died

var maximum := 1
var current := 1

func setup(max_health: int, saved_health: int = -1) -> void:
	maximum=maxi(1,max_health)
	current=maximum if saved_health<0 else clampi(saved_health,1,maximum)

func take_damage(amount: int) -> bool:
	if amount<=0 or current<=0: return false
	current=maxi(0,current-amount)
	health_changed.emit(current,maximum)
	if current==0:
		died.emit()
		return true
	return false

func heal(amount: int) -> int:
	if amount<=0 or current<=0: return 0
	var before:=current
	current=mini(maximum,current+amount)
	if current!=before: health_changed.emit(current,maximum)
	return current-before
