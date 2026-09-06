extends SceneTree
const Audio := preload("res://scripts/m16_action_audio.gd")
const Equip := preload("res://scripts/m16_equip_animation.gd")
const Barrels := preload("res://scripts/barrel_variants.gd")
class Sampler extends Node3D:
	func _sample_transform_track(clip: Animation, track: int, _kind: int, time: float) -> Vector3:
		return clip.position_track_interpolate(track, time)
class LaserGun extends Node3D:
	var inventory_active := true
	var _ads := false
	func hipfire_radius_pixels() -> float: return 0.0
	func _camera() -> Camera3D: return get_parent() as Camera3D
	func aim_screen_position(_cam: Camera3D) -> Vector2:
		return get_viewport().get_visible_rect().size*.5 + Vector2(17,-9)
var failures := 0
var events: Array = []
func _initialize() -> void: call_deferred("run")
func check(ok: bool, label: String) -> void:
	if not ok:
		failures += 1
		push_error(label)
func run() -> void:
	var sound := Audio.new()
	root.add_child(sound)
	sound.cue_played.connect(func(cue: StringName, time: float): events.append([cue,time]))
	for fps in [30,60,144]:
		for clip: StringName in Audio.CUES:
			for speed in [.8,1.0,1.2]:
				events.clear()
				sound.begin(clip,2.4,2.4/speed)
				for f in ceili(3.5*fps): sound.advance(1.0/fps)
				check(events.size()==Audio.CUES[clip].size(),"cue count")
				for i in mini(events.size(),Audio.CUES[clip].size()):
					check(events[i][0]==Audio.CUES[clip][i][1],"cue order")
					check(absf(events[i][1]-Audio.CUES[clip][i][0])<=speed/fps+.00001,"cue within one frame")
	sound.begin(&"reload_empty",2.4,2.4)
	sound.advance(.7)
	sound.stop()
	events.clear()
	sound.advance(4.0)
	check(events.is_empty(),"cancel removes pending audio")
	for voice: AudioStreamPlayer in sound._players.values(): check(not voice.playing,"cancel stops tails")
	sound.queue_free()
	var source := Animation.new()
	source.length=2.333333
	var track:=source.add_track(Animation.TYPE_POSITION_3D)
	source.track_set_path(track,"Rig:Handle")
	for key in [[0.0,Vector3.ZERO],[1.4,Vector3.ZERO],[1.7,Vector3(0,0,.08)],[1.96,Vector3.ZERO],[2.333333,Vector3.ZERO]]:
		source.track_insert_key(track,key[0],key[1])
	var idle:=Animation.new()
	idle.add_track(Animation.TYPE_POSITION_3D)
	idle.track_set_path(0,"Rig:Handle")
	idle.track_insert_key(0,0,Vector3.ZERO)
	var sampler:=Sampler.new()
	var equip:=Equip.build(sampler,source,idle)
	check(absf(equip.length-1.313333)<.00001 and equip.loop_mode==Animation.LOOP_NONE,"equip duration and nonloop")
	check(equip.position_track_interpolate(0,.52).z>.075,"keeps mechanical motion")
	check(equip.position_track_interpolate(0,0).length()<.00001 and equip.position_track_interpolate(0,equip.length).length()<.00001,"returns to held pose")
	sampler.free()
	check(Barrels.normalize("short")=="short" and Barrels.normalize(true)==true,"barrel migration")
	check(Barrels.ads_delta("short")==-.2 and Barrels.spread_multiplier("long")==1.5 and Barrels.range_multiplier("long")==1.25,"barrel modifiers")
	var world:=Node3D.new()
	root.add_child(world)
	var cam:=Camera3D.new()
	world.add_child(cam)
	var gun:=LaserGun.new()
	cam.add_child(gun)
	var device:=Node3D.new()
	device.set_script(preload("res://scripts/tactical_device.gd"))
	device.kind="laser"
	device.position=Vector3(.18,-.12,-.3)
	device.rotation.y=.05
	var emitter:=Node3D.new()
	emitter.name="Emitter"
	device.add_child(emitter)
	gun.add_child(device)
	device.set_process(false)
	var wall:=StaticBody3D.new()
	wall.position.z=-10
	world.add_child(wall)
	var collider:=CollisionShape3D.new()
	var box:=BoxShape3D.new()
	box.size=Vector3(100,100,.2)
	collider.shape=box
	wall.add_child(collider)
	await physics_frame
	for ads in [false,true,false]:
		gun._ads=ads
		device._process(0.0)
		var start:Vector3=device._beam.global_transform*Vector3(0,.5,0)
		var end:Vector3=device._beam.global_transform*Vector3(0,-.5,0)
		check(start.distance_to(emitter.global_position)<.0001,"laser emitter anchor")
		check(device._dot.visible,"wall dot")
		if ads:
			check(cam.unproject_position(end).distance_to(gun.aim_screen_position(cam))<.1,"ADS visible reticle")
		else:
			check((end-start).normalized().distance_to(-emitter.global_basis.z)<.00001,"hip axis retained")
	world.queue_free()
	await process_frame
	print("PUBLISHED_WEAPON_MODULES failures=",failures)
	quit(1 if failures else 0)
