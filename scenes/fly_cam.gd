extends Camera3D

# 简易飞行相机：左键拖拽视角，WASD 移动，空格/Shift 上下，Ctrl 加速。

var speed := 12.0
var boost := 3.0
var yaw := 0.0
var pitch := -0.15


func _ready() -> void:
	position = Vector3(0, 40, 90)
	_apply_rotation()


func _input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		yaw -= event.relative.x * 0.003
		pitch = clampf(pitch - event.relative.y * 0.003, -1.4, 1.4)
		_apply_rotation()


func _physics_process(delta: float) -> void:
	var dir := Vector3.ZERO
	if Input.is_key_pressed(KEY_W):
		dir.z -= 1
	if Input.is_key_pressed(KEY_S):
		dir.z += 1
	if Input.is_key_pressed(KEY_A):
		dir.x -= 1
	if Input.is_key_pressed(KEY_D):
		dir.x += 1
	if Input.is_key_pressed(KEY_SPACE):
		dir.y += 1
	if Input.is_key_pressed(KEY_SHIFT):
		dir.y -= 1
	var s := speed
	if Input.is_key_pressed(KEY_CTRL):
		s *= boost
	position += (transform.basis * dir.normalized()) * s * delta


func _apply_rotation() -> void:
	rotation = Vector3(pitch, yaw, 0)
