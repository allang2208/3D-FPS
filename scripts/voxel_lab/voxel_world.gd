extends Node3D
## 有界体素试验：1 米单元、8 米区块，仅生成暴露面。
const LOW := Vector3i(-24, -8, -24)
const HIGH := Vector3i(24, 16, 24)
const CHUNK := 8
const EMPTY := 0
const SOIL := 1
const STONE := 2
const ORE := 3
const BRICK := 4
const DIRECTIONS := [Vector3i.RIGHT, Vector3i.LEFT, Vector3i.UP, Vector3i.DOWN, Vector3i.BACK, Vector3i.FORWARD]
const COLORS := [Color.TRANSPARENT, Color(0.40, 0.28, 0.16), Color(0.39, 0.43, 0.46), Color(0.32, 0.55, 0.64), Color(0.64, 0.33, 0.20)]
var cells := PackedByteArray()
var edits: Dictionary = {}
var chunks: Dictionary = {}
var stock := {1: 32, 2: 32, 3: 0, 4: 64}
var last_rebuild_ms := 0.0
var last_rebuilt_chunks := 0
var triangle_count := 0
var material: StandardMaterial3D

func _ready() -> void:
	material = StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	material.roughness = 0.95
	reset_data()
	rebuild_all()

func contains_cell(p: Vector3i) -> bool:
	return p.x >= LOW.x and p.y >= LOW.y and p.z >= LOW.z and p.x < HIGH.x and p.y < HIGH.y and p.z < HIGH.z

func index_of(p: Vector3i) -> int:
	var q := p - LOW
	return q.x + 48 * (q.z + 48 * q.y)

func height_at(x: int, z: int) -> int:
	return 1 + floori(7.0 * exp(-pow((x - 7.0) / 9.0, 2.0) - pow(z / 13.0, 2.0)))

func initial_cell(p: Vector3i) -> int:
	var h := height_at(p.x, p.z)
	if p.y >= h:
		return EMPTY
	if p.y >= h - 2:
		return SOIL
	if p.y > LOW.y and posmod(p.x * 13 + p.y * 7 + p.z * 3, 29) < 3:
		return ORE
	return STONE

func reset_data() -> void:
	cells.resize(48 * 48 * 24)
	edits.clear()
	stock = {1: 32, 2: 32, 3: 0, 4: 64}
	for y in range(LOW.y, HIGH.y):
		for z in range(LOW.z, HIGH.z):
			for x in range(LOW.x, HIGH.x):
				var p := Vector3i(x, y, z)
				cells[index_of(p)] = initial_cell(p)

func get_cell(p: Vector3i) -> int:
	return cells[index_of(p)] if contains_cell(p) else EMPTY

func chunk_of(p: Vector3i) -> Vector3i:
	return Vector3i(floori(p.x / 8.0), floori(p.y / 8.0), floori(p.z / 8.0))

func change_cell(p: Vector3i, kind: int) -> void:
	store_cell(p,kind)
	if kind == initial_cell(p):
		edits.erase(p)
	else:
		edits[p] = kind
	var dirty := affected_chunks(p)
	var started := Time.get_ticks_usec()
	for key in dirty:
		rebuild_chunk(key)
	last_rebuilt_chunks = dirty.size()
	last_rebuild_ms = (Time.get_ticks_usec() - started) / 1000.0

func store_cell(p: Vector3i, kind: int) -> void:
	cells[index_of(p)] = kind

func affected_chunks(p: Vector3i) -> Dictionary:
	var dirty := {chunk_of(p): true}
	for direction in DIRECTIONS:
		var neighbor: Vector3i = p + direction
		if contains_cell(neighbor):
			dirty[chunk_of(neighbor)] = true
	return dirty

func mine(p: Vector3i) -> bool:
	if not contains_cell(p) or is_bedrock(p) or get_cell(p) == EMPTY:
		return false
	var kind := get_cell(p)
	stock[kind] += 1
	change_cell(p, EMPTY)
	return true

func is_bedrock(p: Vector3i) -> bool:
	return p.y==LOW.y

func can_place(p: Vector3i, kind: int, occupied: AABB) -> bool:
	if not contains_cell(p) or get_cell(p) != EMPTY or kind < SOIL or kind > BRICK or stock.get(kind, 0) <= 0:
		return false
	if AABB(Vector3(p), Vector3.ONE).intersects(occupied):
		return false
	for direction in DIRECTIONS:
		if get_cell(p + direction) != EMPTY:
			return true
	return false

func place(p: Vector3i, kind: int, occupied: AABB) -> bool:
	if not can_place(p, kind, occupied):
		return false
	stock[kind] -= 1
	change_cell(p, kind)
	return true

