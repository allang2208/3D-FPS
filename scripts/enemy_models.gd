class_name EnemyModels
## 代码拼装的敌人模型（three.js 原型移植）：僵尸犬 / 蜘蛛
## 每条腿是一个名为 Leg 的枢轴节点，enemy.gd 会让它摆动

static func build_zombie_dog() -> Node3D:
	var root := Node3D.new()
	var body := Color(0.44, 0.49, 0.31)
	var dark := Color(0.34, 0.37, 0.23)
	var eye := Color(0.84, 0.27, 0.27)
	_box(root, Vector3(0.95, 0.55, 0.38), Vector3(0, 0.85, 0), body)
	_box(root, Vector3(0.55, 0.52, 0.40), Vector3(0.15, 0.80, 0.12), body)
	_box(root, Vector3(0.34, 0.32, 0.30), Vector3(0.30, 1.16, 0.18), dark)
	_box(root, Vector3(0.18, 0.15, 0.22), Vector3(0.52, 1.14, 0.18), body)
	_box(root, Vector3(0.06, 0.06, 0.03), Vector3(0.48, 1.21, 0.11), eye)
	_box(root, Vector3(0.06, 0.06, 0.03), Vector3(0.48, 1.21, 0.25), eye)
	_box(root, Vector3(0.10, 0.10, 0.36), Vector3(-0.50, 1.02, 0.18), dark)
	for pos in [Vector3(-0.32, 0.62, 0.06), Vector3(0.32, 0.62, 0.06), Vector3(-0.32, 0.62, 0.30), Vector3(0.32, 0.62, 0.30)]:
		_leg(root, pos, dark)
	root.position.y = -0.10
	return root

static func build_spider() -> Node3D:
	var root := Node3D.new()
	var body := Color(0.47, 0.19, 0.30)
	var dark := Color(0.33, 0.13, 0.22)
	var eye := Color(0.84, 0.27, 0.27)
	_box(root, Vector3(0.84, 0.70, 0.90), Vector3(0, 0.55, -0.28), body)
	_box(root, Vector3(0.55, 0.45, 0.52), Vector3(0.18, 0.58, 0.22), dark)
	_box(root, Vector3(0.30, 0.30, 0.30), Vector3(0.42, 0.60, 0.46), body)
	_box(root, Vector3(0.06, 0.06, 0.04), Vector3(0.55, 0.66, 0.42), eye)
	_box(root, Vector3(0.06, 0.06, 0.04), Vector3(0.55, 0.66, 0.50), eye)
	for z in [-0.28, -0.10, 0.10, 0.28]:
		for side in [-1, 1]:
			_spider_leg(root, side * 0.34, 0.48, z, side, dark)
	root.position.y = -0.10
	return root

static func _leg(root: Node3D, pos: Vector3, color: Color) -> void:
	var pivot := Node3D.new()
	pivot.name = "Leg"
	pivot.position = pos
	_box(pivot, Vector3(0.12, 0.5, 0.12), Vector3(0, -0.25, 0), color)
	root.add_child(pivot)

static func _spider_leg(root: Node3D, x: float, y: float, z: float, side: int, color: Color) -> void:
	var pivot := Node3D.new()
	pivot.name = "Leg"
	pivot.position = Vector3(x, y, z)
	_box(pivot, Vector3(0.07, 0.07, 0.55), Vector3(side * 0.28, -0.12, 0), color, Vector3(0, 0, side * 0.55))
	root.add_child(pivot)

static func _box(parent: Node3D, size: Vector3, pos: Vector3, color: Color, rot := Vector3.ZERO) -> void:
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.9
	box.material = mat
	mesh.mesh = box
	mesh.position = pos
	mesh.rotation = rot
	parent.add_child(mesh)
