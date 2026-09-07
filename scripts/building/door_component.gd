extends RefCounted

const Controller := preload("res://scripts/building/build_door_controller.gd")
const SIZE := Vector3(1.0,2.0,.18)
const CENTER := Vector3(.25,.75,0)

static func add_geometry(block: StaticBody3D, frame_material: Material, door_material: Material, accent_material: Material, initially_open := false) -> Node:
	var visual:=Node3D.new()
	visual.name="DoorVisual"
	block.add_child(visual)
	_add_box(visual,"LeftFrame",Vector3(.12,2,.18),Vector3(-.19,.75,0),frame_material)
	_add_box(visual,"RightFrame",Vector3(.12,2,.18),Vector3(.69,.75,0),frame_material)
	_add_box(visual,"Header",Vector3(.76,.16,.20),Vector3(.25,1.67,0),frame_material)
	_add_box(visual,"Threshold",Vector3(.76,.06,.20),Vector3(.25,-.22,0),accent_material)
	var pivot:=Node3D.new()
	pivot.name="DoorPivot"
	pivot.position=Vector3(-.12,0,0)
	visual.add_child(pivot)
	_add_box(pivot,"DoorLeaf",Vector3(.76,1.76,.12),Vector3(.38,.70,0),door_material)
	_add_box(pivot,"DoorBrace",Vector3(.68,.08,.15),Vector3(.38,.70,0),accent_material)
	_add_box(pivot,"Handle",Vector3(.06,.06,.10),Vector3(.68,.72,-.09),accent_material)
	_add_collision(block,"FrameLeft",Vector3(.12,2,.18),Vector3(-.19,.75,0))
	_add_collision(block,"FrameRight",Vector3(.12,2,.18),Vector3(.69,.75,0))
	_add_collision(block,"FrameHeader",Vector3(.76,.16,.18),Vector3(.25,1.67,0))
	var leaf:=_add_collision(block,"DoorLeafCollision",Vector3(.76,1.76,.12),Vector3(.26,.70,0))
	var controller:=Controller.new()
	controller.name="DoorController"
	var area_shape:=BoxShape3D.new()
	area_shape.size=Vector3(1.5,2.2,1.5)
	var area_collision:=CollisionShape3D.new()
	area_collision.position=Vector3(.25,.75,0)
	area_collision.shape=area_shape
	controller.add_child(area_collision)
	block.add_child(controller)
	controller.setup(pivot,leaf,initially_open)
	return controller

static func make_preview(frame_material: Material, door_material: Material, accent_material: Material) -> Node3D:
	var root:=StaticBody3D.new()
	add_geometry(root,frame_material,door_material,accent_material,false)
	for child in root.get_children():
		if child is CollisionShape3D or child is Area3D:
			root.remove_child(child)
			child.free()
	return root

static func _add_box(parent: Node3D, label: String, size: Vector3, position: Vector3, material: Material) -> void:
	var mesh:=BoxMesh.new()
	mesh.size=size
	var visual:=MeshInstance3D.new()
	visual.name=label
	visual.mesh=mesh
	visual.material_override=material
	visual.position=position
	parent.add_child(visual)

static func _add_collision(parent: StaticBody3D, label: String, size: Vector3, position: Vector3) -> CollisionShape3D:
	var shape:=BoxShape3D.new()
	shape.size=size
	var collision:=CollisionShape3D.new()
	collision.name=label
	collision.position=position
	collision.shape=shape
	parent.add_child(collision)
	return collision
