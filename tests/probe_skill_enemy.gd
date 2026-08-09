extends StaticBody3D

var hp := 100
var max_hp := 100
var _hp := 100
var _stun_ms := 0
var _electrified_stacks := 0

func take_damage(dmg: int, damage_type := "physical", _src: Node3D = null) -> void:
	var final_d := dmg
	if damage_type == "electric" and _electrified_stacks > 0:
		final_d = maxi(1, floori(final_d * (1.0 + _electrified_stacks * 0.03)))
	hp = maxi(0, hp - final_d)
	_hp = hp

func apply_stun(duration_ms: int) -> void:
	_stun_ms = maxi(_stun_ms, duration_ms)

func apply_electrified(stacks: int, duration_ms: int, _matk: int = 0, _intt: int = 0) -> void:
	_electrified_stacks += stacks

func _ready() -> void:
	collision_layer = 2
	var col := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.5
	cap.height = 1.0
	col.shape = cap
	col.position = Vector3(0, 0.5, 0)
	add_child(col)
