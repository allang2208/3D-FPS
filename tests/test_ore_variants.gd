extends SceneTree
func _initialize() -> void: call_deferred("run")
func run() -> void:
	var variants := ["rounded", "slab", "leaning", "ridge", "wedge", "saddle", "tall", "long"]
	for variant in variants:
		var folder: String = "res://assets/models/ore_variants/"+variant+"/"
		var model: Node3D = load(folder+"model.scn").instantiate()
		root.add_child(model)
		var geometry: Dictionary = load("res://scenes/scenic_collision.gd").rock_geometry(model)
		assert(geometry.hull.size() >= 4 and geometry.support.size() > 0)
		var pieces: Array = load(folder+"fragments.res").get_meta("pieces")
		assert(pieces.size() == 8)
		var reconstructed := AABB()
		for i in pieces.size():
			var part: Dictionary = pieces[i]
			assert(part.hull.size() >= 4)
			var box: AABB = part.mesh.get_aabb()
			box.position += part.center
			reconstructed = box if i == 0 else reconstructed.merge(box)
		assert(reconstructed.position.is_equal_approx(geometry.bounds.position))
		assert(reconstructed.size.is_equal_approx(geometry.bounds.size))
		model.free()
	print("ORE_VARIANTS PASS: 8 collision hulls and matching 64 fragment bounds")
	quit()
