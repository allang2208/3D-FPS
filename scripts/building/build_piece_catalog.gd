extends RefCounted

const PATHS := {
	"wood":"res://data/building/wood.tres",
	"stone":"res://data/building/stone.tres",
	"marble":"res://data/building/marble.tres",
	"railing":"res://data/building/railing.tres",
	"door":"res://data/building/door.tres",
}
const PANEL_ORDER := ["wood","stone","marble","railing","door"]
const LEGACY := {
	"floor":"wood","wall":"wood","ceiling":"wood",
	"stone_floor":"stone","stone_wall":"stone","stone_ceiling":"stone",
}
static var _cache := {}

static func canonical_id(kind: String) -> String:
	return LEGACY.get(kind,kind)

static func definition(kind: String) -> Resource:
	var canonical := canonical_id(kind)
	if not PATHS.has(canonical): return null
	if not _cache.has(canonical): _cache[canonical]=load(PATHS[canonical])
	return _cache[canonical]

static func panel_definitions() -> Array[Resource]:
	var result: Array[Resource]=[]
	for kind in PANEL_ORDER:
		var value:=definition(kind)
		if value!=null: result.append(value)
	return result

static func rotated_offset(offset: Vector3i, rotation_quarters: int) -> Vector3i:
	match wrapi(rotation_quarters,0,4):
		1: return Vector3i(offset.z,offset.y,-offset.x)
		2: return Vector3i(-offset.x,offset.y,-offset.z)
		3: return Vector3i(-offset.z,offset.y,offset.x)
	return offset

static func occupied_offsets(kind: String, rotation_quarters: int) -> Array[Vector3i]:
	var result: Array[Vector3i]=[]
	var value:=definition(kind)
	if value==null: return result
	for y in range(value.footprint_cells.y):
		for z in range(value.footprint_cells.z):
			for x in range(value.footprint_cells.x):
				result.append(rotated_offset(Vector3i(x,y,z),rotation_quarters))
	return result

static func bottom_offsets(kind: String, rotation_quarters: int) -> Array[Vector3i]:
	var result: Array[Vector3i]=[]
	for offset in occupied_offsets(kind,rotation_quarters):
		if offset.y==0: result.append(offset)
	return result

static func build_occupancy(cells: Dictionary, rotations: Dictionary) -> Dictionary:
	var result := {}
	for root in cells:
		for offset in occupied_offsets(str(cells[root]),int(rotations.get(root,0))):
			result[root+offset]=root
	return result

static func supports_weight(kind: String) -> bool:
	var value:=definition(kind)
	return value!=null and value.supports_weight
