extends SceneTree
## 背包/装备 UI 预览截图（Vega 金白验收）
## 运行： $godot --path 'E:\3d\3-dfps' --script res://tools/ui_preview_backpack.gd

const ItemDB := preload("res://ui/item_db.gd")
const Backpack := preload("res://ui/backpack.gd")
const Equipment := preload("res://ui/equipment.gd")
const BackpackHUD := preload("res://ui/backpack_hud.gd")

const OUT := "C:/Users/allan/AppData/Local/Temp/ui_preview_backpack.png"

func _initialize() -> void:
	root.size = Vector2i(1920, 1080)
	var db := ItemDB.new()
	var bp := Backpack.new(db)
	var eq := Equipment.new(bp)
	var hud := BackpackHUD.new()
	root.add_child(hud)
	await process_frame
	await process_frame
	hud.setup(bp, eq)
	var ids := db.get_all_ids()
	for i in mini(16, ids.size()):
		bp.add_item(ids[i], 1 + (i % 3))
	# 尝试装备几件可装备物品（type 非消耗品），演示装备槽图标
	var equipped := 0
	for i in mini(bp.slots.size(), bp.slots.size()):
		var inst = bp.slots[i]
		if equipped >= 4:
			break
		if inst != null and not inst.is_empty():
			var def := db.get_def(str(inst.get("id", "")))
			if def != null and str(def.get("type", "")) != "消耗品":
				if eq.equip_from_backpack(i):
					equipped += 1
	# 打开装备/背包面板（模拟 Tab 键）
	var ev := InputEventKey.new()
	ev.keycode = KEY_TAB
	ev.pressed = true
	hud._unhandled_input(ev)
	for i in 20:
		await process_frame
	await RenderingServer.frame_post_draw
	var img := root.get_texture().get_image()
	img.save_png(OUT)
	print("saved ", OUT)
	quit()
