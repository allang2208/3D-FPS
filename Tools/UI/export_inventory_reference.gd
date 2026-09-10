extends SceneTree
func _initialize():
	var db = load("res://ui/item_db.gd").new()
	var entries = {}
	for id in db.get_all_ids():
		entries[id] = db.get_def(id).duplicate(true)
	var output = "D:/FPS3D/FPSGAME/Content/ColdSteelData"
	DirAccess.make_dir_recursive_absolute(output)
	var f = FileAccess.open(output + "/items.json", FileAccess.WRITE)
	f.store_string(JSON.stringify(entries, "\t"))
	f.close()
	print("INVENTORY_DEFINITIONS_EXPORTED ", entries.size())
	quit()
