extends SceneTree
const AudioBank = preload("res://scripts/rifle_reload_audio.gd")
const Drum = preload("res://scripts/large_drum_reload.gd")
var failures := 0
var events: Array = []

func check(ok: bool, label: String) -> void:
	if not ok:
		failures += 1
		push_error(label)

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var groups := 0
	for weapon in AudioBank.PROFILES:
		var bank := AudioBank.new()
		bank.weapon = weapon
		root.add_child(bank)
		bank.cue_played.connect(func(cue, time): events.append([cue, time]))
		for clip in AudioBank.PROFILES[weapon]:
			var cues: Array = AudioBank.PROFILES[weapon][clip]
			var source := Animation.new()
			source.length = 3.0
			var track := source.add_track(Animation.TYPE_VALUE)
			source.track_set_path(track, "Dummy:value")
			for cue in cues:
				source.track_insert_key(track, cue[0], cue[1])
			for drum in [false, true]:
				var animation := Drum.build(source) if drum else source
				for speed in [.7, 1.0, 1.6]:
					for fps in [30, 60, 144]:
						groups += 1
						events.clear()
						bank.begin(clip, source.length, animation.length / speed, drum)
						for frame in ceili(animation.length / speed * fps) + 1:
							bank.advance(1.0 / fps)
						check(events.size() == cues.size(), "cue count")
						for i in mini(events.size(), cues.size()):
							check(events[i][0] == cues[i][1], "cue order")
							var error: float = events[i][1] - animation.track_get_key_time(track, i)
							check(error >= -0.00001 and error <= speed / fps + 0.00001, "audio matches actual retimed animation key")
						bank.stop()
						bank.advance(10.0)
						check(events.size() == cues.size(), "cancelled events stay cancelled")
						for voice in bank._players.values():
							check(not voice.playing and voice.pitch_scale == 1.0 and voice.bus == "SFX", "stop/pitch/bus")
		bank.free()
	print("RIFLE_AUDIO_MODULES groups=%d failures=%d" % [groups, failures])
	quit(1 if failures else 0)
