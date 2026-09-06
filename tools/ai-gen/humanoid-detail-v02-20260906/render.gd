extends SceneTree
const OUT="E:/3d/3-dfps/tools/ai-gen/humanoid-detail-v02-20260906/rendered"
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
	ground.position.y=-.01
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
	camera.size=2.5
	var versions=["modern-before","miner-before","runner-before"]
	for kind in ["modern","miner","runner"]:
		if ResourceLoader.exists("res://"+kind+"-after.glb"):versions.append(kind+"-after")
	for version in versions:
		var file="res://"+version+".glb"
		var folder=OUT.path_join(version)
		DirAccess.make_dir_recursive_absolute(folder)
		var model=load(file).instantiate()
		model.scale=Vector3.ONE
		world.add_child(model)
		var ap: AnimationPlayer=model.find_child("AnimationPlayer",true,false)
		ap.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		var idle="Idle"
		if version=="ual":idle="Death01"
		ap.play(idle)
		ap.seek(.5,true)
		for view in ["front","side","back"]:
			camera.position={"front":Vector3(2.5,1.6,4),"side":Vector3(4,1.45,.1),"back":Vector3(-2.5,1.6,-4)}[view]
			camera.look_at(Vector3(0,.87,0))
			await snap(folder.path_join(view+".png"))
		camera.size=.48
		camera.position=Vector3(.38,1.65,1.2)
		camera.look_at(Vector3(0,1.43,0))
		await snap(folder.path_join("head-close.png"))
		camera.size=.86
		camera.position=Vector3(.4,1.15,1.8)
		camera.look_at(Vector3(0,1.05,0))
		await snap(folder.path_join("torso-close.png"))
		camera.size=2.5
		camera.position=Vector3(2.5,1.6,4)
		camera.look_at(Vector3(0,.87,0))
		var clips=[]
		if version=="A":clips=["attack_left_70f","attack_right_70f","walk_64f","walk_limp_60f","slowWalk_85f","idle_220f","running_58f"]
		if version=="quaternius":clips=["Punch","Death","Walk"]
		if version.ends_with("-after") and not "--stills" in OS.get_cmdline_user_args():clips=["Idle","Walk","Attack","AttackRight","Death","HitReact"]
		if version=="ual":clips=["Death01","Death02","Hit_Chest"]
		for clip in clips:
			if not ap.has_animation(clip):continue
			var clip_folder=folder.path_join(clip)
			DirAccess.make_dir_recursive_absolute(clip_folder)
			ap.play(clip)
			var duration: float=ap.get_animation(clip).length
			for i in range(ceili(duration*24)+1):
				ap.seek(minf(i/24.,duration),true)
				await snap(clip_folder.path_join("%03d.png" % i))
		model.queue_free()
		await process_frame
	print("MODERN_ZOMBIE_RENDER_COMPLETE")
	quit()
