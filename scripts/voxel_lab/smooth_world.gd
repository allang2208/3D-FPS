extends "res://scripts/voxel_lab/voxel_world.gd"
## Surface nets：全局采样坐标 + 连续密度梯度，区块共用相同的边界顶点。
const CORNERS := [Vector3i(0,0,0),Vector3i(1,0,0),Vector3i(0,1,0),Vector3i(1,1,0),Vector3i(0,0,1),Vector3i(1,0,1),Vector3i(0,1,1),Vector3i(1,1,1)]
const EDGES := [[0,1],[2,3],[4,5],[6,7],[0,2],[1,3],[4,6],[5,7],[0,4],[1,5],[2,6],[3,7]]
const RINGS := [[Vector3i.ZERO,Vector3i(0,-1,0),Vector3i(0,-1,-1),Vector3i(0,0,-1)], [Vector3i.ZERO,Vector3i(0,0,-1),Vector3i(-1,0,-1),Vector3i(-1,0,0)], [Vector3i.ZERO,Vector3i(-1,0,0),Vector3i(-1,-1,0),Vector3i(0,-1,0)]]
var noise := FastNoiseLite.new()
var ground_material: ShaderMaterial
var active_edits: Dictionary = {}
var source_heights: Dictionary = {}
var source_id := ""
var grid_height_cache: Dictionary = {}
var edit_history: Array[Dictionary] = []

## 必须在 add_child 前调用。捕获旷野高度快照，不改写 Terrain3D 或其碰撞。
## patch_origin 为体素组件在旷野中的位置，高度转换为组件局部坐标。
func configure_from_terrain(data: Object, patch_origin: Vector3, terrain_id: String, horizontal_scale := 1.0) -> Error:
	if is_inside_tree() or terrain_id.is_empty() or not is_finite(horizontal_scale) or horizontal_scale<=0:
		return ERR_INVALID_PARAMETER
	var sampled := {}
	for z in range(-27,28):
		for x in range(-27,28):
			var h: float = data.get_height(patch_origin+Vector3(x*horizontal_scale,0,z*horizontal_scale))
			if not is_finite(h) or h-patch_origin.y < -4 or h-patch_origin.y > 12:
				return ERR_INVALID_DATA
			sampled[Vector2i(x,z)] = h-patch_origin.y
	source_heights = sampled
	grid_height_cache.clear()
	source_id = terrain_id
	position = patch_origin
	scale=Vector3(horizontal_scale,1,horizontal_scale)
	return OK

func _ready() -> void:
	noise.seed = 731
	noise.frequency = 0.17
	noise.fractal_octaves = 3
	ground_material = ShaderMaterial.new()
	ground_material.shader = preload("res://scripts/voxel_lab/natural_ground.gdshader")
	for pair in [["grass", "grass004"], ["soil", "ground020"], ["rock", "rock063"]]:
		ground_material.set_shader_parameter(pair[0] + "_color", load("res://assets/textures/terrain_prepared/" + pair[1] + "_alb_ht.png"))
		ground_material.set_shader_parameter(pair[0] + "_normal", load("res://assets/textures/terrain_prepared/" + pair[1] + "_nrm_rgh.png"))
	ground_material.set_shader_parameter("soil_color",load("res://assets/textures/wilderness_generated/loam_albedo_v1.png"))
	ground_material.set_shader_parameter("grass_color",load("res://assets/textures/wilderness_generated/turf_albedo_v1.png"))
	preload("res://scripts/wilderness_materials.gd").configure_voxel(ground_material)
	super._ready()

func generator_id() -> String:
	return "smooth-hill-v2" if source_id.is_empty() else "terrain-snapshot-v1:"+source_id+":"+str(hash(source_heights))

func natural_height(x: float, z: float) -> float:
	var key := Vector2(x,z)
	if grid_height_cache.has(key):
		return grid_height_cache[key]
	var result: float
	if not source_heights.is_empty():
		var ix := clampi(floori(x),-27,26)
		var iz := clampi(floori(z),-27,26)
		var fx := clampf(x-ix,0,1)
		var fz := clampf(z-iz,0,1)
		result = lerpf(lerpf(source_heights[Vector2i(ix,iz)],source_heights[Vector2i(ix+1,iz)],fx),lerpf(source_heights[Vector2i(ix,iz+1)],source_heights[Vector2i(ix+1,iz+1)],fx),fz)
	else:
		result = 1.0 + 7.0 * exp(-pow((x - 7.0) / 9.0, 2.0) - pow(z / 13.0, 2.0)) + noise.get_noise_2d(x,z) * 1.1 + noise.get_noise_2d(x * 3.1,z * 3.1) * 0.18
	# 只缓存固定采样网格，避免每层 Y 重复计算相同山形；不缓存编辑后的密度。
	if x == floorf(x) and z == floorf(z):
		grid_height_cache[key] = result
	return result

