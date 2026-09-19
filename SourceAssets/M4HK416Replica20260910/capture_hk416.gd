extends SceneTree
const OUT := "D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910/Reference"
const Gun := preload("res://scripts/gun.gd")
var samples := {}
var events := []
var active_clip := ""
var active_time := 0.0

func _initialize() -> void:
	run.call_deferred()

func matrix(t: Transform3D) -> Array:
	return [t.basis.x.x,t.basis.y.x,t.basis.z.x,t.origin.x,t.basis.x.y,t.basis.y.y,t.basis.z.y,t.origin.y,t.basis.x.z,t.basis.y.z,t.basis.z.z,t.origin.z,0,0,0,1]

func run() -> void:
	var world := Node3D.new()
	root.add_child(world)
	current_scene = world
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(.12,.16,.19)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color.WHITE
	env.environment.ambient_light_energy = .6
	world.add_child(env)
	var body := CharacterBody3D.new()
	world.add_child(body)
	var camera := Camera3D.new()
	camera.fov=75;camera.near=.01;camera.current=true
	body.add_child(camera)
	var light := DirectionalLight3D.new()
	light.rotation_degrees=Vector3(-35,-25,0);light.light_energy=1.1
	world.add_child(light)
	var gun := Gun.new()
	gun.data=load("res://weapon_data/hk416.tres")
	camera.add_child(gun)
	gun.set_process(false);gun.set_physics_process(false)
	for i in 120:
		gun._physics_process(1.0/60);gun._process(1.0/60)
		if i%30==0: await process_frame
	var vm:Node3D=gun._model
	vm.cancel_action()
	vm._reload_audio.cue_played.connect(func(cue,time): events.append({"clip":active_clip,"cue":str(cue),"source_time":time,"sample_time":active_time}))
	var rigs := vm.find_children("*","Skeleton3D",true,false)
	var report := {"rigs":{},"clips":{},"events":events,"gun_transform":matrix(gun.transform),"viewmodel_transform":matrix(vm.transform),"fps":60,"fov":75}
	for rig:Skeleton3D in rigs:
		var bones := []
		for b in rig.get_bone_count():
			bones.append({"name":rig.get_bone_name(b),"parent":rig.get_bone_parent(b),"rest":matrix(rig.get_bone_rest(b)),"model_rest":matrix(vm.global_transform.affine_inverse()*rig.global_transform*rig.get_bone_global_rest(b))})
		report.rigs[str(vm.get_path_to(rig))]={"bones":bones,"transform":matrix(vm.global_transform.affine_inverse()*rig.global_transform)}
	for clip in [&"idle",&"equip_charge",&"reload",&"reload_empty",&"fire"]:
		active_clip=str(clip);active_time=0
		vm.cancel_action()
		for i in 12: vm.advance_pose(0,1.0/60)
		var duration:float=vm.player.get_animation(clip).length if clip!=&"idle" else .3
		var data := {"duration":duration,"loop":vm.player.get_animation(clip).loop_mode,"frames":[]}
		if clip!=&"idle":vm.play_action(clip,duration)
		if clip==&"equip_charge":gun._equip_player.play()
		if clip==&"fire":gun._shoot_player.play()
		DirAccess.make_dir_recursive_absolute(OUT.path_join(str(clip)))
		for i in ceili(duration*60)+1:
			active_time=minf(i/60.0,duration)
			vm.advance_pose(0,0 if i==0 else 1.0/60)
			await process_frame
			await RenderingServer.frame_post_draw
			var frame := {"time":active_time,"rigs":{}}
			for rig:Skeleton3D in rigs:
				var pose := []
				for b in rig.get_bone_count():pose.append(matrix(vm.global_transform.affine_inverse()*rig.global_transform*rig.get_bone_global_pose(b)))
				frame.rigs[str(vm.get_path_to(rig))]=pose
			data.frames.append(frame)
			if i%3==0 or i==ceili(duration*60):root.get_texture().get_image().save_png(OUT.path_join(str(clip)).path_join("Frame_%04d.png"%i))
		report.clips[str(clip)]=data
		print("HK416_RUNTIME_CAPTURE ",clip," duration=",duration," samples=",data.frames.size())
		for i in 20:
			vm.advance_pose(0,1.0/60)
			await process_frame
	var file := FileAccess.open(OUT.path_join("runtime_poses.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report));file.close()
	print("HK416_REFERENCE_COMPLETE events=",JSON.stringify(events))
	quit()
