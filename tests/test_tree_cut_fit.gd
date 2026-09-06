extends SceneTree
const Cutter=preload("res://scripts/tools/tree_cut_mesh.gd")
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	for variant in 3:
		var body:=Node3D.new()
		root.add_child(body)
		var model: Node3D=load("res://scenes/imported_pine.tscn").instantiate()
		model.variant=variant
		body.add_child(model)
		model.position.y=-model.burial_depth
		model.setup_lod()
		var baseline:=Cutter.split_tree(body,0.65)
		assert(not baseline.contours.is_empty(),"Real trunk must yield closed cut contours")
		var cap:=Cutter.section_mesh(baseline.contours,true)
		assert(cap!=null)
		var vertices: PackedVector3Array=cap.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		for p in vertices:
			assert(absf(p.y-0.65)<0.00001)
			var edge_match:=false
			for ring in baseline.contours:
				for edge in ring:
					if p.distance_squared_to(edge)<0.0000000001: edge_match=true
			assert(edge_match,"Cap vertex may not exceed the real cross-section")
		model.position+=Vector3(1.4,0,-2.1)
		var shifted:=Cutter.split_tree(body,0.65)
		assert(is_equal_approx(baseline.radius,shifted.radius),"Offset trunk must not inflate diameter")
		assert(shifted.center.distance_to(baseline.center+Vector3(1.4,0,-2.1))<0.0001)
		print("CUT_FIT variant=",variant," contours=",baseline.contours.size()," radius=",baseline.radius," cap_triangles=",vertices.size()/3)
		baseline.lower.free()
		baseline.upper.free()
		shifted.lower.free()
		shifted.upper.free()
		body.free()
	print("TREE_CUT_FIT PASS: three current pine variants, seam-bound caps, offset invariance")
	quit()
