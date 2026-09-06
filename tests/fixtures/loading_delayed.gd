extends Node
var initialized := false
func _ready():
	add_child(load("res://ui/loading_screen.gd").new())
	await get_tree().create_timer(0.25, true).timeout
	initialized = true
func is_loading_ready() -> bool:
	return initialized