func rebuild_all() -> void:
	for y in range(-1, 2):
		for z in range(-3, 3):
			for x in range(-3, 3):
				rebuild_chunk(Vector3i(x, y, z))

func rebuild_chunk(key: Vector3i) -> void:
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	var indices := PackedInt32Array()
	var origin := key * CHUNK
	for y in CHUNK:
		for z in CHUNK:
			for x in CHUNK:
				var p := origin + Vector3i(x, y, z)
				var kind := get_cell(p)
				if kind == EMPTY:
					continue
				for direction in DIRECTIONS:
					if get_cell(p + direction) != EMPTY:
						continue
					var normal := Vector3(direction)
					var u := Vector3.RIGHT if direction.y != 0 else Vector3.UP
					var v := normal.cross(u)
					var center := Vector3(p) + Vector3.ONE * 0.5 + normal * 0.5
					var first := vertices.size()
					var shade: Color = COLORS[kind]
					if kind == SOIL and direction == Vector3i.UP:
						shade = Color(0.31, 0.47, 0.20)
					shade *= 0.94 + posmod(p.x * 3 + p.z * 7 + p.y, 7) * 0.01
					shade.a = 1.0
					for corner in [center - u * 0.5 - v * 0.5, center + u * 0.5 - v * 0.5, center + u * 0.5 + v * 0.5, center - u * 0.5 + v * 0.5]:
						vertices.append(corner)
						normals.append(normal)
						colors.append(shade)
					for i in [0, 2, 1, 0, 3, 2]:
						indices.append(first + i)
	var body: StaticBody3D = chunks.get(key)
	if body == null:
		body = StaticBody3D.new()
		body.collision_layer = 1
		body.set_meta("voxel_chunk", true)
		var mesh_node := MeshInstance3D.new()
		mesh_node.name = "Mesh"
		body.add_child(mesh_node)
		var collision := CollisionShape3D.new()
		collision.name = "Collision"
		body.add_child(collision)
		add_child(body)
		chunks[key] = body
	triangle_count -= int(body.get_meta("triangles", 0))
	var triangles := indices.size() / 3.0
	body.set_meta("triangles", int(triangles))
	triangle_count += int(triangles)
	if vertices.is_empty():
		body.get_node("Mesh").mesh = null
		body.get_node("Collision").shape = null
		return
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colors
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.surface_set_material(0, material)
	body.get_node("Mesh").mesh = mesh
	body.get_node("Collision").shape = mesh.create_trimesh_shape()

func generator_id() -> String:
	return "hill-v1"

func save_world(path: String) -> Error:
	var changes := []
	for p in edits:
		changes.append([p.x, p.y, p.z, edits[p]])
	var data := {"version": 1, "generator": generator_id(), "edits": changes, "stock": [stock[1], stock[2], stock[3], stock[4]]}
	data.merge(save_metadata())
	var file := FileAccess.open(path + ".tmp", FileAccess.WRITE)
	if file == null:
		return FileAccess.get_open_error()
	file.store_string(JSON.stringify(data))
	file.flush()
	var result := file.get_error()
	file.close()
	if result != OK:
		return result
	return DirAccess.rename_absolute(ProjectSettings.globalize_path(path + ".tmp"), ProjectSettings.globalize_path(path))

func load_world(path: String) -> Error:
	if not FileAccess.file_exists(path):
		return ERR_FILE_NOT_FOUND
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not data is Dictionary or data.get("version") != 1 or data.get("generator") != generator_id():
		return ERR_FILE_CORRUPT
	if not validate_metadata(data): return ERR_FILE_CORRUPT
	var changes = data.get("edits")
	var amounts = data.get("stock")
	if not changes is Array or not amounts is Array or amounts.size() != 4:
		return ERR_FILE_CORRUPT
	for amount in amounts:
		if not (amount is float or amount is int) or amount < 0 or amount != floor(amount):
			return ERR_FILE_CORRUPT
	for row in changes:
		if not row is Array or row.size() != 4:
			return ERR_FILE_CORRUPT
		for value in row:
			if not (value is float or value is int) or value != floor(value):
				return ERR_FILE_CORRUPT
		var p := Vector3i(row[0], row[1], row[2])
		if not contains_cell(p) or is_bedrock(p) or row[3] < EMPTY or row[3] > BRICK:
			return ERR_FILE_CORRUPT
	reset_data()
	for row in changes:
		var p := Vector3i(row[0], row[1], row[2])
		store_cell(p,int(row[3]))
		edits[p] = int(row[3])
	for i in 4:
		stock[i + 1] = int(amounts[i])
	restore_metadata(data)
	rebuild_all()
	return OK

func save_metadata() -> Dictionary:
	return {}

func validate_metadata(_data: Dictionary) -> bool:
	return true

func restore_metadata(_data: Dictionary) -> void:
	pass
