extends RefCounted

## Five narrow blades, still 30 triangles per near tuft; outer LODs stay smaller.
static func grass_mesh(blades: int = 5, segments: int = 3) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for blade in blades:
		var direction := Vector3(cos(blade * 2.4), 0, sin(blade * 2.4))
		var across := Vector3(-direction.z, 0, direction.x)
		var length := 0.74 + 0.28 * (0.5 + 0.5 * sin(blade * 3.7))
		var root_offset := direction * (0.06 + 0.025 * blade)
		for row in segments + 1:
			var t := row / float(segments)
			var center := root_offset + Vector3.UP * (t * length) + direction * t * t * (0.32 + 0.07 * blade)
			var width := (0.14 + 0.012 * (blade % 3)) * pow(1.0 - t, 0.85)
			for side in 2:
				st.set_uv(Vector2(side, t))
				st.set_normal((Vector3.UP * 0.6 + direction).normalized())
				st.add_vertex(center + across * width * (side * 2 - 1))
		for row in segments:
			var a := blade * (segments + 1) * 2 + row * 2
			for i in [a, a + 2, a + 1, a + 1, a + 2, a + 3]:
				st.add_index(i)
	return st.commit()
