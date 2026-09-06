extends SceneTree
const Rock = preload("res://scripts/ore_crystal_projectile.gd")
func _initialize() -> void: call_deferred("run")
func run() -> void:
	var world := Node3D.new()
	root.add_child(world)
	var p := Rock.new()
	world.add_child(p)
	p.set_physics_process(false)
	p._finish(true)
	p._finish(true)
	assert(get_nodes_in_group("ore_impact_fx").size() == 1)
	var fx = get_nodes_in_group("ore_impact_fx")[0]
	fx.set_process(false)
	assert(fx.dust.size() == 18 and fx.chips.size() == 12)
	fx._process(.2)
	assert(fx.chips[0].position.y > .1 and fx.dust[0].position.length() > .5)
	fx._process(1.0)
	await process_frame
	assert(get_nodes_in_group("ore_impact_fx").is_empty())
	world.queue_free()
	await process_frame
	print("ORE_IMPACT PASS: one effect, radial dust and ballistic chips, lifetime cleanup")
	quit()
