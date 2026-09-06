extends SceneTree
const World := preload("res://scripts/voxel_lab/smooth_world.gd")
class HeightSource extends RefCounted:
	func get_height(p: Vector3) -> float:
		return 20.0+p.x*0.04+p.z*0.03
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	root.get_node("HUD").set_process(false)
	var source := HeightSource.new()
	var world := World.new()
	var origin := Vector3(100,26,200)
	assert(world.configure_from_terrain(source,origin,"slope-fixture")==OK)
	var expected := source.get_height(origin+Vector3(0.37,0,0.81))-origin.y
	assert(absf(world.natural_height(0.37,0.81)-expected)<0.00001)
	assert(world.position==origin)
	assert(world.generator_id().begins_with("terrain-snapshot-v1:"))
	var identity := world.generator_id()
	assert(world.configure_from_terrain(source,Vector3(0,100,0),"invalid")==ERR_INVALID_DATA)
	assert(world.generator_id()==identity)
	root.add_child(world)
	assert(world.configure_from_terrain(source,origin,"late")==ERR_INVALID_PARAMETER)
	await physics_frame
	await physics_frame
	var query := PhysicsRayQueryParameters3D.create(origin+Vector3(0.37,12,0.81),origin+Vector3(0.37,-4,0.81),1)
	var hit := world.get_world_3d().direct_space_state.intersect_ray(query)
	assert(not hit.is_empty())
	assert(absf(hit.position.y-source.get_height(hit.position))<0.001)
	print("TERRAIN_SOURCE_ACCEPTANCE PASS: local/world height conversion, fractional sampling, rejection atomicity, identity, translated mesh collision")
	world.queue_free()
	await process_frame
	quit()
