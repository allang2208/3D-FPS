extends Node3D
## 只驱动视模动画；弹药、命中与换弹完成仍由 Gun 结算。
@export var model_resource: PackedScene = preload("res://assets/models/infima/infima_ar.glb")
@export var use_charge_equip := true
## Mechanical motion must not drive the whole arm rig's ADS alignment.
@export var ads_mechanical_bone: StringName = &""
@export var stable_ads_grip := false
@export var fitted_hands_enabled := true
## Measured in the owning bone's local units, not the mesh AABB or sight line.
@export var calibrated_muzzle_bone: StringName = &""
@export var calibrated_muzzle_position := Vector3.ZERO
@export var calibrated_muzzle_forward := Vector3(0, -1, 0)
var skeleton: Skeleton3D
var player: AnimationPlayer
var tree: AnimationTree
var action_node: AnimationNodeAnimation
var shot_node: AnimationNodeOneShot
var _held_hand_pose = preload("res://scripts/held_hand_pose.gd").new()
var _drum_hand = preload("res://scripts/large_drum_hand_pose.gd").new()
var _drum_clock := -1.0
var _drum_source_length := 0.0
var _drum_speed := 1.0
var gunsmith_parts := {}
var _mounted_parts := {}
var _reload_audio: Node

func uses_reload_audio() -> bool:
	return is_instance_valid(_reload_audio)

func stop_action_audio() -> void:
	if is_instance_valid(_reload_audio): _reload_audio.stop()

func apply_gunsmith_parts(selection: Dictionary) -> void:
	var adapter = _attachment_adapter()
	var next := selection.duplicate(true) if adapter != null else {}
	if str(next.get("foregrip", false)) in preload("res://scripts/barrel_variants.gd").IDS or model_resource.resource_path.ends_with("/qbz191.glb"):
		next.erase("foregrip") # Numeric barrel variants retain the factory geometry.
	if gunsmith_parts == next:
		return
	_held_hand_pose.restore(_foregrip_rig.rig)
	_drum_hand.restore(_foregrip_rig.rig if _foregrip_rig.rig!=null else skeleton)
	_foregrip_pose.restore(_foregrip_rig.rig if _foregrip_rig.rig!=null else skeleton)
	for part in _mounted_parts.values():
		var holder: Node = part.get_parent()
		holder.get_parent().remove_child(holder)
		holder.queue_free()
	_mounted_parts.clear()
	# Magazine was cut after the stock. Restore in reverse order so a combined
	# stock + drum draft cannot retain a cut receiver after both are removed.
	preload("res://scripts/large_drum_ammo_mesh.gd").restore(self)
	if model_resource.resource_path.contains("qbz191"):
		preload("res://scripts/remaining_drum_mounts.gd").restore(self)
	preload("res://scripts/stock_variants.gd").restore(self)
	preload("res://scripts/hollow_grip_mesh.gd").restore(self)
	if adapter != null and adapter.has_method("restore"):
		adapter.restore(self)
	for original in ["SM_AR_01_Scope_Default", "SM_AR_01_Magazine_Default"]:
		var mesh := find_child(original, true, false)
		if mesh != null:
			mesh.show()
	gunsmith_parts = next.duplicate(true)
	if not next.is_empty():
		_mounted_parts = adapter.mount(self, next)
		if str(next.get("magazine",false)) == "large_drum" and _mounted_parts.has("magazine") and not _mounted_parts.magazine.has_meta("large_drum"):
			var weapon := "m16" if model_resource.resource_path.contains("m16") else "hk416" if model_resource.resource_path.contains("hk416") else "infima_ar"
			preload("res://scripts/large_drum_mount.gd").replace(_mounted_parts.magazine,weapon)
		preload("res://scripts/attachment_material_match.gd").apply(self,_mounted_parts)
		if str(next.get("magazine",false)) == "large_drum":
			preload("res://scripts/large_drum_ammo_mesh.gd").apply(self)
	preload("res://scripts/foregrip_hand_mesh.gd").set_enabled(self,_mounted_parts.has("underbarrel"))
	preload("res://scripts/rifle_polymer_finish.gd").apply(self,_mounted_parts)

