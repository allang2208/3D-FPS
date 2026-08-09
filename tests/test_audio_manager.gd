extends SceneTree


func _initialize() -> void:
	var am: Node = root.get_node_or_null("AudioManager")
	print("AudioManager autoload: ", am != null)
	if am == null:
		quit(1)
		return
	var bus_names: PackedStringArray = []
	for i in AudioServer.bus_count:
		bus_names.append(AudioServer.get_bus_name(i))
	print("Buses: ", ", ".join(bus_names))
	am.play_sfx(null)  # null-safe no-op, verifies call path
	print("set_sfx_volume ok: ", am.set_sfx_volume(0.5) == null)
	quit(0)
