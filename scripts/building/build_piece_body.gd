extends StaticBody3D

signal destroyed(cell: Vector3i)
signal health_changed(cell: Vector3i, current: int, maximum: int)
signal state_changed(cell: Vector3i, state: Dictionary)

const Health := preload("res://scripts/building/build_health_component.gd")
var build_cell := Vector3i.ZERO
var health_component: Node

func setup(cell: Vector3i, max_health: int, saved_health: int = -1) -> void:
	build_cell=cell
	set_meta("build_cell",cell)
	set_meta("built_cell",cell)
	health_component=Health.new()
	health_component.name="HealthComponent"
	health_component.setup(max_health,saved_health)
	health_component.health_changed.connect(func(current: int, maximum: int):
		health_changed.emit(build_cell,current,maximum))
	health_component.died.connect(func(): destroyed.emit(build_cell))
	add_child(health_component)

func take_damage(amount: int, _damage_type := "physical", _source: Node3D = null) -> bool:
	return health_component.take_damage(amount) if health_component!=null else false

func heal(amount: int) -> int:
	return health_component.heal(amount) if health_component!=null else 0

func current_health() -> int:
	return health_component.current if health_component!=null else 0

func maximum_health() -> int:
	return health_component.maximum if health_component!=null else 0

func health_text() -> String:
	return "%d/%d" % [current_health(),maximum_health()]

func bind_state_source(source: Node) -> void:
	if source!=null and source.has_signal("state_changed"):
		source.state_changed.connect(func(state: Dictionary): state_changed.emit(build_cell,state))