func _attachment_adapter():
	if model_resource.resource_path.ends_with("/infima_handgun.glb"):
		return preload("res://scripts/p9_attachment_mounts.gd")
	return preload("res://scripts/akm_attachment_mounts.gd") if model_resource.resource_path.ends_with("/infima_ar.glb") else null

func _part_point(slot: String, marker: String) -> Vector3:
	var part: Node3D = _mounted_parts[slot]
	var holder: BoneAttachment3D = part.get_parent()
	var rig: Skeleton3D = holder.get_parent()
	return rig.global_transform * rig.get_bone_global_pose(holder.bone_idx) * part.transform * part.get_node(marker).position

func _ready() -> void:
	var model := model_resource.instantiate()
	add_child(model)
	_tune_materials(model)
	if fitted_hands_enabled:
		preload("res://scripts/fitted_player_hands.gd").apply(self,model_resource.resource_path)
	player = model.find_child("AnimationPlayer", true, false)
	skeleton = model.find_child("Skeleton3D", true, false)
	_build_equip_clip()
	if stable_ads_grip:
		_build_stable_ads_fire()
	if model_resource.resource_path.contains("infima_ar") or model_resource.resource_path.contains("hk416") or model_resource.resource_path.contains("m16") or model_resource.resource_path.contains("akm_") or model_resource.resource_path.contains("qbz191"):
		for clip in [&"reload",&"reload_empty"]:
			preload("res://scripts/large_drum_reload.gd").ensure(self,clip)
	var graph := AnimationNodeBlendTree.new()
	var idle := AnimationNodeAnimation.new()
	idle.animation = &"idle"
	var aim := AnimationNodeAnimation.new()
	aim.animation = &"aim"
	graph.add_node(&"idle", idle)
	graph.add_node(&"aim", aim)
	graph.add_node(&"ads", AnimationNodeBlend2.new())
	graph.connect_node(&"ads", 0, &"idle")
	graph.connect_node(&"ads", 1, &"aim")
	action_node = AnimationNodeAnimation.new()
	action_node.animation = &"fire"
	graph.add_node(&"action", action_node)
	graph.add_node(&"speed", AnimationNodeTimeScale.new())
	graph.connect_node(&"speed", 0, &"action")
	shot_node = AnimationNodeOneShot.new()
	shot_node.fadein_time = 0.035
	shot_node.fadeout_time = 0.10
	graph.add_node(&"shot", shot_node)
	graph.connect_node(&"shot", 0, &"ads")
	graph.connect_node(&"shot", 1, &"speed")
	graph.connect_node(&"output", 0, &"shot")
	tree = AnimationTree.new()
	add_child(tree)
	tree.anim_player = tree.get_path_to(player)
	tree.tree_root = graph
	tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	tree.active = true
	tree.set("parameters/speed/scale", 1.0)
	tree.advance(0)
	_foregrip_rig.setup(self)
	preload("res://scripts/rifle_polymer_finish.gd").apply(self,_mounted_parts)
	var audio_weapon := preload("res://scripts/rifle_reload_audio.gd").weapon_for(model_resource.resource_path)
	if not audio_weapon.is_empty():
		_reload_audio = preload("res://scripts/rifle_reload_audio.gd").new()
		_reload_audio.weapon = audio_weapon
		_reload_audio.name = "RifleReloadAudio"
		add_child(_reload_audio)

var _foregrip_rig = preload("res://scripts/foregrip_rig.gd").new()
var _foregrip_pose = preload("res://scripts/foregrip_pose.gd").new()

