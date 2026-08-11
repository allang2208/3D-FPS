extends SceneTree
## 完整 HUD 实拍（走 autoload(HUD)：顶部栏/左侧导航/快捷栏/侧边菜单/经验条）
## 运行：$godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_hud_full.gd

var _frames := 0


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		var scene := Node3D.new()
		scene.name = "HudScene"
		root.add_child(scene)
		current_scene = scene
		var player := CharacterBody3D.new()
		player.name = "Player"
		player.set_script(load("res://scripts/player.gd"))
		scene.add_child(player)
	if _frames == 24:
		var img := root.get_viewport().get_texture().get_image()
		if img != null and img.get_width() > 0:
			img.save_png("res://docs/preview/ui_hud_full.png")
			print("SAVED ", ProjectSettings.globalize_path("res://docs/preview/ui_hud_full.png"))
		quit(0)
		return true
	return false
