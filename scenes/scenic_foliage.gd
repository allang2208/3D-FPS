extends RefCounted

## Five asymmetric blades, still 30 triangles per near tuft; outer LODs stay smaller.
static func grass_mesh(blades: int = 5, segments: int = 3) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for blade in blades:
		# Irrational angular spacing, alternating root radii and sideways lean keep
		# the silhouette from resolving into a repeated star at eye level.
		var angle := blade * 2.39996 + sin(blade * 5.17) * 0.23
		var direction := Vector3(cos(angle), 0, sin(angle))
		var across := Vector3(-direction.z, 0, direction.x)
		var length := 0.58 + 0.34 * (0.5 + 0.5 * sin(blade * 3.7 + 0.4))
		var root_offset := direction * (0.045 + 0.028 * (blade % 3))
		var side_lean := across * sin(blade * 4.31) * 0.11
		for row in segments + 1:
			var t := row / float(segments)
			var center := root_offset + Vector3.UP * (t * length)
			center += direction * t * t * (0.22 + 0.045 * blade) + side_lean * t * t
			var width := (0.095 + 0.018 * (blade % 3)) * pow(1.0 - t, 0.78)
			for side in 2:
				st.set_uv(Vector2(side, t))
				st.set_normal((Vector3.UP * 0.6 + direction).normalized())
				st.add_vertex(center + across * width * (side * 2 - 1))
		for row in segments:
			var a := blade * (segments + 1) * 2 + row * 2
			for i in [a, a + 2, a + 1, a + 1, a + 2, a + 3]:
				st.add_index(i)
	return st.commit()
