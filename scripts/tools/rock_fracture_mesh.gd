extends RefCounted
## Partition the rendered source mesh. Exterior UVs/materials survive the cut.
static func fracture(parts: Array) -> Array:
	var faces: Array=[]
	var bounds:=AABB()
	var started:=false
	for part in parts:
		var mesh: Mesh=part.mesh
		var xf: Transform3D=part.transform
		for surface in mesh.get_surface_count():
			var a:=mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array=a[Mesh.ARRAY_VERTEX]
			var indices: PackedInt32Array=a[Mesh.ARRAY_INDEX] if a[Mesh.ARRAY_INDEX]!=null else PackedInt32Array()
			var count:=indices.size() if not indices.is_empty() else vertices.size()
			for t in range(0,count,3):
				var tri: Array=[]
				for j in 3:
					var k:=indices[t+j] if not indices.is_empty() else t+j
					var p:=xf*vertices[k]
					bounds=bounds.expand(p) if started else AABB(p,Vector3.ZERO)
					started=true
					var n: Vector3=(xf.basis.inverse().transposed()*a[Mesh.ARRAY_NORMAL][k]).normalized()
					var uv: Vector2=a[Mesh.ARRAY_TEX_UV][k] if a[Mesh.ARRAY_TEX_UV]!=null else Vector2.ZERO
					tri.append([p,n,uv])
				faces.append([tri,mesh.surface_get_material(surface)])
	var groups: Array=[faces]
	for axis in 3:
		var next: Array=[]
		for group in groups:
			next.append_array(split(group,axis,bounds.get_center()[axis]))
		groups=next
	var result: Array=[]
	for group in groups:
		if group.is_empty(): continue
		var box:=AABB(group[0][0][0][0],Vector3.ZERO)
		var surfaces: Dictionary={}
		for face in group:
			if not surfaces.has(face[1]): surfaces[face[1]]=[]
			surfaces[face[1]].append(face[0])
			for v in face[0]: box=box.expand(v[0])
		var center:=box.get_center()
		var mesh:=ArrayMesh.new()
		for mat in surfaces:
			var st:=SurfaceTool.new()
			st.begin(Mesh.PRIMITIVE_TRIANGLES)
			st.set_material(mat)
			for tri in surfaces[mat]:
				for v in tri:
					st.set_normal(v[1])
					st.set_uv(v[2])
					st.add_vertex(v[0]-center)
			st.generate_tangents()
			st.commit(mesh)
		result.append({"mesh":mesh,"center":center})
	return result

static func split(faces: Array, axis: int, distance: float) -> Array:
	var halves: Array=[[],[]]
	var segments: Array=[]
	for face in faces:
		for side in 2:
			var polygon: Array=[]
			var tri: Array=face[0]
			for i in tri.size():
				var a: Array=tri[i]
				var b: Array=tri[(i+1)%tri.size()]
				var ina: bool=a[0][axis]>=distance if side==1 else a[0][axis]<=distance
				var inb: bool=b[0][axis]>=distance if side==1 else b[0][axis]<=distance
				if ina: polygon.append(a)
				if ina!=inb:
					var t: float=(distance-a[0][axis])/(b[0][axis]-a[0][axis])
					polygon.append([a[0].lerp(b[0],t),a[1].lerp(b[1],t).normalized(),a[2].lerp(b[2],t)])
			for j in range(1,polygon.size()-1): halves[side].append([[polygon[0],polygon[j],polygon[j+1]],face[1]])
			if side==1:
				for j in polygon.size():
					var a: Vector3=polygon[j][0]
					var b: Vector3=polygon[(j+1)%polygon.size()][0]
					if absf(a[axis]-distance)<0.00001 and absf(b[axis]-distance)<0.00001:
						segments.append([a,b])
	var contours:=preload("res://scripts/tools/tree_cut_mesh.gd").cut_contours(segments)
	for contour in contours:
		var polygon:=PackedVector2Array()
		for p in contour: polygon.append(Vector2(p[(axis+1)%3],p[(axis+2)%3]))
		var ids:=Geometry2D.triangulate_polygon(polygon)
		for side in 2:
			var normal:=Vector3.ZERO
			normal[axis]=1 if side==0 else -1
			for i in range(0,ids.size(),3):
				var order: Array=[ids[i],ids[i+1],ids[i+2]]
				var a: Vector3=contour[order[0]]
				var b: Vector3=contour[order[1]]
				var c: Vector3=contour[order[2]]
				if (b-a).cross(c-a).dot(normal)>0: order.reverse()
				var tri: Array=[]
				for k in order: tri.append([contour[k],normal,polygon[k]])
				halves[side].append([tri,faces[0][1]])
	return halves
