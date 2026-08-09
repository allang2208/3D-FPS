extends SceneTree
## UI 预览截图：加载设置面板 Demo 并保存 PNG（需要显示环境，非 --headless）
## 运行： $godot --path 'E:\3d\3-dfps' --script res://tools/ui_preview.gd

const OUT := "C:/Users/allan/AppData/Local/Temp/ui_preview.png"

func _initialize() -> void:
	var ps: PackedScene = load("res://scenes/ui/settings_demo.tscn")
	root.add_child(ps.instantiate())
	for i in 6:
		await process_frame
	await RenderingServer.frame_post_draw
	var img := root.get_texture().get_image()
	img.save_png(OUT)
	print("saved ", OUT)
	quit()
