extends RefCounted
## DJMaesen empty reload: frames 108–136 at 30 FPS, after magazine seating.
const START := 1.4
const LEAD := 0.22
const TAIL := 0.16

static func build(model: Node3D, source: Animation, idle: Animation) -> Animation:
	var clip := Animation.new()
	clip.length = LEAD + source.length - START + TAIL
	clip.loop_mode = Animation.LOOP_NONE
	for track in source.get_track_count():
		var kind := source.track_get_type(track)
		if kind not in [Animation.TYPE_POSITION_3D, Animation.TYPE_ROTATION_3D, Animation.TYPE_SCALE_3D]:
			continue
		var path := source.track_get_path(track)
		var target := clip.add_track(kind)
		clip.track_set_path(target, path)
		var rest_track := idle.find_track(path, kind)
		for frame in ceili(clip.length * 60.0) + 1:
			var time := minf(frame / 60.0, clip.length)
			var sample := clampf(START + time - LEAD, START, source.length)
			var value: Variant = model._sample_transform_track(source, track, kind, sample)
			if rest_track >= 0:
				var rest: Variant = model._sample_transform_track(idle, rest_track, kind, 0.0)
				var weight := smoothstep(0.0, LEAD, time) * (1.0 - smoothstep(clip.length - TAIL, clip.length, time))
				value = rest.slerp(value, weight) if kind == Animation.TYPE_ROTATION_3D else rest.lerp(value, weight)
			clip.track_insert_key(target, time, value)
	return clip
