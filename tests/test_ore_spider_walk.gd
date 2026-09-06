extends SceneTree
func _initialize() -> void: call_deferred("run_test")
func run_test() -> void:
	var enemy: Node3D = load("res://scenes/enemies/ore_spider.tscn").instantiate()
	root.add_child(enemy)
	enemy.set_physics_process(false)
	var model: Node3D = enemy.get_node("Model")
	var ap := model.find_child("AnimationPlayer",true,false) as AnimationPlayer
	var skeleton := model.find_children("*","Skeleton3D",true,false)[0] as Skeleton3D
	ap.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	var clip: StringName
	for key in ap.get_animation_list():
		if key.get_file() == "Walk": clip=key
	assert(not clip.is_empty())
	ap.play(clip)
	var first: Array[Transform3D]=[]
	var previous: Array[Vector3]=[]
	var phases: Array[float]=[]
	var max_slip := 0.0
	for frame in 43:
		var t := frame / 30.0
		ap.seek(t,true)
		await process_frame
		if frame==0:
			for i in skeleton.get_bone_count():first.append(skeleton.get_bone_global_pose(i))
		for i in 12:
			var bone := skeleton.find_bone("leg%02d_foot"%i)
			assert(bone>=0)
			var point := skeleton.to_global(skeleton.get_bone_global_pose(bone).origin) + Vector3(0,0,1.05*t)
			var phase := fmod(t/.7+(i%3)/3.0+(i/3)*.014,1.0)
			if frame==0:previous.append(point);phases.append(phase)
			else:
				if phase<.72 and phases[i]<.72 and phase>phases[i]:
					var drift := point.distance_to(previous[i])
					if drift>max_slip:
						max_slip=drift
				previous[i]=point;phases[i]=phase
	var seam := 0.0
	for i in skeleton.get_bone_count():
		var last := skeleton.get_bone_global_pose(i)
		seam=maxf(seam,first[i].origin.distance_to(last.origin))
	assert(seam<.001,str(seam))
	assert(max_slip<.006,str(max_slip))
	print("ORE_WALK_VALIDATION PASS: 12 foot chains; loop seam=",seam,"m; planted drift per 1/30s=",max_slip,"m")
	enemy.queue_free()
	await process_frame
	quit()
