extends SceneTree

# Player-spawn view: what the player sees when entering the scene.

var _scene: Node
var _frames := 0
var _cam: Camera3D


func _initialize() -> void:
	_scene = load("res://scenes/demo_terrain.tscn").instantiate()
	root.add_child(_scene)


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 25:
		var terrain := _scene.get_node_or_null("Terrain3D") as Terrain3D
		var spawn := Vector3(0, 0, 40)
		var h := terrain.data.get_height(spawn)
		var player := _scene.get_node_or_null("Player") as Node3D
		var cam := player.get_node_or_null("Camera3D") as Camera3D
		cam.global_position = Vector3(0, h + 2.0 + 1.62, 40)
		cam.look_at(Vector3(0, h - 8.0, -30), Vector3.UP)
		cam.current = true
	if _frames < 45:
		return false
	var img := root.get_viewport().get_texture().get_image()
	if img == null or img.get_width() == 0:
		print("VIEWPORT EMPTY")
		quit(1)
		return false
	img.save_png("user://spawn_view.png")
	print("SAVED ", ProjectSettings.globalize_path("user://spawn_view.png"))
	quit(0)
	return false
