extends SceneTree
## 状态栏解释浮窗实拍
## 运行：$godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_hud_tooltip.gd

var _frames := 0


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		var sb = load("res://ui/status_bar.gd").new()
		root.add_child(sb)
		sb.set_hp(76, 300)
		sb.set_mp(48, 120)
		sb.set_ammo(30, 90)
		sb.set_weapon_name("AK-74")
		sb.set_kills(3)
		sb.call("_show_tooltip", "生命值", "角色的生命，归零时死亡。低血量会触发红色警示。",
			[["当前生命", "76 / 300"], ["低血量", "低于 25% 警示"]], Vector2(20, 40))
	if _frames == 8:
		var img := root.get_viewport().get_texture().get_image()
		if img != null and img.get_width() > 0:
			img.save_png("res://docs/preview/ui_hud_tooltip.png")
			print("SAVED ", ProjectSettings.globalize_path("res://docs/preview/ui_hud_tooltip.png"))
		quit(0)
		return true
	return false
