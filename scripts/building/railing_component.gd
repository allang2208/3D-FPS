extends RefCounted

const SIZE := Vector3(.5,.95,.18)
const DIRECTIONS: Array[Vector3i]=[Vector3i.LEFT,Vector3i.RIGHT,Vector3i.FORWARD,Vector3i.BACK]

static func connection_directions(cell: Vector3i, cells: Dictionary) -> Array[Vector3i]:
	var result: Array[Vector3i]=[]
	for direction in DIRECTIONS:
		if str(cells.get(cell+direction,""))=="railing": result.append(direction)
	return result

static func topology_kind(connections: Array[Vector3i]) -> String:
	match connections.size():
		0: return "isolated"
		1: return "end"
		2: return "straight" if connections[0]==-connections[1] else "corner"
		3: return "t"
		_: return "cross"

static func make_visual(body_material: Material, accent_material: Material, connections: Array[Vector3i]=[], rotation_quarters := 0) -> Node3D:
	var root:=Node3D.new()
	root.name="RailingVisual"
	root.set_meta("railing_topology",topology_kind(connections))
	_add_box(root,"CenterFoot",Vector3(.18,.14,.18),Vector3(0,-.18,0),body_material)
	_add_box(root,"CenterPost",Vector3(.10,.82,.10),Vector3(0,.205,0),body_material)
	_add_box(root,"CenterCap",Vector3(.14,.025,.14),Vector3(0,.6925,0),accent_material)
	for world_direction in _rendered_directions(connections,rotation_quarters):
		var local_direction:=_to_local_direction(world_direction,rotation_quarters)
		_add_arm(root,local_direction,body_material,accent_material)
		if not connections.has(world_direction): _add_end_post(root,local_direction,body_material,accent_material)
	return root

static func add_geometry(block: StaticBody3D, body_material: Material, accent_material: Material, connections: Array[Vector3i]=[]) -> void:
	rebuild_geometry(block,body_material,accent_material,connections)

static func rebuild_geometry(block: StaticBody3D, body_material: Material, accent_material: Material, connections: Array[Vector3i]) -> void:
	for child in block.get_children():
		if child.name=="RailingVisual" or child.has_meta("railing_collision"):
			block.remove_child(child)
			child.queue_free()
	var orientation:=wrapi(roundi(block.rotation.y/(PI*.5)),0,4)
	block.add_child(make_visual(body_material,accent_material,connections,orientation))
	block.set_meta("railing_topology",topology_kind(connections))
	_add_collision(block,"RailingCenter",Vector3(.18,.95,.18),Vector3(0,.225,0))
	for world_direction in _rendered_directions(connections,orientation):
		var local_direction:=_to_local_direction(world_direction,orientation)
		var size:=Vector3(.27,.95,.18) if local_direction.x!=0 else Vector3(.18,.95,.27)
		_add_collision(block,"RailingArm"+_direction_suffix(local_direction),size,Vector3(local_direction.x*.125,.225,local_direction.z*.125))

static func make_block(cell: Vector3i, rotation_quarters: int, body_material: Material, accent_material: Material, grid) -> StaticBody3D:
	var block:=StaticBody3D.new()
	block.name="Railing_%d_%d_%d" % [cell.x,cell.y,cell.z]
	block.position=grid.cell_center(cell)
	block.rotation.y=wrapi(rotation_quarters,0,4)*PI*.5
	block.set_meta("build_cell",cell)
	block.set_meta("impact_surface","metal")
	add_geometry(block,body_material,accent_material)
	return block

static func _rendered_directions(connections: Array[Vector3i], rotation_quarters: int) -> Array[Vector3i]:
	if connections.is_empty():
		var axis:=Vector3i.RIGHT if rotation_quarters%2==0 else Vector3i.FORWARD
		return [axis,-axis]
	if connections.size()==1: return [connections[0],-connections[0]]
	return connections.duplicate()

static func _to_local_direction(world_direction: Vector3i, rotation_quarters: int) -> Vector3i:
	var local:=Basis(Vector3.UP,wrapi(rotation_quarters,0,4)*PI*.5).inverse()*Vector3(world_direction)
	return Vector3i(roundi(local.x),0,roundi(local.z))

static func _add_arm(root: Node3D, direction: Vector3i, body_material: Material, accent_material: Material) -> void:
	var along_x:=direction.x!=0
	var offset:=Vector3(direction.x*.125,0,direction.z*.125)
	var suffix:=_direction_suffix(direction)
	var length_size:=Vector3(.27,.14,.18) if along_x else Vector3(.18,.14,.27)
	_add_box(root,"Foot"+suffix,length_size,offset+Vector3(0,-.18,0),body_material)
	length_size=Vector3(.27,.075,.10) if along_x else Vector3(.10,.075,.27)
	_add_box(root,"LowerRail"+suffix,length_size,offset+Vector3(0,.10,0),body_material)
	length_size=Vector3(.27,.13,.24) if along_x else Vector3(.24,.13,.27)
	_add_box(root,"Handrail"+suffix,length_size,offset+Vector3(0,.615,0),body_material)
	length_size=Vector3(.27,.025,.26) if along_x else Vector3(.26,.025,.27)
	_add_box(root,"SilverCap"+suffix,length_size,offset+Vector3(0,.6925,0),accent_material)

static func _add_end_post(root: Node3D, direction: Vector3i, body_material: Material, accent_material: Material) -> void:
	var at:=Vector3(direction.x*.25,.205,direction.z*.25)
	var suffix:=_direction_suffix(direction)
	_add_box(root,"EndPost"+suffix,Vector3(.10,.82,.10),at,body_material)
	_add_box(root,"EndCap"+suffix,Vector3(.14,.025,.14),at+Vector3(0,.4875,0),accent_material)

static func _direction_suffix(direction: Vector3i) -> String:
	if direction==Vector3i.LEFT: return "NX"
	if direction==Vector3i.RIGHT: return "PX"
	if direction==Vector3i.FORWARD: return "NZ"
	return "PZ"

static func _add_collision(parent: StaticBody3D, label: String, size: Vector3, position: Vector3) -> void:
	var shape:=BoxShape3D.new()
	shape.size=size
	var collision:=CollisionShape3D.new()
	collision.name=label
	collision.position=position
	collision.shape=shape
	collision.set_meta("railing_collision",true)
	parent.add_child(collision)

static func _add_box(parent: Node3D, label: String, size: Vector3, position: Vector3, material: Material) -> void:
	var mesh:=BoxMesh.new()
	mesh.size=size
	var visual:=MeshInstance3D.new()
	visual.name=label
	visual.mesh=mesh
	visual.material_override=material
	visual.position=position
	parent.add_child(visual)