func advance_pose(ads: float, delta: float) -> void:
	_held_hand_pose.restore(_foregrip_rig.rig)
	_drum_hand.restore(_foregrip_rig.rig if _foregrip_rig.rig!=null else skeleton)
	_foregrip_pose.restore(_foregrip_rig.rig if _foregrip_rig.rig!=null else skeleton)
	tree.set("parameters/ads/blend_amount", ads)
	tree.advance(delta)
	if is_instance_valid(_reload_audio): _reload_audio.advance(delta)
	_foregrip_pose.advance(delta)
	if _drum_clock >= 0.0:
		_drum_clock += delta * _drum_speed
		_foregrip_pose.elapsed = preload("res://scripts/large_drum_reload.gd").source_time(_drum_clock,_drum_source_length)
		if _drum_clock >= _drum_source_length*1.75: _drum_clock = -1.0
	if _mounted_parts.has("underbarrel"):
		_foregrip_pose.apply(_foregrip_rig.rig, _mounted_parts.underbarrel, _foregrip_rig)
	if _drum_clock >= 0.0 and _mounted_parts.has("magazine") and _mounted_parts.magazine.has_node("LargeDrum"):
		var clearance_weight:float = 1.0-_foregrip_pose.weight if _mounted_parts.has("underbarrel") else 1.0
		_drum_hand.clear_shell(_mounted_parts.magazine,_foregrip_rig,clearance_weight)
	else:
		_drum_hand.correction_meters=0.0
	_held_hand_pose.apply(_foregrip_rig.rig, _foregrip_pose, _mounted_parts.has("underbarrel"), ads)

func _build_stable_ads_fire() -> void:
	var aim := player.get_animation(&"aim")
	var fire := player.get_animation(&"aim_fire").duplicate() as Animation
	var weapon_root := skeleton.get_bone_parent(skeleton.find_bone(ads_mechanical_bone))
	for track in fire.get_track_count():
		var path := fire.track_get_path(track)
		var bone := skeleton.find_bone(path.get_subname(0)) if path.get_subname_count() > 0 else -1
		var ancestor := bone
		while ancestor >= 0 and ancestor != weapon_root:
			ancestor = skeleton.get_bone_parent(ancestor)
		if ancestor == weapon_root:
			continue # Keep slide, hammer and other weapon mechanics animated.
		var kind := fire.track_get_type(track)
		if kind not in [Animation.TYPE_POSITION_3D, Animation.TYPE_ROTATION_3D, Animation.TYPE_SCALE_3D]:
			continue
		var aim_track := aim.find_track(path, kind)
		if aim_track < 0:
			continue
		var pose: Variant = _sample_transform_track(aim, aim_track, kind, 0.0)
		for key in fire.track_get_key_count(track):
			fire.track_set_key_value(track, key, pose)
	# The library is instance-local, so the source asset and reload clips stay intact.
	var library := player.get_animation_library(&"")
	library.remove_animation(&"aim_fire")
	library.add_animation(&"aim_fire", fire)

func _build_equip_clip() -> void:
	if not use_charge_equip:
		var draw_library := player.get_animation_library(&"").duplicate() as AnimationLibrary
		draw_library.add_animation(&"equip_charge", player.get_animation(&"draw").duplicate())
		player.remove_animation_library(&"")
		player.add_animation_library(&"", draw_library)
		return
	# Extract the synchronized hand/bolt section; blend in from the held idle pose.
	var source := player.get_animation(&"reload_empty")
	var idle := player.get_animation(&"idle")
	var clip := Animation.new()
	var start := 1.75
	var lead := 0.18
	clip.length = source.length - start + lead
	for track in source.get_track_count():
		var kind := source.track_get_type(track)
		if kind not in [Animation.TYPE_POSITION_3D, Animation.TYPE_ROTATION_3D, Animation.TYPE_SCALE_3D]:
			continue
		var path := source.track_get_path(track)
		var target := clip.add_track(kind)
		clip.track_set_path(target, path)
		var idle_track := idle.find_track(path, kind)
		for frame in ceili(clip.length * 60.0) + 1:
			var time := minf(frame / 60.0, clip.length)
			var source_time := start + maxf(0.0, time - lead)
			var value: Variant = _sample_transform_track(source, track, kind, source_time)
			if idle_track >= 0 and time < lead:
				var rest: Variant = _sample_transform_track(idle, idle_track, kind, 0.0)
				var weight := smoothstep(0.0, lead, time)
				value = rest.slerp(value, weight) if kind == Animation.TYPE_ROTATION_3D else rest.lerp(value, weight)
			clip.track_insert_key(target, time, value)
	var library := player.get_animation_library(&"").duplicate() as AnimationLibrary
	library.add_animation(&"equip_charge", clip)
	player.remove_animation_library(&"")
	player.add_animation_library(&"", library)

