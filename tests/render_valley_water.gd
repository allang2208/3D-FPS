extends SceneTree
## Fixed close-up for validating the actual valley water over white pebbles.

var scene: Node3D
var camera: Camera3D
var frames := 0

func _initialize() -> void:
	scene = load("res://scenes/scenic_valley.tscn").instantiate()
	root.add_child(scene)
	current_scene = scene

func _process(_delta: float) -> bool:
	frames += 1
	if frames == 20:
		var player := scene.get_node("Player")
		player.set_physics_process(false)
		player.set_process_unhandled_input(false)
		player.hide()
		for layer in root.find_children("", "CanvasLayer", true, false):
			layer.hide()
		camera = Camera3D.new()
		camera.fov = 64.0
		camera.far = 900.0
		root.add_child(camera)
	if frames == 25:
		var x := -190.0
		var center: float = scene._river_center_z(x)
		camera.global_position = Vector3(x + 11.0, scene.water_height(x) + 2.4, center + 9.0)
		var target_x := x - 34.0
		camera.look_at(Vector3(target_x, scene.water_height(target_x) + 0.08, scene._river_center_z(target_x)))
		camera.make_current()
	if frames == 80:
		await RenderingServer.frame_post_draw
		var path := "res://docs/preview/valley_water_enhanced_v5.png"
		var result := root.get_texture().get_image().save_png(path)
		print("[water-capture] ", path, " error=", result)
		quit(0 if result == OK else 1)
	return false
