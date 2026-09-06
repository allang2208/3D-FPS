extends RefCounted
## Clip only the authored near mesh. Keep imported UVs, normals and materials.
static func split_tree(body: Node3D, cut_height: float) -> Dictionary:
	var lower:=Node3D.new()
	var upper:=Node3D.new()
	var segments: Array=[]
	var height:=0.0
	var bark: Material
	for source in body.find_children("","MeshInstance3D",true,false):
		if source.mesh==null or source.has_meta("harvest_scar") or source.get_meta("scenic_lod",0)!=0 or source.visibility_range_begin>0: continue
		var xf: Transform3D=body.global_transform.affine_inverse()*source.global_transform
		var normal_xf:=xf.basis.inverse().transposed()
		var meshes: Array[ArrayMesh]=[ArrayMesh.new(),ArrayMesh.new()]
		for surface in source.mesh.get_surface_count():
			var arrays: Array=source.mesh.surface_get_arrays(surface)
			var verts: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]
			var uv: PackedVector2Array=arrays[Mesh.ARRAY_TEX_UV] if arrays[Mesh.ARRAY_TEX_UV]!=null else PackedVector2Array()
			var colors: PackedColorArray=arrays[Mesh.ARRAY_COLOR] if arrays[Mesh.ARRAY_COLOR]!=null else PackedColorArray()
			var indices: PackedInt32Array=arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX]!=null else PackedInt32Array()
			var mat: Material=source.get_active_material(surface)
			var title:=mat.resource_name.to_lower() if mat!=null else ""
			var woody:=not ("leav" in title or "twig" in title or "canopy_branches" in title)
			if woody and bark==null: bark=mat
			var builders: Array[SurfaceTool]=[SurfaceTool.new(),SurfaceTool.new()]
			var counts: Array[int]=[0,0]
			for st in builders: st.begin(Mesh.PRIMITIVE_TRIANGLES)
			var n:=indices.size() if not indices.is_empty() else verts.size()
			for t in range(0,n,3):
				var triangle: Array=[]
				for j in 3:
					var index:=indices[t+j] if not indices.is_empty() else t+j
					var p:=xf*verts[index]
					height=maxf(height,p.y)
					triangle.append([p,(normal_xf*normals[index]).normalized() if not normals.is_empty() else Vector3.UP,uv[index] if not uv.is_empty() else Vector2.ZERO,colors[index] if not colors.is_empty() else Color.WHITE])
				for side in 2:
					var polygon:=clip(triangle,cut_height,side==1)
					for j in range(1,polygon.size()-1):
						for v in [polygon[0],polygon[j],polygon[j+1]]:
							builders[side].set_normal(v[1])
							builders[side].set_uv(v[2])
							builders[side].set_color(v[3])
							builders[side].add_vertex(v[0])
							counts[side]+=1
					if side==1 and woody:
						for j in polygon.size():
							var a: Vector3=polygon[j][0]
							var b: Vector3=polygon[(j+1)%polygon.size()][0]
							if absf(a.y-cut_height)<0.00001 and absf(b.y-cut_height)<0.00001 and a.distance_squared_to(b)>0.0000000001:
								segments.append([a,b])
			for side in 2:
				if counts[side]>0:
					builders[side].set_material(mat)
					builders[side].generate_tangents()
					builders[side].commit(meshes[side])
		for side in 2:
			if meshes[side].get_surface_count()>0:
				var node:=MeshInstance3D.new()
				node.mesh=meshes[side]
				(lower if side==0 else upper).add_child(node)
	var contours:=cut_contours(segments)
	var radius:=0.001
	var center:=Vector3(0,cut_height,0)
	var largest_area:=0.0
	for contour in contours:
		var area:=0.0
		var sum:=Vector3.ZERO
		for i in contour.size():
			var a: Vector3=contour[i]
			var b: Vector3=contour[(i+1)%contour.size()]
			area+=a.x*b.z-b.x*a.z
			sum+=a
		if absf(area)>largest_area:
			largest_area=absf(area)
			center=sum/contour.size()
			radius=0.001
			for p in contour: radius=maxf(radius,Vector2(p.x-center.x,p.z-center.z).length())
	return {"lower":lower,"upper":upper,"height":height,"radius":radius,"center":center,"contours":contours,"bark":bark}

## Walk the welded intersection edges, keeping disconnected sections separate.
## A hull or bounding circle would bridge gaps and grow beyond concave bark.
static func cut_contours(segments: Array) -> Array:
	var positions: Dictionary={}
	var neighbors: Dictionary={}
	for segment in segments:
		var a:=Vector3i((segment[0]*100000.0).round())
		var b:=Vector3i((segment[1]*100000.0).round())
		if a==b: continue
		positions[a]=segment[0]
		positions[b]=segment[1]
		if not neighbors.has(a): neighbors[a]=[]
		if not neighbors.has(b): neighbors[b]=[]
		if not neighbors[a].has(b): neighbors[a].append(b)
		if not neighbors[b].has(a): neighbors[b].append(a)
	var visited: Dictionary={}
	var result: Array=[]
	for start: Vector3i in neighbors:
		if visited.has(start): continue
		var chain: Array[Vector3]=[]
		var current:=start
		var previous:=start
		var closed:=false
		for step in neighbors.size()+1:
			if neighbors[current].size()!=2: break
			visited[current]=true
			chain.append(positions[current])
			var next: Vector3i=neighbors[current][0]
			if next==previous: next=neighbors[current][1]
			previous=current
			current=next
			if current==start:
				closed=true
				break
			if visited.has(current): break
		if closed and chain.size()>=3: result.append(chain)
	return result

static func section_mesh(contours: Array, up: bool) -> ArrayMesh:
	var st:=SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var count:=0
	for contour in contours:
		var polygon:=PackedVector2Array()
		var bounds:=Rect2(Vector2(contour[0].x,contour[0].z),Vector2.ZERO)
		for p in contour:
			var v:=Vector2(p.x,p.z)
			polygon.append(v)
			bounds=bounds.expand(v)
		var triangles:=Geometry2D.triangulate_polygon(polygon)
		for i in range(0,triangles.size(),3):
			var ids: Array[int]=[triangles[i],triangles[i+1],triangles[i+2]]
			var a: Vector3=contour[ids[0]]
			var b: Vector3=contour[ids[1]]
			var c: Vector3=contour[ids[2]]
			# Godot front faces use clockwise winding.
			if ((b-a).cross(c-a).y<0)!=up: ids.reverse()
			for id in ids:
				var p: Vector3=contour[id]
				st.set_normal(Vector3.UP if up else Vector3.DOWN)
				st.set_uv((Vector2(p.x,p.z)-bounds.position)/bounds.size.max(Vector2.ONE*0.00001))
				st.add_vertex(p)
				count+=1
	return st.commit() if count>0 else null

static func clip(input: Array, y: float, above: bool) -> Array:
	var output: Array=[]
	for i in input.size():
		var a: Array=input[i]
		var b: Array=input[(i+1)%input.size()]
		var ina: bool=a[0].y>=y if above else a[0].y<=y
		var inb: bool=b[0].y>=y if above else b[0].y<=y
		if ina: output.append(a)
		if ina!=inb:
			var t: float=(y-a[0].y)/(b[0].y-a[0].y)
			output.append([a[0].lerp(b[0],t),a[1].lerp(b[1],t).normalized(),a[2].lerp(b[2],t),a[3].lerp(b[3],t)])
	return output
