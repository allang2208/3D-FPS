extends SceneTree

const BuildSystem:=preload("res://scripts/building/build_system.gd")

var failures:=0

class GunStub:
	extends Node
	var building_input_blocked:=false

class BuildHost:
	extends Node3D
	var _gun: Node
	var _status_bar: Node

func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH","user://build-history-%d.save" % OS.get_process_id())
	call_deferred("run")

func settle(count := 3) -> void:
	for _i in range(count): await physics_frame

func check(ok: bool, label: String) -> void:
	print("PASS " if ok else "FAIL ",label)
	if not ok: failures+=1

func run() -> void:
	var hud:=root.get_node("HUD")
	hud._ensure_built()
	hud.backpack.add_item("wood",20)
	var initial_wood: int=hud.backpack.count_item("wood")
	var host:=BuildHost.new()
	host._gun=GunStub.new()
	host.add_child(host._gun)
	root.add_child(host)
	var foundation:=StaticBody3D.new()
	foundation.set_meta("build_foundation",true)
	var foundation_shape:=BoxShape3D.new()
	foundation_shape.size=Vector3(12,.1,12)
	var foundation_collision:=CollisionShape3D.new()
	foundation_collision.shape=foundation_shape
	foundation.add_child(foundation_collision)
	foundation.position.y=-.05
	host.add_child(foundation)
	var build=BuildSystem.new()
	host.add_child(build)
	await settle(5)
	var cell:=Vector3i(0,0,0)
	check(build.place(cell,"wood").is_empty(),"placement transaction succeeds")
	check(hud.backpack.count_item("wood")==initial_wood-1 and build._undo_stack.size()==1,"placement charges once and records history")
	check(build.undo_last()=="已撤销上一步" and not build.cells.has(cell),"Ctrl-Z operation removes last placement")
	check(hud.backpack.count_item("wood")==initial_wood and build._redo_stack.size()==1,"undo placement refunds material")
	check(build.redo_last()=="已重做上一步" and build.cells.has(cell),"Ctrl-Y operation restores placement")
	check(hud.backpack.count_item("wood")==initial_wood-1,"redo placement charges material again")
	check(build.remove_block(cell).is_empty() and hud.backpack.count_item("wood")==initial_wood,"manual removal refunds material")
	check(build.undo_last()=="已撤销上一步" and build.cells.has(cell) and hud.backpack.count_item("wood")==initial_wood-1,"undo removal restores piece and takes refund back")
	check(build.redo_last()=="已重做上一步" and not build.cells.has(cell) and hud.backpack.count_item("wood")==initial_wood,"redo removal removes and refunds again")

	var door_cell:=Vector3i(2,0,0)
	check(build.place(door_cell,"door",0).is_empty(),"door placement enters history")
	build.health[door_cell]=117
	build.states[door_cell]={"open":true}
	check(build.undo_last()=="已撤销上一步" and not build.cells.has(door_cell),"undo captures current interactive piece state")
	check(build.redo_last()=="已重做上一步" and build.health.get(door_cell)==117 and build.states.get(door_cell,{}).get("open",false),"redo restores health and door state")
	check(build.undo_last()=="已撤销上一步","door can be undone again")
	check(build.place(Vector3i(4,0,0),"wood").is_empty() and build._redo_stack.is_empty(),"new action clears redo chain")

	print("BUILD_HISTORY failures=",failures)
	quit(failures)
