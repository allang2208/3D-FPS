extends SceneTree

const BuildSystem := preload("res://scripts/building/build_system.gd")
const Grid := preload("res://scripts/building/block_grid.gd")
const Railing := preload("res://scripts/building/railing_component.gd")
const RailingMaterial := preload("res://scripts/building/railing_material.gd")
const Save := preload("res://ui/inventory_save.gd")

var failures := 0

func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH","user://railing-component-test-%d.save" % OS.get_process_id())
	call_deferred("run")

func check(ok: bool, label: String) -> void:
	print("PASS " if ok else "FAIL ",label)
	if not ok: failures+=1

func run() -> void:
	var build=BuildSystem.new()
	build._ensure_input_actions()
	check(InputMap.has_action("build_toggle_snap") and InputMap.has_action("build_rotate_previous") and InputMap.has_action("build_rotate_next") and InputMap.has_action("build_undo") and InputMap.has_action("build_redo"),"build snap, rotation and history actions register")
	var undo_chord:=InputEventKey.new()
	undo_chord.keycode=KEY_Z
	undo_chord.ctrl_pressed=true
	undo_chord.pressed=true
	check(undo_chord.is_action_pressed("build_undo"),"Ctrl+Z chord matches undo action")
	build.kind="railing"
	build.rotation_quarters=3
	build.snap_enabled=false
	check(build.resolved_rotation(Vector3i.ZERO)==3,"manual orientation remains selected")
	build.snap_enabled=true
	build.cells[Vector3i.ZERO]="railing"
	build.rotations[Vector3i.ZERO]=0
	check(build.resolved_rotation(Vector3i.RIGHT,"railing")==0,"side neighbor resolves to X axis")
	build.rotations[Vector3i.ZERO]=1
	check(build.resolved_rotation(Vector3i.BACK,"railing")==1,"forward/back neighbor resolves to Z axis")
	check(build.resolved_rotation(Vector3i.RIGHT,"railing")==0,"adjacent railing snaps into a branch-capable graph")
	var body:=RailingMaterial.create_body()
	var accent:=RailingMaterial.create_accent()
	var block:=Railing.make_block(Vector3i(2,0,3),1,body,accent,Grid)
	check(block.get_meta("impact_surface")=="metal" and is_equal_approx(block.rotation.y,PI*.5),"railing factory applies metal surface and orientation")
	check(block.get_meta("railing_topology")=="isolated" and block.get_node("RailingVisual").get_child_count()==15,"isolated railing authors two arms and two end posts")
	check(Railing.topology_kind([Vector3i.LEFT])=="end","one neighbor resolves an end segment")
	check(Railing.topology_kind([Vector3i.LEFT,Vector3i.FORWARD])=="corner","two perpendicular neighbors resolve a corner")
	check(Railing.topology_kind([Vector3i.LEFT,Vector3i.RIGHT])=="straight","two opposite neighbors resolve a straight segment")
	check(Railing.topology_kind([Vector3i.LEFT,Vector3i.RIGHT,Vector3i.FORWARD])=="t","three neighbors resolve a T junction")
	check(Railing.topology_kind([Vector3i.LEFT,Vector3i.RIGHT,Vector3i.FORWARD,Vector3i.BACK])=="cross","four neighbors resolve a cross junction")
	block.rotation.y=0
	Railing.rebuild_geometry(block,body,accent,[Vector3i.LEFT,Vector3i.FORWARD])
	check(block.get_meta("railing_topology")=="corner" and block.get_node("RailingVisual").get_node_or_null("HandrailNX")!=null and block.get_node("RailingVisual").get_node_or_null("HandrailNZ")!=null,"corner rebuild updates visible arms and collision")
	build.cells={Vector3i.ZERO:"railing",Vector3i.LEFT:"railing",Vector3i.RIGHT:"railing",Vector3i.FORWARD:"railing"}
	build.nodes={Vector3i.ZERO:block}
	build.materials={"railing":body}
	build._rail_accent=accent
	build.refresh_edges()
	check(block.get_meta("railing_topology")=="t","building neighbor refresh authors a T junction")
	build.cells={Vector3i(2,0,3):"railing"}
	build.nodes={}
	build.rotations={Vector3i(2,0,3):1}
	check(build.persist().is_empty(),"railing sidecar snapshot writes")
	var data:=Save.read_snapshot(build.save_path())
	check(data.get("version")==1 and data.get("blocks",[])[0].size()==7 and int(data.get("blocks",[])[0][4])==1,"snapshot stores orientation, health and component state")
	block.free()
	build.free()
	print("RAILING_COMPONENT failures=",failures)
	quit(failures)
