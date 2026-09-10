extends SceneTree
const Tip = preload("res://ui/item_tooltip.gd")
const DB = preload("res://ui/item_db.gd")
const Config = preload("res://ui/npc_config.gd")
const OUT = "D:/FPS3D/FPSGAME/Saved/ItemTooltip/"
func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH", "user://ue-tooltip-reference-20260909.save")
	OS.set_environment("GAME_SETTINGS_PATH", "user://ue-tooltip-reference-20260909.cfg")
	call_deferred("run")
func run() -> void:
	root.size = Vector2i(1280,720)
	var db = DB.new()
	var configs = {}
	for id in db.get_all_ids():
		var item = db.create_instance(id)
		configs[id] = Config.craft_config_for(item)
	var file = FileAccess.open("D:/FPS3D/FPSGAME/Content/ColdSteelData/tooltip-reference.json", FileAccess.WRITE)
	file.store_string(JSON.stringify({"craft": configs}, "\t"))
	file.close()
	var tip = Tip.new()
	root.add_child(tip)
	await process_frame
	var sword = db.create_instance("fps_akm")
	sword.enhanceLevel=10
	sword._craftData={"blade":"light_blade"}
	sword.gunsmith_parts={"optic":true,"magazine":true,"stock":"precision"}
	sword._craftEffects={"damagePercent":0.2,"attackIntervalDelta":-50,"moveSpeedPercent":-0.1}
	sword._enchantData={"prefix":{"name":"锋利"}}
	sword._enchantEffects={"damagePercent":0.1,"poisonOnHit":true}
	var index=0
	for item in [db.create_instance("hp_potion",3),sword]:
		tip.render(item)
		tip.set_pinned(true)
		for n in 8: await process_frame
		tip.place_at(Vector2(1250,680))
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(OUT+"godot-"+str(index)+"-1280.png")
		index+=1
	print("TOOLTIP_REFERENCE_COMPLETE configs=",configs.size())
	quit()
