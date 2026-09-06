extends SceneTree
const OUT = "E:/3d/3-dfps/tools/ai-gen/foreman-attack-v09-20260906/rendered"
var camera: Camera3D
var world: Node3D
func _initialize() -> void:
	call_deferred("run")
func snap(path: String) -> void:
	await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(path)
func run() -> void:
	world=Node3D.new()
	root.add_child(world)
	current_scene=world
	var environment=Environment.new()
	environment.background_mode=Environment.BG_COLOR
	environment.background_color=Color(.22,.25,.29)
	environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color=Color(.72,.78,.85)
	environment.ambient_light_energy=.55
	environment.tonemap_mode=Environment.TONE_MAPPER_FILMIC
	environment.tonemap_exposure=.92
	environment.tonemap_white=6.0
	environment.ssao_enabled=true
	environment.ssao_radius=1.2
	var env_node=WorldEnvironment.new()
	env_node.environment=environment
	world.add_child(env_node)
	var ground=MeshInstance3D.new()
	var plane=PlaneMesh.new()
	plane.size=Vector2(50,50)
	var material=StandardMaterial3D.new()
	material.albedo_color=Color(.32,.35,.37)
	material.roughness=.9
	plane.material=material
	ground.mesh=plane
	world.add_child(ground)
	# Identical neutral inspection lights for both versions, not production lighting changes.
	var key=DirectionalLight3D.new()
	key.rotation_degrees=Vector3(-45,-30,0)
	key.light_energy=1.6
	key.shadow_enabled=true
	world.add_child(key)
	var fill=DirectionalLight3D.new()
	fill.rotation_degrees=Vector3(-20,135,0)
	fill.light_energy=.8
	world.add_child(fill)
	camera=Camera3D.new()
	world.add_child(camera)
	camera.projection=Camera3D.PROJECTION_ORTHOGONAL
	camera.current=true
	for version in ["v08","v09"]:
		var model=load("res://%s.glb" % version).instantiate()
		world.add_child(model)
		var player: AnimationPlayer=model.find_child("AnimationPlayer",true,false)
		assert(player!=null and player.has_animation("Attack"))
		player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		player.play("Attack")
		for view in ["body","side"]:
			var folder=OUT.path_join(version+"-"+view)
			DirAccess.make_dir_recursive_absolute(folder)
			if view=="body":
				root.size=Vector2i(960,720)
				camera.position=Vector3(-5,3.1,7)
				camera.look_at(Vector3(0,1.32,0))
				camera.size=3.7
			else:
				root.size=Vector2i(1280,720)
				camera.position=Vector3(-12,4.7,2)
				camera.look_at(Vector3(0,2.65,.5))
				camera.size=8.7
			for i in range(37):
				player.seek(minf(i/24.,1.5),true)
				await snap(folder.path_join("%03d.png" % i))
			player.seek(.59625,true)
			await snap(folder.path_join("contact.png"))
		model.queue_free()
		await process_frame
	print("FOREMAN_V09_RENDER_COMPLETE: both exported models, full Attack, body and whip side views, contact=.59625s")
	quit()
