extends RefCounted
## Building scale contract: integer XYZ cells, one cell is half a metre.
const CELL_SIZE := 0.5

static func cell_center(cell: Vector3i) -> Vector3:
	return (Vector3(cell)+Vector3.ONE*.5)*CELL_SIZE

static func world_to_cell(point: Vector3) -> Vector3i:
	return Vector3i((point/CELL_SIZE).floor())

static func make_block(cell: Vector3i, material: Material) -> StaticBody3D:
	var block := StaticBody3D.new()
	block.name = "Block_%d_%d_%d" % [cell.x,cell.y,cell.z]
	block.position = cell_center(cell)
	block.set_meta("build_cell",cell)
	block.set_meta("impact_surface","concrete")
	var mesh := BoxMesh.new()
	mesh.size = Vector3.ONE*CELL_SIZE
	var visual := MeshInstance3D.new()
	visual.mesh = mesh
	visual.material_override = material
	block.add_child(visual)
	var shape := BoxShape3D.new()
	shape.size = Vector3.ONE*CELL_SIZE
	var collision := CollisionShape3D.new()
	collision.shape = shape
	block.add_child(collision)
	return block
