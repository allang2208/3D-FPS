extends "res://scripts/portal.gd"
func _ready() -> void:
	name="ForemanPracticePortal"
	target_scene="res://scenes/foreman_demo.tscn"
	label_text="工头试玩 · 鞭击与号召"
	position=Vector3(10,1.4,10)
	super._ready()