func reset_data() -> void:
	grid_height_cache.clear()
	edit_history.clear()
	super.reset_data()

func mine(p: Vector3i) -> bool:
	var record := {"cell":p,"kind":get_cell(p),"stock":stock.duplicate()}
	if not super.mine(p):
		return false
	remember(record)
	return true

func can_place(p: Vector3i, kind: int, occupied: AABB) -> bool:
	if not super.can_place(p,kind,occupied):
		return false
	if kind != BRICK:
		var center := Vector3(p)+Vector3.ONE*0.5
		var nearest := center.clamp(occupied.position,occupied.end)
		# 圆形填土含融合带，不能仅用格子包围盒检测玩家。
		if center.distance_squared_to(nearest) < 1.02*1.02:
			return false
	return true

func place(p: Vector3i, kind: int, occupied: AABB) -> bool:
	var record := {"cell":p,"kind":get_cell(p),"stock":stock.duplicate()}
	if not super.place(p,kind,occupied):
		return false
	remember(record)
	return true

func remember(record: Dictionary) -> void:
	edit_history.append(record)
	if edit_history.size()>32:
		edit_history.pop_front()

func undo_edit(occupied: AABB) -> bool:
	if edit_history.is_empty():
		return false
	var record: Dictionary = edit_history.back()
	if record.kind != EMPTY:
		var bounds := AABB(Vector3(record.cell)-Vector3.ONE*0.52,Vector3.ONE*2.04)
		if bounds.intersects(occupied):
			return false
	edit_history.pop_back()
	stock = record.stock.duplicate()
	change_cell(record.cell,record.kind)
	return true

func surface_weights(at: Vector3) -> Color:
	var disturbed := 0.0
	for p in active_edits:
		if active_edits[p] != BRICK:
			disturbed = maxf(disturbed,1.0-smoothstep(0.8,1.7,at.distance_to(Vector3(p)+Vector3.ONE*0.5)))
	var depth:=natural_height(at.x,at.z)-at.y
	return Color(smoothstep(5.0,8.0,depth),maxf(disturbed,smoothstep(0.04,0.25,depth)),0,1)

func height_at(x: int, z: int) -> int:
	return ceili(natural_height(x + 0.5, z + 0.5))

func smooth_min(a: float, b: float) -> float:
	var h := maxf(0.26 - absf(a-b), 0.0) / 0.26
	return minf(a,b) - h*h*0.065

func field(p: Vector3, changes: Dictionary) -> float:
	var d := p.y - natural_height(p.x, p.z)
	for cell in changes:
		var kind: int = changes[cell]
		if kind == BRICK:
			# 砖块只替换其真实立方体内的地形，不再挖出大于砖底的圆坑。
			var q := (p-Vector3(cell)-Vector3.ONE*0.5).abs()-Vector3.ONE*0.5
			var box_distance := q.max(Vector3.ZERO).length()+minf(maxf(q.x,maxf(q.y,q.z)),0.0)
			d = maxf(d,-box_distance)
			continue
		var ball := p.distance_to(Vector3(cell) + Vector3.ONE * 0.5) - 0.95
		if kind == EMPTY:
			d = -smooth_min(-d, ball)
		else:
			d = smooth_min(d, ball)
	return limit_density(d,p)

func limit_density(d: float, p: Vector3) -> float:
	return maxf(d, maxf(maxf(absf(p.x)-24.0,absf(p.z)-24.0),maxf(-8.0-p.y,p.y-16.0)))

func density(p: Vector3) -> float:
	return field(p, edits)

func normal_at(p: Vector3) -> Vector3:
	var e := 0.08
	return Vector3(field(p+Vector3(e,0,0),active_edits)-field(p-Vector3(e,0,0),active_edits), field(p+Vector3(0,e,0),active_edits)-field(p-Vector3(0,e,0),active_edits), field(p+Vector3(0,0,e),active_edits)-field(p-Vector3(0,0,e),active_edits)).normalized()

func surface_position(at: Vector3) -> Vector3:
	return at

