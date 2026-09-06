extends SceneTree
const OUT="E:/3d/3-dfps/tools/ai-gen/zombie-dog-v01-20260906/rendered"
func _initialize() -> void:
	call_deferred("render_all")
func snap(path: String) -> void:
	await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(path)
func render_all() -> void:
	var world=Node3D.new()
	root.add_child(world)
	current_scene=world
	var env=Environment.new()
	env.background_mode=Environment.BG_COLOR
	env.background_color=Color(.10,.12,.145)
	env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color=Color(.70,.78,.88)
	env.ambient_light_energy=.48
	env.tonemap_mode=Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure=1.0
	env.ssao_enabled=true
	env.ssao_radius=.45
	var we=WorldEnvironment.new()
	we.environment=env
	world.add_child(we)
	var ground=MeshInstance3D.new()
	var plane=PlaneMesh.new()
	plane.size=Vector2(30,30)
	var mat=StandardMaterial3D.new()
	mat.albedo_color=Color(.16,.185,.20)
	mat.roughness=.93
	plane.material=mat
	ground.mesh=plane
	ground.position.y=-.005
	world.add_child(ground)
	var key=DirectionalLight3D.new()
	key.rotation_degrees=Vector3(-38,-30,0)
	key.light_color=Color(1,.92,.83)
	key.light_energy=1.5
	key.shadow_enabled=true
	world.add_child(key)
	var fill=DirectionalLight3D.new()
	fill.rotation_degrees=Vector3(-25,125,0)
	fill.light_energy=.7
	fill.light_color=Color(.69,.80,1)
	world.add_child(fill)
	var camera=Camera3D.new()
	world.add_child(camera)
	camera.current=true
	camera.projection=Camera3D.PROJECTION_ORTHOGONAL
	camera.size=1.4
	for version in ["source","zombie"]:
		var file="res://source.gltf" if version=="source" else "res://zombie.glb"
		if not ResourceLoader.exists(file):continue
		var folder=OUT.path_join(version)
		DirAccess.make_dir_recursive_absolute(folder)
		var model=load(file).instantiate()
		model.scale=Vector3.ONE*.3
		world.add_child(model)
		var ap: AnimationPlayer=model.find_child("AnimationPlayer",true,false)
		ap.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		ap.play("Idle")
		ap.seek(.5,true)
		for view in ["left","right","front","side"]:
			camera.position={"left":Vector3(3,1.40,2.5),"right":Vector3(-3,1.40,2.5),"front":Vector3(0,1.15,4),"side":Vector3(4,1.25,.1)}[view]
			camera.look_at(Vector3(0,.43,-.03))
			await snap(folder.path_join(view+".png"))
		if version=="zombie":
			camera.size=.65
			camera.position=Vector3(2,.70,.06)
			camera.look_at(Vector3(.13,.50,-.012))
			await snap(folder.path_join("wound-detail.png"))
			camera.position=Vector3(1.7,.90,2.6)
			camera.look_at(Vector3(0,.66,.63))
			await snap(folder.path_join("head-detail.png"))
			camera.size=1.4
		camera.position=Vector3(3,1.35,2.3)
		camera.look_at(Vector3(0,.44,-.03))
		for clip in ["Idle","Gallop","Attack","Death"]:
			var clip_folder=folder.path_join(clip)
			DirAccess.make_dir_recursive_absolute(clip_folder)
			ap.play(clip)
			var duration: float=ap.get_animation(clip).length
			var count=ceili(duration*24)
			for i in range(count+1):
				ap.seek(minf(i/24.,duration),true)
				await snap(clip_folder.path_join("%03d.png" % i))
		model.queue_free()
		await process_frame
	print("ZOMBIE_DOG_RENDER_COMPLETE: existing clips, default D3D12 Forward+, fixed review lights")
	quit()
