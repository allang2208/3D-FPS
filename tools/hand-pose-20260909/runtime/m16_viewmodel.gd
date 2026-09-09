extends "res://scripts/infima_viewmodel.gd"
## DJMaesen source timing; mechanical objects baked to bones, Infima standard arms.
var _draw_remaining := 0.0
var _draw_duration := 0.62
var _action_audio: Node

func uses_action_audio() -> bool:
	return true

func stop_action_audio() -> void:
	if is_instance_valid(_action_audio):
		_action_audio.stop()

func equip_animation(first_draw: bool) -> StringName:
	return &"equip_charge" if first_draw else &"equip_quick"

func cancel_action() -> void:
	_draw_remaining=0.0
	_update_draw_offset()
	super.cancel_action()

func play_action(clip: StringName, duration: float = 0.0) -> void:
	super.play_action(clip, duration)
	if not is_instance_valid(_action_audio):
		_action_audio = preload("res://scripts/m16_action_audio.gd").new()
		_action_audio.name = "M16ActionAudio"
		add_child(_action_audio)
	_action_audio.begin(clip, player.get_animation(clip).length, duration, str(gunsmith_parts.get("magazine",false))=="large_drum")
	_draw_duration = 0.22 if clip == &"equip_charge" else 0.62
	_draw_remaining = _draw_duration if clip in [&"equip_charge", &"equip_quick"] else 0.0
	_update_draw_offset()

func advance_pose(ads: float, delta: float) -> void:
	super.advance_pose(ads, delta)
	if is_instance_valid(_action_audio):
		_action_audio.advance(delta)
	_draw_remaining = maxf(0.0, _draw_remaining - delta)
	_update_draw_offset()

func _update_draw_offset() -> void:
	var weight := smoothstep(0.0, _draw_duration, _draw_remaining)
	get_child(0).position = Vector3(0, -0.30, 0.15) * weight

func _build_equip_clip() -> void:
	for node in find_children("*", "Skeleton3D", true, false):
		if node.find_bone("RearSight") >= 0:
			skeleton = node
	get_child(0).rotation.y = PI
	var library := player.get_animation_library(&"").duplicate(true) as AnimationLibrary
	player.remove_animation_library(&"")
	player.add_animation_library(&"", library)
	var held := player.get_animation(&"idle")
	for track in held.get_track_count():
		if held.track_get_key_count(track) == 0:
			continue
		var value: Variant = held.track_get_key_value(track, 0)
		for key in held.track_get_key_count(track):
			held.track_set_key_value(track, key, value)
	library.add_animation(&"aim", held.duplicate())
	# Source has no draw clip: lift the complete held assembly without changing grips.
	var draw := held.duplicate() as Animation
	draw.length = 0.62
	library.add_animation(&"equip_quick", draw)
	library.add_animation(&"equip_charge", preload("res://scripts/m16_equip_animation.gd").build(self, player.get_animation(&"reload_empty"), held))
	var fire := held.duplicate() as Animation
	fire.length = 0.10
	var path := NodePath(str(player.get_node(player.root_node).get_path_to(skeleton)) + ":m16a2_bolt")
	var track := fire.find_track(path, Animation.TYPE_POSITION_3D)
	var rest := skeleton.get_bone_pose_position(skeleton.find_bone("m16a2_bolt"))
	if track >= 0:
		rest = fire.position_track_interpolate(track, 0.0)
	else:
		track = fire.add_track(Animation.TYPE_POSITION_3D)
		fire.track_set_path(track, path)
	# Blender -Y forward maps to Godot +Z before the model's one-time PI turn.
	fire.track_insert_key(track, 0.0, rest)
	fire.track_insert_key(track, 0.025, rest + Vector3(0, 0, -0.03))
	fire.track_insert_key(track, 0.075, rest)
	fire.track_insert_key(track, 0.10, rest)
	library.remove_animation(&"fire")
	library.add_animation(&"fire", fire)
	library.add_animation(&"aim_fire", fire.duplicate())

func _tune_materials(node: Node) -> void:
	if node is MeshInstance3D:
		for surface in node.mesh.get_surface_count():
			var source := node.get_active_material(surface) as StandardMaterial3D
			if source == null:
				continue
			var mat := source.duplicate() as StandardMaterial3D
			if source.resource_name.contains("Arms"):
				mat.albedo_color = Color(0.62, 0.59, 0.53)
				mat.roughness = 0.88
				mat.metallic = 0.0
				mat.metallic_specular = 0.08
			else:
				node.set_surface_override_material(surface,preload("res://scripts/rifle_clean_finish.gd").textured(source,"m16"))
				continue
			node.set_surface_override_material(surface, mat)
	for child in node.get_children():
		_tune_materials(child)

func _attachment_adapter():
	return preload("res://scripts/m16_attachment_mounts.gd")
