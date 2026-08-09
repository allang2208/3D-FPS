extends Node3D
## 程序化拼装 AKM 风格枪械（占位模型）+ 开火后坐动画

var _recoil := 0.0

func _ready() -> void:
	_build_gun()

func _process(delta: float) -> void:
	if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		_recoil = 1.0
	_recoil = maxf(0.0, _recoil - delta * 7.0)
	position.z = -0.5 - _recoil * 0.09
	rotation.x = -_recoil * 0.08

func _box(parent: Node3D, size: Vector3, pos: Vector3, color: Color, rot := Vector3.ZERO) -> void:
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.55
	mat.metallic = 0.35
	box.material = mat
	mesh.mesh = box
	mesh.position = pos
	mesh.rotation = rot
	parent.add_child(mesh)

func _build_gun() -> void:
	var dark := Color(0.13, 0.14, 0.16)
	var mid := Color(0.22, 0.23, 0.27)
	var wood := Color(0.32, 0.22, 0.12)
	_box(self, Vector3(0.06, 0.09, 0.42), Vector3.ZERO, mid)
	_box(self, Vector3(0.04, 0.04, 0.30), Vector3(0, 0.02, -0.35), dark)
	_box(self, Vector3(0.05, 0.10, 0.16), Vector3(0, -0.02, 0.28), wood)
	_box(self, Vector3(0.04, 0.13, 0.05), Vector3(0, -0.11, 0.10), dark, Vector3(0.25, 0, 0))
	_box(self, Vector3(0.045, 0.17, 0.07), Vector3(0, -0.14, -0.02), dark)
	_box(self, Vector3(0.02, 0.05, 0.02), Vector3(0, 0.06, -0.20), dark)
