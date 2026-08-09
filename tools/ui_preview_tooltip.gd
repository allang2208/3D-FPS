extends SceneTree
## 物品浮窗预览截图（验证白底）
## 运行： $godot --path 'E:\3d\3-dfps' --script res://tools/ui_preview_tooltip.gd

const ItemDB := preload("res://ui/item_db.gd")
const ItemTooltip := preload("res://ui/item_tooltip.gd")

const OUT := "C:/Users/allan/AppData/Local/Temp/ui_preview_tooltip.png"

func _initialize() -> void:
	root.size = Vector2i(900, 700)
	var db := ItemDB.new()
	var ids := db.get_all_ids()
	if ids.is_empty():
		print("no items")
		quit(1)
		return
	var item := db.create_instance(ids[0], 3)
	var tt := ItemTooltip.new()
	root.add_child(tt)
	await process_frame
	await process_frame
	tt.render(item)
	for i in 6:
		await process_frame
	await RenderingServer.frame_post_draw
	var img := root.get_texture().get_image()
	img.save_png(OUT)
	print("saved ", OUT)
	quit()
