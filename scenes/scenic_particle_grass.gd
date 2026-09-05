extends "res://addons/terrain_3d/extras/particle_example/terrain_3D_particles.gd"

## Give outer cells genuinely smaller meshes, rather than hiding processed blades.
func _create_grid() -> void:
	super._create_grid()
	var middle := preload("res://scenes/scenic_foliage.gd").grass_mesh(2, 3)
	var far_mesh := preload("res://scenes/scenic_foliage.gd").grass_mesh(1, 2)
	var half := grid_width / 2
	for i in particle_nodes.size():
		var ring := maxi(absi(i / grid_width - half), absi(i % grid_width - half))
		if ring >= 2:
			particle_nodes[i].draw_pass_1 = middle if ring == 2 else far_mesh
