extends RefCounted
## Re-time the authored arm + mechanical tracks together. More time is spent
## withdrawing, carrying and seating; release and return retain a brisk cadence.
const SOURCE := [0.0,.20,.38,.56,.72,.88,1.0]
const TARGET := [0.0,.13,.36,.60,.82,.93,1.0]
static func map_phase(value:float,from:Array,to:Array) -> float:
	var t:=clampf(value,0,1)
	for i in from.size()-1:
		if t<=from[i+1]:
			var u:float=(t-from[i])/(from[i+1]-from[i])
			return lerpf(to[i],to[i+1],u)
	return 1.0
static func output_time(authored_time:float,length:float) -> float:
	return map_phase(authored_time/length,SOURCE,TARGET)*length*1.75
static func source_time(output_time_:float,length:float) -> float:
	return map_phase(output_time_/(length*1.75),TARGET,SOURCE)*length
static func build(source:Animation) -> Animation:
	var result:=source.duplicate(true) as Animation
	result.length=source.length*1.75
	result.loop_mode=Animation.LOOP_NONE
	# Alter key times in reverse so neighbouring keys cannot transiently collide.
	for track in result.get_track_count():
		for key in range(result.track_get_key_count(track)-1,-1,-1):
			result.track_set_key_time(track,key,output_time(source.track_get_key_time(track,key),source.length))
	return result
static func ensure(model:Node3D,clip:StringName) -> StringName:
	var name_:StringName=StringName("drum_"+str(clip))
	if not model.player.has_animation(name_):
		var lib:=model.player.get_animation_library(&"").duplicate() as AnimationLibrary
		model.player.remove_animation_library(&"")
		model.player.add_animation_library(&"",lib)
		lib.add_animation(name_,build(model.player.get_animation(clip)))
	return name_
