extends SceneTree
## 无头验证：UI Token 纪律
## 1) DESIGN.md 关键色板已落 ui/style.gd（测试侧以 DESIGN.md 色值为真源）
## 2) status_bar / item_tooltip 禁止硬编码颜色（一律走 Style.* Token）
## 运行： $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_ui_tokens.gd

const Style := preload("res://ui/style.gd")

var _fail := 0

func _check(name: String, ok: bool, detail := "") -> void:
	print("TEST ", name, "=", ok, "" if detail.is_empty() else "  " + detail)
	if not ok:
		_fail += 1

func _initialize() -> void:
	# 1) DESIGN.md 关键 Token 对齐 style.gd
	_check("v2_bg_scene", Style.V2_BG_SCENE.is_equal_approx(Color(0.039, 0.055, 0.086)))
	_check("v2_accent_cyan", Style.V2_ACCENT_CYAN.is_equal_approx(Color(0.310, 0.765, 0.969)))
	_check("v2_accent_gold", Style.V2_ACCENT_GOLD.is_equal_approx(Color(1.0, 0.847, 0.290)))
	_check("v2_hp_green", Style.V2_HP_GREEN.is_equal_approx(Color(0.498, 0.824, 0.416)))
	_check("v2_warn_orange", Style.V2_WARN_ORANGE.is_equal_approx(Color(0.878, 0.663, 0.310)))
	_check("v2_danger_red", Style.V2_DANGER_RED.is_equal_approx(Color(0.851, 0.357, 0.290)))
	_check("v2_mp_blue", Style.V2_MP_BLUE.is_equal_approx(Color(0.353, 0.561, 0.878)))
	_check("v2_text_primary", Style.V2_TEXT_PRIMARY.is_equal_approx(Color(0.910, 0.894, 0.847)))
	_check("dmg_flash_token", Style.COLOR_DMG_FLASH.is_equal_approx(Color(0.8, 0, 0, 0)))
	_check("transparent_token", Style.COLOR_TRANSPARENT.is_equal_approx(Color(0, 0, 0, 0)))

	# 2) 组件禁止硬编码颜色（引用 Style.* 的行除外；backpack 待对方提交后纳入）
	var files := ["res://ui/status_bar.gd", "res://ui/item_tooltip.gd"]
	for f in files:
		var p := FileAccess.open(f, FileAccess.READ)
		if p == null:
			_check("open " + f, false)
			continue
		var bad: Array[String] = []
		var n := 0
		while not p.eof_reached():
			n += 1
			var line := p.get_line()
			if line.contains("Color(") and not line.contains("Style."):
				bad.append("%d: %s" % [n, line.strip_edges()])
		p.close()
		_check("no_hardcode_" + f.get_file(), bad.is_empty(), "; ".join(bad))

	quit(0 if _fail == 0 else 1)
