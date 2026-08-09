extends CharacterBody3D
## 第一人称控制器：WASD 移动 + 鼠标视角 + 空格跳 + Shift 疾跑 + Esc 释放鼠标

signal damaged(hp: int)
signal died

@export var walk_speed := 5.0
@export var sprint_speed := 8.5
@export var jump_velocity := 4.8
@export var mouse_sensitivity := 0.0022
@export var max_hp := 100

const GRAVITY := 18.0

var hp := 100
var is_dead := false

func _ready() -> void:
	hp = max_hp
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func take_damage(d: int) -> void:
	if is_dead:
		return
	hp = maxi(0, hp - d)
	damaged.emit(hp)
	if hp <= 0:
		is_dead = true
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		died.emit()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * mouse_sensitivity)
		var cam := get_node_or_null("Camera3D") as Camera3D
		if cam:
			cam.rotate_x(-event.relative.y * mouse_sensitivity)
			cam.rotation.x = clampf(cam.rotation.x, -1.45, 1.45)
	elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	if Input.is_key_pressed(KEY_SPACE) and is_on_floor():
		velocity.y = jump_velocity
	var input := Vector3(
		float(Input.is_key_pressed(KEY_D)) - float(Input.is_key_pressed(KEY_A)),
		0.0,
		float(Input.is_key_pressed(KEY_S)) - float(Input.is_key_pressed(KEY_W))
	)
	if input.length() > 1.0:
		input = input.normalized()
	var spd := sprint_speed if Input.is_key_pressed(KEY_SHIFT) else walk_speed
	var dir := (transform.basis * input).normalized()
	velocity.x = dir.x * spd
	velocity.z = dir.z * spd
	move_and_slide()
