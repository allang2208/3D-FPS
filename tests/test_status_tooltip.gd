extends SceneTree
## 状态栏 HUD 解释浮窗冒烟：数据记录 + 浮窗显示 + 排版无报错

var _sb


func _initialize() -> void:
	process_frame.connect(_run)


func _run() -> void:
	_sb = load("res://ui/status_bar.gd").new()
	root.add_child(_sb)
	_sb.set_hp(76, 300)
	_sb.set_mp(48, 120)
	_sb.set_ammo(30, 90)
	_sb.set_weapon_name("AK-74")
	_sb.set_kills(3)
	_sb.call("_show_tooltip", "生命值", "角色的生命，归零时死亡。",
		[["当前生命", "76 / 300"], ["低血量", "低于 25% 警示"]], Vector2(20, 40))
	var tip: PanelContainer = _sb.get("_tip")
	print("tooltip visible: ", tip != null and tip.visible)
	print("tooltip title: ", _sb.get("_tip_title").text)
	quit(0 if tip != null and tip.visible else 1)
