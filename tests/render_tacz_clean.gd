extends SceneTree
var _f := 0
func _process(_d) -> bool:
	_f += 1
	if _f == 1:
		var env := Environment.new()
		env.background_mode = Environment.BG_COLOR
		env.background_color = Color(0.5, 0.5, 0.55)
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(1, 1, 1)
		env.ambient_light_energy = 2.5
		var we := WorldEnvironment.new(); we.environment = env; root.add_child(we)
		var l1 := DirectionalLight3D.new(); l1.rotation_degrees = Vector3(-30, 140, 0); l1.light_energy = 2.5; root.add_child(l1)
		var l2 := DirectionalLight3D.new(); l2.rotation_degrees = Vector3(15, -45, 0); l2.light_energy = 1.2; l2.light_color = Color(0.8,0.85,1); root.add_child(l2)
		var cam := Camera3D.new(); cam.fov = 32.0; root.add_child(cam); cam.make_current()
		var body: PackedScene = load("res://assets/models/tacz_ak47/ak47_v2.glb")
		var b := body.instantiate()
		root.add_child(b)
		cam.position = Vector3(1.15, 0.06, 0.0)
		cam.look_at(Vector3(0.0, 0.0, 0.0), Vector3.UP)
	if _f == 8:
		var img := root.get_viewport().get_texture().get_image()
		img.save_png("user://tacz_clean_side.png")
		print("SAVED ", ProjectSettings.globalize_path("user://tacz_clean_side.png"))
		quit(0)
		return false
	return false
