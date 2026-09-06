extends SceneTree

const Weather := preload("res://scripts/weather_system.gd")

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var world := Node3D.new()
	root.add_child(world)
	var weather := Weather.new()
	world.add_child(weather)
	await process_frame
	var expected := {
		"light_rain": Vector3(0.012,0.0,0.09),
		"rain": Vector3(0.18,0.22,0.055),
		"storm": Vector3(0.52,0.38,0.0),
	}
	for mode in expected:
		weather.profile = Weather.PROFILES[mode]
		weather._update_rain_audio(20.0)
		var actual := Vector3(weather._rain_gain,weather._detail_gain,weather._drizzle_gain)
		assert(actual.distance_to(expected[mode])<0.0001)
		assert(is_equal_approx(weather.rain_audio.volume_db,linear_to_db(maxf(actual.x,0.0001))))
		assert(is_equal_approx(weather.rain_detail_audio.volume_db,linear_to_db(maxf(actual.y,0.0001))))
		assert(is_equal_approx(weather.rain_drizzle_audio.volume_db,linear_to_db(maxf(actual.z,0.0001))))
	assert(not weather.rain_drizzle_audio.playing or weather.rain_drizzle_audio.volume_db<-70.0)
	for player in [weather.rain_audio,weather.rain_detail_audio,weather.rain_drizzle_audio]:
		assert(player.stream.format==AudioStreamWAV.FORMAT_16_BITS)
		assert(player.stream.stereo)
		assert(player.stream.loop_mode==AudioStreamWAV.LOOP_FORWARD)
		assert(player.stream.loop_end==529200)
		assert(is_equal_approx(player.stream.get_length(),24.0))
	assert(weather.rain_drizzle_audio.get_meta("source_path").contains("rain_leaves_ground_ccby_v4"))
	weather.profile = Vector3.ZERO
	weather._update_rain_audio(20.0)
	assert(not weather.rain_audio.playing)
	assert(not weather.rain_detail_audio.playing)
	assert(not weather.rain_drizzle_audio.playing)
	print("PASS weather audio: quiet sparse drizzle, stronger medium patter, unchanged storm bed/detail, clean stop")
	quit()
