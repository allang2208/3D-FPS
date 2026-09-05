extends RefCounted

## Three slender, segmented blades per tuft; vertices share a grounded root.
static func grass_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for blade in 3:
		var direction := Vector3(cos(blade * 2.4), 0, sin(blade * 2.4))
		var across := Vector3(-direction.z, 0, direction.x)
		var length := 0.72 + blade * 0.14
		for row in 6:
			var t := row / 5.0
			var center := Vector3.UP * (t * length) + direction * t * t * (0.6 + blade * 0.15)
			var width := (0.24 + blade * 0.025) * pow(1.0 - t, 0.7)
			for side in 2:
				st.set_uv(Vector2(side, t))
				st.set_normal((Vector3.UP * 0.6 + direction).normalized())
				st.add_vertex(center + across * width * (side * 2 - 1))
		for row in 5:
			var a := blade * 12 + row * 2
			for i in [a, a + 2, a + 1, a + 1, a + 2, a + 3]:
				st.add_index(i)
	return st.commit()
