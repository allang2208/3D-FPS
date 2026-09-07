extends SceneTree

const Catalog := preload("res://scripts/building/build_piece_catalog.gd")
const Supports := preload("res://scripts/building/support_graph.gd")
const BuildSystem := preload("res://scripts/building/build_system.gd")
const PieceBody := preload("res://scripts/building/build_piece_body.gd")
const Door := preload("res://scripts/building/door_component.gd")
const RailingMaterial := preload("res://scripts/building/railing_material.gd")
const WoodMaterial := preload("res://scripts/building/generated_wood_material.gd")
const Save := preload("res://ui/inventory_save.gd")

var failures := 0

func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH","user://build-piece-foundation-%d.save" % OS.get_process_id())
	call_deferred("run")

func check(ok: bool, label: String) -> void:
	print("PASS " if ok else "FAIL ",label)
	if not ok: failures+=1

func run() -> void:
	var definitions:=Catalog.panel_definitions()
	check(definitions.size()==5,"catalog exposes five panel components")
	check(Catalog.definition("floor").stable_id==&"wood","legacy floor resolves to unified wood definition")
	check(Catalog.definition("door").footprint_cells==Vector3i(2,4,1),"door definition reserves a one metre by two metre volume")
	check(Catalog.definition("wood").max_health==100 and Catalog.definition("stone").max_health==250 and Catalog.definition("marble").max_health==300,"material blocks define distinct durability")
	var door_x:=Catalog.occupied_offsets("door",0)
	var door_z:=Catalog.occupied_offsets("door",1)
	check(door_x.has(Vector3i(1,3,0)) and door_z.has(Vector3i(0,3,-1)),"door occupancy follows visual quarter rotation")

	var structural:={Vector3i(0,0,0):"stone",Vector3i(1,0,0):"stone",Vector3i(0,1,0):"door"}
	var structural_rotations:={Vector3i(0,0,0):0,Vector3i(1,0,0):0,Vector3i(0,1,0):0}
	var supported:=Supports.supported(structural,{Vector3i(0,0,0):true,Vector3i(1,0,0):true},structural_rotations)
	check(supported.has(Vector3i(0,1,0)),"door is supported only when its full base rests on structure")
	var incomplete:={Vector3i(0,0,0):"stone",Vector3i(0,1,0):"door"}
	check(not Supports.supported(incomplete,{Vector3i(0,0,0):true},{Vector3i(0,1,0):0}).has(Vector3i(0,1,0)),"door rejects partial base support")
	var non_bearing:={Vector3i(3,0,0):"railing",Vector3i(3,1,0):"wood"}
	var non_bearing_result:=Supports.supported(non_bearing,{Vector3i(3,0,0):true},{})
	check(non_bearing_result.has(Vector3i(3,0,0)) and not non_bearing_result.has(Vector3i(3,1,0)),"railing cannot carry a structural block")

	var piece:=PieceBody.new()
	root.add_child(piece)
	piece.setup(Vector3i(7,0,7),160,120)
	var destroyed:=[false]
	piece.destroyed.connect(func(_cell: Vector3i): destroyed[0]=true)
	check(piece.health_text()=="120/160","piece restores saved health")
	check(not piece.take_damage(20) and piece.current_health()==100,"piece receives projectile-compatible damage")
	check(piece.take_damage(100) and destroyed[0],"piece emits destruction when health reaches zero")
	piece.queue_free()

	var door_body:=PieceBody.new()
	root.add_child(door_body)
	door_body.setup(Vector3i(9,0,9),160,160)
	var frame:=RailingMaterial.create_body()
	var wood:=WoodMaterial.create(false)
	var accent:=RailingMaterial.create_accent()
	var controller=Door.add_geometry(door_body,frame,wood,accent,false)
	var saved_state:=[{}]
	door_body.bind_state_source(controller)
	door_body.state_changed.connect(func(_cell: Vector3i, state: Dictionary): saved_state[0]=state)
	controller.set_open(true,false)
	check(controller.is_open() and saved_state[0].get("open",false),"door open state reaches persistence owner")
	check(door_body.find_child("DoorLeafCollision",true,false)!=null and door_body.find_child("DoorController",true,false)!=null,"door includes authored collision and interaction controller")
	door_body.queue_free()
	var build:=BuildSystem.new()
	build.cells={Vector3i(2,0,2):"door"}
	build.rotations={Vector3i(2,0,2):1}
	build.health={Vector3i(2,0,2):117}
	build.states={Vector3i(2,0,2):{"open":true}}
	check(build.persist().is_empty(),"extended building sidecar writes")
	var row: Array=Save.read_snapshot(build.save_path()).get("blocks",[])[0]
	check(row.size()==7 and row[3]=="door" and row[4]==1 and row[5]==117 and row[6].get("open",false),"sidecar stores door orientation, health and state")
	build.free()

	print("BUILD_PIECE_FOUNDATION failures=",failures)
	quit(failures)
