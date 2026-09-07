extends RefCounted
## Visual-only edge rounding. Shared faces keep the exact half-metre grid.
const HALF := 0.25
const RADIUS := 0.036
const AXES := [Vector3i(1,0,0), Vector3i(0,1,0), Vector3i(0,0,1)]
var cache := {}

func for_cell(cell: Vector3i, cells: Dictionary) -> ArrayMesh:
	var mask := 0
	var bit := 0
	for a in range(3):
		for b in range(a+1,3):
			for sa in [-1,1]:
				for sb in [-1,1]:
					if edge_clear(cell,AXES[a]*sa,AXES[b]*sb,cells): mask |= 1 << bit
					bit += 1
	if cache.has(mask): return cache[mask]
	var faces: Array = []
	for axis in AXES:
		for sign_value in [-1,1]:
			var n := Vector3(axis * sign_value)
			var u := n.cross(Vector3.UP if absf(n.y) < .5 else Vector3.RIGHT)
			var v := n.cross(u)
			var c := n * HALF
			faces.append({"normal":n,"rounded":false,"points":[c-u*HALF-v*HALF,c-u*HALF+v*HALF,c+u*HALF+v*HALF,c+u*HALF-v*HALF]})
	bit=0
	for a in range(3):
		for b in range(a+1,3):
			for sa in [-1,1]:
				for sb in [-1,1]:
					var da: Vector3i = AXES[a]*sa
					var db: Vector3i = AXES[b]*sb
					var rounded := (mask & (1 << bit)) != 0
					bit += 1
					if not rounded: continue
					# Eleven segments keep the wider exposed edge visually round.
					for section in range(1,12):
						var angle := PI*.5*section/12.0
						var n := Vector3(da)*cos(angle)+Vector3(db)*sin(angle)
						var distance := (HALF-RADIUS)*(cos(angle)+sin(angle))+RADIUS
						faces = clip(faces,n,distance)
	# Spherical corner caps soften the meeting of three exposed rounded edges.
	for sx in [-1,1]:
		for sy in [-1,1]:
			for sz in [-1,1]:
				var x := Vector3i(sx,0,0)
				var y := Vector3i(0,sy,0)
				var z := Vector3i(0,0,sz)
				if not (edge_clear(cell,x,y,cells) and edge_clear(cell,x,z,cells) and edge_clear(cell,y,z,cells)): continue
				for direction in [Vector3(1,1,1),Vector3(2,1,1),Vector3(1,2,1),Vector3(1,1,2),Vector3(2,2,1),Vector3(2,1,2),Vector3(1,2,2)]:
					var n: Vector3 = (direction*Vector3(sx,sy,sz)).normalized()
					faces=clip(faces,n,(HALF-RADIUS)*(absf(n.x)+absf(n.y)+absf(n.z))+RADIUS)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for face in faces:
		var points: Array = face.points
		for i in range(1,points.size()-1):
			for p in [points[0],points[i],points[i+1]]:
				var normal: Vector3 = face.normal
				if face.rounded:
					normal=Vector3.ZERO
					for adjacent in faces:
						if absf(adjacent.normal.dot(p-adjacent.points[0])) < .00001:
							normal += adjacent.normal
					normal=normal.normalized()
				st.set_normal(normal)
				st.add_vertex(p)
	var mesh := st.commit()
	cache[mask]=mesh
	return mesh

static func edge_clear(cell: Vector3i, a: Vector3i, b: Vector3i, cells: Dictionary) -> bool:
	if cells.has(cell+a) or cells.has(cell+b) or cells.has(cell+a+b): return false
	var along := Vector3i(Vector3(a).cross(Vector3(b)))
	# A continuous edge shares one profile. A square junction conservatively
	# keeps the whole run square, avoiding mismatched cuts at shared faces.
	for direction in [along,-along]:
		var next: Vector3i = cell+direction
		while cells.has(next):
			if cells.has(next+a) or cells.has(next+b) or cells.has(next+a+b): return false
			next += direction
	return true

static func clip(faces: Array, normal: Vector3, distance: float) -> Array:
	var result: Array = []
	var cap: Array = []
	for face in faces:
		var polygon: Array = face.points
		var trimmed: Array = []
		for i in polygon.size():
			var a: Vector3 = polygon[i]
			var b: Vector3 = polygon[(i+1)%polygon.size()]
			var da := normal.dot(a)-distance
			var db := normal.dot(b)-distance
			if da <= .000001: trimmed.append(a)
			if (da < 0 and db > 0) or (da > 0 and db < 0):
				var p := a.lerp(b,da/(da-db))
				trimmed.append(p)
				var duplicate := false
				for existing in cap:
					if p.distance_squared_to(existing) < .0000000001: duplicate=true
				if not duplicate: cap.append(p)
		if trimmed.size() >= 3:
			result.append({"normal":face.normal,"rounded":face.rounded,"points":trimmed})
	if cap.size() >= 3:
		var center := Vector3.ZERO
		for p in cap: center += p
		center /= cap.size()
		var u := normal.cross(Vector3.UP if absf(normal.y) < .5 else Vector3.RIGHT).normalized()
		var v := normal.cross(u)
		cap.sort_custom(func(a: Vector3,b: Vector3): return atan2((a-center).dot(v),(a-center).dot(u)) > atan2((b-center).dot(v),(b-center).dot(u)))
		result.append({"normal":normal,"rounded":true,"points":cap})
	return result
