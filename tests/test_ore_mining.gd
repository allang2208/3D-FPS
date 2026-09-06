extends SceneTree
class Host:
	extends Node3D
	var world: Node3D
	var status: Label
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	var host:=Host.new()
	root.add_child(host)
	host.world=load("res://scripts/voxel_lab/voxel_world.gd").new()
	host.add_child(host.world)
	host.status=Label.new()
	host.add_child(host.status)
	var kit: Node=load("res://scripts/tools/basic_toolkit.gd").new()
	host.add_child(kit)
	kit.editor=host
	kit.set_process(false)
	var cell:=Vector3i(-15,1,12)
	host.world.change_cell(cell,3)
	var before: int=host.world.stock[3]
	assert(not kit.mine_cell(cell))
	kit.equip("axe")
	assert(not kit.mine_cell(cell))
	kit.equip("pickaxe")
	assert(not kit.mine_cell(cell) and not kit.mine_cell(cell))
	assert(host.world.get_cell(cell)==3 and host.world.stock[3]==before)
	assert(kit.mine_cell(cell))
	assert(host.world.get_cell(cell)==0 and host.world.stock[3]==before+1)
	assert(not kit.mine_cell(cell) and host.world.stock[3]==before+1)
	var burst: Node=host.get_child(host.get_child_count()-1)
	assert(burst.pieces.size()==14)
	var saved: String="user://ore-mining-test-"+str(OS.get_process_id())+".json"
	assert(host.world.save_world(saved)==OK)
	assert(host.world.load_world(saved)==OK and host.world.get_cell(cell)==0 and host.world.stock[3]==before+1)
	for body in burst.pieces:
		assert(body.collision_layer==0 and body.collision_mask==1)
		assert(body.linear_velocity.length()>0)
	var mesh: ArrayMesh=load("res://scripts/tools/ore_break_fx.gd").shard_mesh(1,0.2,true)
	var arrays:=mesh.surface_get_arrays(0)
	assert(arrays[Mesh.ARRAY_NORMAL][0].dot(arrays[Mesh.ARRAY_VERTEX][0])>0)
	print("ORE_MINING PASS: correct tool, three contacts, one reward, real voxel removed, 14 debris bodies, outward normals, save restore")
	host.free()
	quit()
