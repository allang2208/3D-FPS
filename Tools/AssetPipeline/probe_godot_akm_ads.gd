extends SceneTree

const Gun := preload("res://scripts/gun.gd")

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var body := CharacterBody3D.new()
	root.add_child(body)
	var camera := Camera3D.new()
	body.add_child(camera)
	var gun := Gun.new()
	gun.data = preload("res://weapon_data/akm_classic.tres")
	camera.add_child(gun)
	gun.set_process(false)
	gun.set_physics_process(false)
	await process_frame
	print("AKM_ADS_PROBE rear=", gun._sight_rear)
	print("AKM_ADS_PROBE front=", gun._sight_front)
	print("AKM_ADS_PROBE rear_dist=", gun._rear_dist)
	print("AKM_ADS_PROBE ads_pos=", gun._ads_pos)
	print("AKM_ADS_PROBE ads_rot=", gun._ads_rot)
	print("AKM_ADS_PROBE muzzle=", gun._muzzle_local)
	print("AKM_ADS_PROBE eject=", gun._eject_local)
	body.queue_free()
	await process_frame
	quit(0)