func affected_chunks(p: Vector3i) -> Dictionary:
	var dirty := {}
	# 球半径、融合带和 surface-net 邻接单元需要额外边界。
	for z in range(p.z-2,p.z+3):
		for y in range(p.y-2,p.y+3):
			for x in range(p.x-2,p.x+3):
				var q := Vector3i(x,y,z)
				if contains_cell(q):
					dirty[chunk_of(q)] = true
	return dirty

func rebuild_chunk(key: Vector3i) -> void:
	var origin := key * CHUNK
	active_edits = {}
	for p in edits:
		if AABB(Vector3(origin)-Vector3.ONE*3.0,Vector3.ONE*14.0).has_point(Vector3(p)):
			active_edits[p] = edits[p]
	var samples := {}
	for y in range(-1,9):
		for z in range(-1,9):
			for x in range(-1,9):
				var p := origin + Vector3i(x,y,z)
				samples[p] = field(Vector3(p),active_edits)
	var dual := {}
	for y in range(-1,8):
		for z in range(-1,8):
			for x in range(-1,8):
				var p := origin + Vector3i(x,y,z)
				var inside_count := 0
				for corner in CORNERS:
					if samples[p+corner] < 0:
						inside_count += 1
				if inside_count == 0 or inside_count == 8:
					continue
				var position_sum := Vector3.ZERO
				var count := 0
				for edge in EDGES:
					var a: Vector3i = p + CORNERS[edge[0]]
					var b: Vector3i = p + CORNERS[edge[1]]
					var da: float = samples[a]
					var db: float = samples[b]
					if (da < 0) == (db < 0):
						continue
					position_sum += Vector3(a).lerp(Vector3(b),da/(da-db))
					count += 1
				if count > 0:
					var at := surface_position(position_sum / count)
					dual[p] = [at,normal_at(at)]
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	for y in CHUNK:
		for z in CHUNK:
			for x in CHUNK:
				var p := origin + Vector3i(x,y,z)
				for axis in 3:
					var step := Vector3i.ZERO
					step[axis] = 1
					if (samples[p] < 0) == (samples[p+step] < 0):
						continue
					var quad := []
					for offset in RINGS[axis]:
						if dual.has(p+offset):
							quad.append(dual[p+offset])
					if quad.size() != 4:
						continue
					for tri in [[0,1,2],[0,2,3]]:
						var a: Vector3 = quad[tri[0]][0]
						var b: Vector3 = quad[tri[1]][0]
						var c: Vector3 = quad[tri[2]][0]
						if (b-a).cross(c-a).length_squared() < 0.00000001:
							continue
						if (b-a).cross(c-a).dot(quad[tri[0]][1]+quad[tri[1]][1]+quad[tri[2]][1]) > 0:
							tri.reverse()
						for i in tri:
							var at: Vector3 = quad[i][0]
							vertices.append(at)
							normals.append(quad[i][1])
							colors.append(surface_weights(at))
	var mesh := ArrayMesh.new()
	if not vertices.is_empty():
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = vertices
		arrays[Mesh.ARRAY_NORMAL] = normals
		arrays[Mesh.ARRAY_COLOR] = colors
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		mesh.surface_set_material(0,ground_material)
	var bricks := SurfaceTool.new()
	bricks.begin(Mesh.PRIMITIVE_TRIANGLES)
	var brick_count := 0
	for p in edits:
		if edits[p] == BRICK and chunk_of(p) == key:
			var box := BoxMesh.new()
			box.size = Vector3.ONE
			bricks.append_from(box,0,Transform3D(Basis.IDENTITY,Vector3(p)+Vector3.ONE*0.5))
			brick_count += 1
	if brick_count > 0:
		bricks.commit(mesh)
		var brick_mat := StandardMaterial3D.new()
		brick_mat.albedo_color = COLORS[BRICK]
		brick_mat.roughness = 0.9
		mesh.surface_set_material(mesh.get_surface_count()-1,brick_mat)
	var body: StaticBody3D = chunks.get(key)
	if body == null:
		body = StaticBody3D.new()
		body.collision_layer = 1
		body.set_meta("voxel_chunk",true)
		var mi := MeshInstance3D.new()
		mi.name = "Mesh"
		body.add_child(mi)
		var shape := CollisionShape3D.new()
		shape.name = "Collision"
		body.add_child(shape)
		add_child(body)
		chunks[key] = body
	triangle_count -= int(body.get_meta("triangles",0))
	var count := int(vertices.size()/3.0) + brick_count*12
	triangle_count += count
	body.set_meta("triangles",count)
	body.get_node("Mesh").mesh = mesh if count > 0 else null
	body.get_node("Collision").shape = mesh.create_trimesh_shape() if count > 0 else null