func _sample_transform_track(animation: Animation, track: int, kind: int, time: float) -> Variant:
	if kind == Animation.TYPE_ROTATION_3D:
		return animation.rotation_track_interpolate(track, time)
	if kind == Animation.TYPE_SCALE_3D:
		return animation.scale_track_interpolate(track, time)
	return animation.position_track_interpolate(track, time)

func _tune_materials(node: Node) -> void:
	if node is MeshInstance3D:
		preload("res://scripts/hk416_materials.gd").prepare(node)
		for surface in node.mesh.get_surface_count():
			var source := node.get_active_material(surface) as StandardMaterial3D
			if source == null:
				continue
			var finish := preload("res://scripts/weapon_surface_materials.gd").for_source(source, str(node.name))
			if finish != null:
				node.set_surface_override_material(surface, finish)
				continue
			var material := source.duplicate() as StandardMaterial3D
			var label := source.resource_name.to_lower()
			var fabric := label.contains("arms")
			var polymer := label.contains("grip") or label.contains("stock")
			# Set display-space surface colors explicitly instead of multiplying
			# the imported, linear-authored gray palette into another pale gray.
			if fabric:
				material.albedo_color = Color(0.62, 0.59, 0.53)
				material.roughness = 0.88
				material.metallic = 0.0
				material.metallic_specular = 0.08
			elif polymer:
				material.albedo_color = Color(0.32, 0.26, 0.18)
				material.roughness = 0.76
				material.metallic = 0.0
				material.metallic_specular = 0.16
			else:
				material.albedo_color = Color(0.24, 0.27, 0.29)
				if label.contains("details"):
					material.albedo_color = Color(0.23, 0.25, 0.27)
				elif label.contains("bullets"):
					material.albedo_color = Color(0.52, 0.34, 0.12)
				material.roughness = 0.48
				material.metallic = 0.45
				material.metallic_specular = 0.35
			node.set_surface_override_material(surface, material)
	for child in node.get_children():
		_tune_materials(child)

func cancel_action() -> void:
	# Ownership may change between two instances of the same model, without a
	# model reload. Cancel both the one-shot and its post-animation pose clocks.
	stop_action_audio()
	_held_hand_pose.restore(_foregrip_rig.rig)
	_drum_hand.restore(_foregrip_rig.rig if _foregrip_rig.rig!=null else skeleton)
	_foregrip_pose.restore(_foregrip_rig.rig if _foregrip_rig.rig!=null else skeleton)
	_drum_clock=-1.0
	_drum_speed=1.0
	_foregrip_pose.begin("",0.0,1.0)
	tree.set("parameters/shot/request",AnimationNodeOneShot.ONE_SHOT_REQUEST_ABORT)
	tree.set("parameters/speed/scale",1.0)
	advance_pose(0.0,0.0)

