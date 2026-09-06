extends SceneTree
func _initialize() -> void:
	if DisplayServer.get_name()=="headless":
		printerr("Run with D3D12: the dummy renderer cannot read MultiMesh instance data.")
		quit(1)
		return
	call_deferred("run")
func run() -> void:
	var world := Node3D.new()
	root.add_child(world)
	current_scene = world
	var camera := Camera3D.new()
	world.add_child(camera)
	camera.make_current()
	var stars = preload("res://scripts/night_starfield.gd").new()
	world.add_child(stars)
	assert(stars.multimesh.instance_count==2400)
	assert(stars.galaxy_dome != null and stars.galaxy_dome.mesh is SphereMesh)
	assert(stars.galaxy_material.shader.resource_path.ends_with("galaxy_dome.gdshader"))
	assert((stars.galaxy_material.get_shader_parameter("galaxy_texture") as Texture2D).get_size()==Vector2(8192,4096))
	var low := 100.0
	var high := 0.0
	var bright_direction := Vector3.UP
	var phases: Dictionary = {}
	for i in 2400:
		var transform: Transform3D = stars.multimesh.get_instance_transform(i)
		assert(absf(transform.origin.length()-1.0)<0.001)
		assert(transform.origin.y>0.0)
		assert(transform.basis.determinant()!=0)
		var parameters: Color = stars.multimesh.get_instance_custom_data(i)
		phases[int(parameters.r*1000)] = true
		low = minf(low,parameters.a)
		high = maxf(high,parameters.a)
		if parameters.a>2.0 and transform.origin.y>0.3 and transform.origin.y<0.8:
			bright_direction = transform.origin
	assert(high>low*5)
	assert(phases.size()>500)
	stars.set_sky_state({"direction":Vector3.UP})
	assert(not stars.visible)
	stars.set_sky_state({"direction":Vector3.DOWN,"phase":0.25,"cloud_cover":0.8})
	assert(stars.visible)
	assert(is_equal_approx(stars.galaxy_material.get_shader_parameter("night_visibility"),1.0))
	assert(is_equal_approx(stars.galaxy_material.get_shader_parameter("sidereal_rotation"),0.33))
	assert(is_equal_approx(stars.galaxy_material.get_shader_parameter("cloud_cover"),0.8))
	await process_frame
	await process_frame
	var before: float = stars.elapsed
	paused = true
	await process_frame
	await process_frame
	assert(stars.elapsed==before)
	paused = false
	await process_frame
	await process_frame
	assert(stars.elapsed>before)
	# Pixel-level depth test: an opaque foreground object must occlude a star.
	var environment_node := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color.BLACK
	environment_node.environment = environment
	world.add_child(environment_node)
	camera.look_at(bright_direction)
	for layer in root.find_children("*","CanvasLayer",true,false): layer.hide()
	for i in 4: await process_frame
	await RenderingServer.frame_post_draw
	var screenshot := root.get_texture().get_image()
	var center := Vector2i(screenshot.get_width()/2,screenshot.get_height()/2)
	var before_pixel := screenshot.get_pixelv(center)
	assert(before_pixel.r+before_pixel.g+before_pixel.b>0.1)
	var blocker := MeshInstance3D.new()
	blocker.mesh = BoxMesh.new()
	var black := StandardMaterial3D.new()
	black.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	black.albedo_color = Color.BLACK
	blocker.material_override = black
	world.add_child(blocker)
	blocker.position = bright_direction*5
	for i in 4: await process_frame
	await RenderingServer.frame_post_draw
	var blocked := root.get_texture().get_image().get_pixelv(center)
	assert(blocked.r+blocked.g+blocked.b<0.03)
	print("PASS starfield: seeded twinkle plus 2:1 galaxy dome, day/weather/sidereal controls, pause/resume")
	print("PASS foreground opaque geometry occludes stars in rendered pixels")
	quit()
