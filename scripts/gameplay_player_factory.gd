class_name GameplayPlayerFactory
extends RefCounted

## Single construction path for every playable 3D map. Scenes choose only the
## spawn point; movement, camera, audio listener and weapon runtime stay shared.
const PLAYER_SCRIPT := preload("res://scripts/player.gd")
const CAMERA_FX_SCRIPT := preload("res://scripts/camera_fx.gd")
const GUN_SCRIPT := preload("res://scripts/gun.gd")


static func create(spawn: Vector3) -> Dictionary:
	var player := CharacterBody3D.new()
	player.name = "Player"
	player.position = spawn
	player.set_script(PLAYER_SCRIPT)

	var collision := CollisionShape3D.new()
	collision.name = "Collision"
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.35
	capsule.height = 1.7
	collision.shape = capsule
	player.add_child(collision)

	var camera := Camera3D.new()
	camera.name = "Camera3D"
	camera.position = Vector3(0, 1.62, 0)
	camera.fov = 75.0
	camera.current = true
	player.add_child(camera)

	var listener := AudioListener3D.new()
	listener.name = "AudioListener3D"
	camera.add_child(listener)

	var camera_fx := Node3D.new()
	camera_fx.name = "CameraFx"
	camera_fx.set_script(CAMERA_FX_SCRIPT)
	camera.add_child(camera_fx)

	var gun := Node3D.new()
	gun.name = "Gun"
	gun.position = Vector3(0.28, -0.26, -0.5)
	gun.set_script(GUN_SCRIPT)
	camera.add_child(gun)

	return {"player": player, "camera": camera, "gun": gun}
