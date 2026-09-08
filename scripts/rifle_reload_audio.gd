extends "res://scripts/m16_action_audio.gd"
## Source-animation contacts, sampled from the current weapon rigs at 60 Hz.
## Only reloads use this bank; dedicated equipment recordings remain separate.
const PROFILES := {
	"infima_ar": {
		&"reload": [[.433333,&"mag_out"],[1.233333,&"mag_insert"],[1.483333,&"mag_seat"]],
		&"reload_empty": [[.416667,&"mag_out"],[1.15,&"mag_insert"],[1.466667,&"mag_seat"],[2.133333,&"charge_pull"],[2.333333,&"charge_release"]]},
	"akm_classic": {
		&"reload": [[.433333,&"mag_out"],[1.233333,&"mag_insert"],[1.483333,&"mag_seat"]],
		&"reload_empty": [[.416667,&"mag_out"],[1.15,&"mag_insert"],[1.466667,&"mag_seat"],[2.133333,&"charge_pull"],[2.333333,&"charge_release"]]},
	"hk416": {
		&"reload": [[.483333,&"mag_out"],[1.266667,&"mag_insert"],[1.583333,&"mag_seat"]],
		&"reload_empty": [[.35,&"mag_out"],[.9,&"mag_insert"],[1.333333,&"mag_seat"],[2.166667,&"bolt_release"]]},
	"qbz191": {
		&"reload": [[.483333,&"mag_out"],[1.266667,&"mag_insert"],[1.583333,&"mag_seat"]],
		&"reload_empty": [[.35,&"mag_out"],[.9,&"mag_insert"],[1.333333,&"mag_seat"],[2.166667,&"bolt_release"]]},
}
var weapon := ""

static func weapon_for(path: String) -> String:
	for id: String in PROFILES:
		if path.contains(id): return id
	return ""

func _ready() -> void:
	for cue: StringName in STREAMS:
		var voice := AudioStreamPlayer.new()
		voice.name = cue
		var path := "res://assets/sfx/%s/mechanics/%s.wav" % [weapon,cue]
		voice.stream = load(path) if ResourceLoader.exists(path) else STREAMS[cue]
		voice.bus = "SFX"
		voice.volume_db = -4.0
		add_child(voice)
		_players[cue] = voice

func begin(clip: StringName, clip_length: float, duration: float, drum := false) -> void:
	start_cues(PROFILES.get(weapon,{}).get(clip,[]),clip_length,duration,drum and clip in [&"reload",&"reload_empty"])
