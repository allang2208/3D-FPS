extends Area3D

signal state_changed(state: Dictionary)

var _player_near: Node3D
var _pivot: Node3D
var _leaf_collision: CollisionShape3D
var _prompt: Label3D
var _open := false
var _moving := false

func setup(pivot: Node3D, leaf_collision: CollisionShape3D, initially_open: bool) -> void:
	_pivot=pivot
	_leaf_collision=leaf_collision
	_open=initially_open
	_apply_state(false)

func _ready() -> void:
	collision_layer=0
	collision_mask=4
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)

func _input(event: InputEvent) -> void:
	if not is_instance_valid(_player_near) or _moving: return
	if event is InputEventKey and event.pressed and not event.echo and event.keycode==KEY_E:
		get_viewport().set_input_as_handled()
		set_open(not _open)

func set_open(value: bool, animate := true) -> void:
	if _open==value and animate: return
	_open=value
	_apply_state(animate)
	state_changed.emit({"open":_open})

func is_open() -> bool:
	return _open

func _apply_state(animate: bool) -> void:
	if _pivot==null or _leaf_collision==null: return
	_leaf_collision.set_deferred("disabled",_open)
	var target: float=-PI*.5 if _open else 0.0
	if not animate:
		_pivot.rotation.y=target
		_update_prompt()
		return
	_moving=true
	var tween:=create_tween()
	tween.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tween.tween_property(_pivot,"rotation:y",target,.2)
	tween.finished.connect(func():
		_moving=false
		_update_prompt())
	_update_prompt()

func _on_body_entered(body: Node3D) -> void:
	if body is CharacterBody3D and body.name=="Player":
		_player_near=body
		_update_prompt()

func _on_body_exited(body: Node3D) -> void:
	if body==_player_near:
		_player_near=null
		_update_prompt()

func _update_prompt() -> void:
	if _prompt==null:
		_prompt=Label3D.new()
		_prompt.name="DoorPrompt"
		_prompt.billboard=BaseMaterial3D.BILLBOARD_ENABLED
		_prompt.position=Vector3(.25,1.9,0)
		_prompt.font_size=36
		_prompt.outline_size=7
		add_child(_prompt)
	_prompt.text="按 E 关门" if _open else "按 E 开门"
	_prompt.visible=is_instance_valid(_player_near)