func play_action(clip: StringName, duration: float = 0.0) -> void:
	if is_instance_valid(_reload_audio):
		_reload_audio.begin(clip,player.get_animation(clip).length,duration,str(gunsmith_parts.get("magazine",false))=="large_drum")
	_held_hand_pose.restore(_foregrip_rig.rig)
	_drum_hand.restore(_foregrip_rig.rig if _foregrip_rig.rig!=null else skeleton)
	_foregrip_pose.restore(_foregrip_rig.rig if _foregrip_rig.rig!=null else skeleton)
	tree.set("parameters/shot/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_ABORT)
	tree.advance(0)
	_foregrip_rig.setup(self)
	var actual := clip
	_drum_clock = -1.0
	if clip in [&"reload",&"reload_empty"] and str(gunsmith_parts.get("magazine",false)) == "large_drum":
		actual = preload("res://scripts/large_drum_reload.gd").ensure(self,clip)
		_drum_clock = 0.0
		_drum_source_length = player.get_animation(clip).length
	action_node.animation = actual
	var speed := player.get_animation(actual).length / duration if duration > 0.0 else 1.0
	_drum_speed = speed
	_foregrip_pose.begin(clip, player.get_animation(clip).length, speed)
	tree.set("parameters/speed/scale", speed)
	tree.set("parameters/shot/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
	tree.advance(0)
	_foregrip_rig.setup(self)
	if _mounted_parts.has("underbarrel"):
		_foregrip_pose.apply(_foregrip_rig.rig,_mounted_parts.underbarrel,_foregrip_rig)

	_held_hand_pose.apply(_foregrip_rig.rig, _foregrip_pose, _mounted_parts.has("underbarrel"), _held_hand_pose.ads)

func socket_position(socket: StringName) -> Vector3:
	if socket == &"SOCKET_Muzzle" and _mounted_parts.has("muzzle"):
		return _part_point("muzzle", "Muzzle")
	if socket == &"SOCKET_Muzzle" and calibrated_muzzle_bone != &"":
		return _muzzle_bone_transform() * calibrated_muzzle_position
	var index := skeleton.find_bone(socket)
	return skeleton.to_global(skeleton.get_bone_global_pose(index).origin)

func muzzle_direction() -> Vector3:
	if _mounted_parts.has("muzzle"):
		return (_part_point("muzzle", "Muzzle") - _part_point("muzzle", "Mount")).normalized()
	if calibrated_muzzle_bone != &"":
		return (_muzzle_bone_transform().basis * calibrated_muzzle_forward).normalized()
	return (socket_position(&"FrontSight") - socket_position(&"RearSight")).normalized()

func _muzzle_bone_transform() -> Transform3D:
	return skeleton.global_transform * skeleton.get_bone_global_pose(skeleton.find_bone(calibrated_muzzle_bone))

func visible_aim_position() -> Vector3:
	# The firing ray follows what is visible, including mechanical and recoil motion.
	if _mounted_parts.has("optic"):
		return _part_point("optic", "ReticleDot")
	return socket_position(&"FrontSight")

func ads_sight_position(socket: StringName) -> Vector3:
	if _mounted_parts.has("optic") and socket in [&"RearSight", &"FrontSight"]:
		if ads_mechanical_bone != &"":
			var part: Node3D = _mounted_parts.optic
			var holder: BoneAttachment3D = part.get_parent()
			var optic_moving := skeleton.find_bone(ads_mechanical_bone)
			if holder.bone_idx == optic_moving:
				var optic_parent := skeleton.get_bone_parent(optic_moving)
				var optic_closed := skeleton.get_bone_global_pose(optic_parent) * skeleton.get_bone_rest(optic_moving)
				var marker: Node3D = part.get_node("SightRear" if socket == &"RearSight" else "SightFront")
				return skeleton.global_transform * optic_closed * part.transform * marker.position
		return _part_point("optic", "SightRear" if socket == &"RearSight" else "SightFront")
	if ads_mechanical_bone == &"":
		return socket_position(socket)
	var moving := skeleton.find_bone(ads_mechanical_bone)
	var sight := skeleton.find_bone(socket)
	var parent := skeleton.get_bone_parent(moving)
	# Follow the animated gun/hand pose, but evaluate the slide at battery.
	# Visible sights still follow the real slide through socket_position().
	var closed := skeleton.get_bone_global_pose(parent) * skeleton.get_bone_rest(moving)
	var offset := skeleton.get_bone_global_rest(moving).affine_inverse() * skeleton.get_bone_global_rest(sight).origin
	return skeleton.to_global(closed * offset)
