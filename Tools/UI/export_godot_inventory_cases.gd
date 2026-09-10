extends SceneTree
const Spatial = preload("res://ui/spatial_inventory.gd")

func _initialize() -> void:
	var cases: Array = []
	for source in [0, 8, 36, 49]:
		for target in [0, 4, 8, 17, 18, 36, 49, 71]:
			var bag: Array = []
			bag.resize(72)
			var gun := {"id":"gun", "instance_id":"gun", "category":"weapon_ranged", "weaponType":"rifle", "isTwoHanded":true, "stack":1, "maxStack":1}
			bag[source] = Spatial.normalize_at(gun, source)
			if Spatial.occupancy(bag)[target] >= 0:
				continue
			bag[target] = Spatial.normalize_at({"id":"potion", "instance_id":"potion", "category":"consumable", "stack":8, "maxStack":99}, target)
			for from in [source, target]:
				for to in range(-1, 74):
					var result := Spatial.move(bag, from, to)
					var placed: Array = []
					for cell in result.size():
						if result[cell] != null:
							placed.append({"id":result[cell].instance_id, "cell":cell, "count":result[cell].stack})
					cases.append({"gun":source,"potion":target,"from":"gun" if from==source else "potion","to":to,"valid":not result.is_empty(),"items":placed})
	var output := FileAccess.open("D:/FPS3D/FPSGAME/Tools/UI/fixtures/godot_inventory_cases.json", FileAccess.WRITE)
	if output == null:
		push_error("Cannot write inventory cases")
		quit(1)
		return
	output.store_string(JSON.stringify(cases))
	output.close()
	print("GODOT_INVENTORY_REFERENCE_COMPLETE cases=",cases.size())
	quit(0)
