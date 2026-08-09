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
	# 1) DESIGN.md 关键 Token 对齐（以 DESIGN.md 的十六进制色值为真源，经 palette.json 加载）
	_check("theme_bg", Style.THEME_BG.is_equal_approx(Style._hex_to_color("#0F0F10")))
	_check("theme_gold", Style.THEME_GOLD.is_equal_approx(Style._hex_to_color("#D4AF37")))
	_check("theme_white", Style.THEME_WHITE.is_equal_approx(Style._hex_to_color("#FFFFFF")))
	_check("theme_gray_light", Style.THEME_GRAY_LIGHT.is_equal_approx(Style._hex_to_color("#B5B5B5")))
	_check("theme_gray_mid", Style.THEME_GRAY_MID.is_equal_approx(Style._hex_to_color("#3A3A3C")))
	_check("theme_hp_green", Style.THEME_HP_GREEN.is_equal_approx(Style._hex_to_color("#7FD26A")))
	_check("theme_warn_orange", Style.THEME_WARN_ORANGE.is_equal_approx(Style._hex_to_color("#E0A94F")))
	_check("theme_danger_red", Style.THEME_DANGER_RED.is_equal_approx(Style._hex_to_color("#D95B4A")))
	_check("theme_mp_blue", Style.THEME_MP_BLUE.is_equal_approx(Style._hex_to_color("#5A8FE0")))
	_check("theme_btn_hover", Style.THEME_BTN_HOVER_BG.is_equal_approx(Style._hex_to_color("#D4AF37")))
	_check("theme_progress_fill", Style.THEME_PROGRESS_FILL.is_equal_approx(Style._hex_to_color("#D4AF37")))
	_check("transparent_token", Style.COLOR_TRANSPARENT.is_equal_approx(Style._hex_to_color("#00000000")))

	# 1b) ui/palette.json 是色值真源：存在、可解析、关键 Token 齐全、加载后与 Style 当前值一致
	var pf := FileAccess.open("res://ui/palette.json", FileAccess.READ)
	_check("palette_json_exists", pf != null)
	if pf != null:
		var parsed = JSON.parse_string(pf.get_as_text())
		var pal: Dictionary = parsed if typeof(parsed) == TYPE_DICTIONARY else {}
		_check("palette_json_parse", typeof(parsed) == TYPE_DICTIONARY)
		var colors: Dictionary = pal.get("colors", {})
		for key in ["THEME_BG", "THEME_GOLD", "THEME_WHITE", "THEME_GRAY_LIGHT", "THEME_GRAY_MID",
				"THEME_HP_GREEN", "THEME_WARN_ORANGE", "THEME_DANGER_RED", "THEME_MP_BLUE",
				"COLOR_HP_BG", "COLOR_TT_BG"]:
			_check("palette_has_" + key, colors.has(key))
		var loaded_gold := Style._hex_to_color(str(colors.get("THEME_GOLD", "#000000")))
		_check("palette_loaded_eq_style", loaded_gold.is_equal_approx(Style.THEME_GOLD))

	# 1c) ui/style-config.json：风格配置存在、可解析、关键字段生效
	var cf := FileAccess.open("res://ui/style-config.json", FileAccess.READ)
	_check("style_config_exists", cf != null)
	if cf != null:
		var cparsed = JSON.parse_string(cf.get_as_text())
		var cfg: Dictionary = cparsed if typeof(cparsed) == TYPE_DICTIONARY else {}
		_check("style_config_parse", typeof(cparsed) == TYPE_DICTIONARY)
		_check("config_theme_valid", Style.theme_active() in ["dark_gold", "gold_white_gray"])
		_check("config_radius", Style.RADIUS == 8)
		_check("config_spacing_grid", Style.spacing("grid") == 4)
		_check("config_font_h1", Style.font_size("h1") == 48)
		_check("config_font_weight_heavy", Style.font_weight("heavy") == 700)
		_check("config_motion", absf(Style.MOTION_DURATION - 0.2) < 0.001)

	# 1d) 金白主题预设生效（active_theme=gold_white_gray 时组件消费的 COLOR_* 已被 THEME_* 覆盖）
	if Style.theme_active() == "gold_white_gray":
		_check("preset_text_white", Style.COLOR_TEXT.is_equal_approx(Style.THEME_WHITE))
		_check("preset_hp_green", Style.COLOR_HP_HIGH.is_equal_approx(Style.THEME_HP_GREEN))
		_check("preset_border_gold", Style.COLOR_BAR_BORDER.is_equal_approx(Style.THEME_GOLD))
		_check("preset_panel_dark", Style.COLOR_PANEL_BG.r < 0.15)
		_check("preset_dmg_flash", Style.COLOR_DMG_FLASH.is_equal_approx(Color(Style.THEME_DANGER_RED, 0.0)))
	else:
		_check("preset_dark_gold_default", Style.COLOR_TEXT.is_equal_approx(Style._hex_to_color("#d4c5a9")))
		_check("dmg_flash_token", Style.COLOR_DMG_FLASH.is_equal_approx(Style._hex_to_color("#CC000000")))

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
