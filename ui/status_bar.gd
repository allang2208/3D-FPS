extends CanvasLayer
## 状态栏（UI 迁移线）：把 three.js 原型的 HUD 迁到 Godot 的代码版。
## 只消费 player.gd / gun.gd 的稳定信号（damaged/died/hp、shot/reloaded/reloading/empty/hit/ammo/reserve），
## 不改任何动画线接口；后续金币/波次/技能栏在这个文件里扩展。
## 配色/字体统一走 ui/style.gd（换肤只改那一处）。

const Style := preload("res://ui/style.gd")

var _ammo_label: Label
var _ammo_reserve_label: Label
var _weapon_label: Label
var _status_label: Label
var _hitmarker: Label
var _death_panel: VBoxContainer
var _dmgflash: ColorRect
var _theme: Theme
var _font_bold: Font
var _font_heavy: Font
var _font_regular: Font
var _font_mono: Font

var _hitmark_t := 0.0
var _dmgflash_t := 0.0
var _status_t := 0.0
var _ch_gap := 4.0
var _last_ammo := -1
var _low_hp := false
var _vignette_mat: ShaderMaterial
var _ch_up: ColorRect
var _ch_down: ColorRect
var _ch_left: ColorRect
var _ch_right: ColorRect
var _vignette: ColorRect
var _tip: PanelContainer
var _tip_title: Label
var _tip_desc: Label
var _tip_body: VBoxContainer
var _hp_now := 0
var _hp_max := 100
var _mp_now := 0
var _mp_max := 100
var _ammo_now := 0
var _ammo_reserve := 0
var _kills := 0
var _weapon_name := ""
var _bar_w := 220.0
var _bar_h := 18.0
var _hp_cfg := {}
var _mp_cfg := {}
var _kill_cfg := {}
var _weapon_cfg := {}
var _ammo_cfg := {}
var _status_cfg := {}
var _death_cfg := {}
var _hitmark_cfg := {}
var _dmg_cfg := {}
var _cross_cfg := {}
var _vig_cfg := {}
var _labels := {}
var _top_bar: PanelContainer
var _top_name_lbl: Label
var _top_level_lbl: Label
var _top_class_lbl: Label
var _top_kills_lbl: Label
var _top_hp_fill: ColorRect
var _top_mp_fill: ColorRect
var _top_stamina_fill: ColorRect
var _exp_bar: ColorRect
var _stamina_now := 100
var _stamina_max := 100
var _exp_now := 0
var _exp_max := 100
var _buff_bar: HBoxContainer
var _buff_items := {}
var _buff_sig := ""
var _emoji_font: SystemFont

func _ready() -> void:
	_hud_cfg()
	_theme = Style.make_theme()
	_font_bold = Style.make_font(600)
	_font_heavy = Style.make_font(700)
	_font_regular = Style.make_font(400)
	_font_mono = Style.make_mono_font(600)
	_build()

## 从 style-config.json "hud" 段读取布局/字号/行为/文案（改配置不改代码）
func _hud_cfg() -> void:
	_bar_w = float(Style.hud("bar_w", 220.0))
	_bar_h = float(Style.hud("bar_h", 18.0))
	_hp_cfg = Style.hud_section("hp")
	_mp_cfg = Style.hud_section("mp")
	_kill_cfg = Style.hud_section("kill")
	_weapon_cfg = Style.hud_section("weapon")
	_ammo_cfg = Style.hud_section("ammo")
	_status_cfg = Style.hud_section("status")
	_death_cfg = Style.hud_section("death")
	_hitmark_cfg = Style.hud_section("hitmark")
	_dmg_cfg = Style.hud_section("dmgflash")
	_cross_cfg = Style.hud_section("crosshair")
	_vig_cfg = Style.hud_section("vignette")
	_labels = Style.hud_section("labels")

func _cfg_num(d: Dictionary, key: String, default: float) -> float:
	return float(d.get(key, default))

func _cfg_int(d: Dictionary, key: String, default: int) -> int:
	return int(d.get(key, default))

func _label(key: String, default: String) -> String:
	return String(_labels.get(key, default))

func _process(delta: float) -> void:
	_sync_top_bar()
	_sync_buffs()
	_hitmark_t = maxf(0.0, _hitmark_t - delta)
	_hitmarker.visible = _hitmark_t > 0.0
	_dmgflash_t = maxf(0.0, _dmgflash_t - delta)
	_dmgflash.color.a = _cfg_num(_dmg_cfg, "alpha", 0.25) * (_dmgflash_t / _cfg_num(_dmg_cfg, "ms", 0.18))
	_status_t = maxf(0.0, _status_t - delta)
	_status_label.visible = _status_t > 0.0
	# 准星随扩散张开（读 gun 的扩散状态；无枪时保持最小）
	var gun := get_tree().root.find_child("Gun", true, false) if get_tree() != null else null
	if gun != null:
		var base: float = 0.0025
		var data = gun.get("data")
		if data != null:
			base = float(data.base_spread)
		var total := base + float(gun.get("_spread")) + float(gun.get("_move_spread")) + float(gun.get("_air_spread"))
		_set_crosshair(clampf(total / _cfg_num(_cross_cfg, "max_ratio", 0.035), 0.0, 1.0))
	# 低血量血雾呼吸
	if _low_hp and _vignette_mat != null:
		var v := _cfg_num(_vig_cfg, "base", 0.30) + _cfg_num(_vig_cfg, "amp", 0.22) \
			* (0.5 + 0.5 * sin(Time.get_ticks_msec() / 1000.0 * _cfg_num(_vig_cfg, "freq", 2.4)))
		_vignette_mat.set_shader_parameter("intensity", v)

func _sync_top_bar() -> void:
	var hud := get_parent()
	var st: RefCounted = hud.get("player_status") if hud != null else null
	if st != null:
		if _top_name_lbl != null:
			_top_name_lbl.text = String(st.get("character_name"))
		if _top_level_lbl != null:
			_top_level_lbl.text = "Lv.%d" % int(st.get("level"))
		if _top_class_lbl != null:
			_top_class_lbl.text = String(st.get("character_class"))
		var sm := int(st.call("max_stamina"))
		if _stamina_now != int(st.get("stamina")) or _stamina_max != sm:
			set_stamina(int(st.get("stamina")), sm)
		var mm := int(st.call("max_mp"))
		if _mp_now != int(st.get("mp")) or _mp_max != mm:
			set_mp(int(st.get("mp")), mm)
		var em := int(st.call("max_exp"))
		if _exp_now != int(st.get("exp")) or _exp_max != em:
			set_exp(int(st.get("exp")), em)
	if _top_kills_lbl != null:
		_top_kills_lbl.text = "%d" % _kills

func _build() -> void:
	_build_tooltip()
	# 左下：武器模式 + 武器名（原项目 weapon-info，金色发光）
	var wsize := _cfg_int(_weapon_cfg, "size", 16)
	var wmode := _make_label("武器", Vector2.ZERO, 12, Style.COLOR_DIM_TEXT)
	wmode.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	wmode.offset_left = 16.0
	wmode.offset_top = -204.0
	_weapon_label = _make_label("", Vector2.ZERO, wsize, Style.THEME_GOLD)
	_weapon_label.add_theme_font_override("font", _font_bold)
	_weapon_label.add_theme_color_override("font_color", Style.THEME_GOLD)
	_weapon_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	_weapon_label.offset_left = 16.0
	_weapon_label.offset_top = -182.0
	_bind_hover(_weapon_label, _label("weapon_tip_title", "当前武器"), _label("weapon_tip_desc", "正在使用的武器。1~4 键切换，R 键换弹。"),
		func() -> Array: return [["武器", _weapon_name]])
	var ammo_row := HBoxContainer.new()
	ammo_row.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	ammo_row.offset_left = -220.0
	ammo_row.offset_top = -82.0
	ammo_row.offset_right = -16.0
	ammo_row.offset_bottom = -40.0
	ammo_row.alignment = BoxContainer.ALIGNMENT_END
	ammo_row.add_theme_constant_override("separation", 6)
	add_child(ammo_row)
	_bind_hover(ammo_row, _label("ammo_tip_title", "弹药"), _label("ammo_tip_desc", "弹匣内子弹 / 备弹。弹匣打空后自动换弹。"),
		func() -> Array: return [["弹匣", "%d" % _ammo_now], ["备弹", "%d" % _ammo_reserve]])
	_ammo_label = Label.new()
	_ammo_label.theme = _theme
	_ammo_label.add_theme_font_override("font", _font_mono)
	_ammo_label.add_theme_color_override("font_color", Style.COLOR_AMMO)
	_ammo_label.add_theme_font_size_override("font_size", _cfg_int(_ammo_cfg, "size", 34))
	_ammo_label.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	ammo_row.add_child(_ammo_label)
	_ammo_reserve_label = Label.new()
	_ammo_reserve_label.theme = _theme
	_ammo_reserve_label.add_theme_font_override("font", _font_mono)
	_ammo_reserve_label.add_theme_color_override("font_color", Style.COLOR_DIM_TEXT)
	_ammo_reserve_label.add_theme_font_size_override("font_size", _cfg_int(_ammo_cfg, "reserve_size", 16))
	_ammo_reserve_label.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	ammo_row.add_child(_ammo_reserve_label)
	_status_label = _make_label("", Vector2.ZERO, _cfg_int(_status_cfg, "size", 16), Style.COLOR_STATUS)
	_status_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	_status_label.offset_left = -300.0
	_status_label.offset_top = -34.0
	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_status_label.visible = false
	# 中央：四段式准星（随扩散张开）+ 命中标记
	_ch_up = _make_crosshair_line(Vector2(0, -1))
	_ch_down = _make_crosshair_line(Vector2(0, 1))
	_ch_left = _make_crosshair_line(Vector2(-1, 0))
	_ch_right = _make_crosshair_line(Vector2(1, 0))
	_set_crosshair(0.0)
	_hitmarker = _make_label("✕", Vector2.ZERO, _cfg_int(_hitmark_cfg, "size", 30), Style.COLOR_HITMARKER)
	_center(_hitmarker)
	_hitmarker.visible = false
	# 死亡面板
	_death_panel = VBoxContainer.new()
	_death_panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_death_panel.custom_minimum_size = Vector2(
		_cfg_int(_death_cfg, "w", 320), _cfg_int(_death_cfg, "h", 140))
	_death_panel.alignment = BoxContainer.ALIGNMENT_CENTER
	_death_panel.add_theme_constant_override("separation", 10)
	var title := Label.new()
	title.text = _label("death_title", "你死了")
	title.theme = _theme
	title.add_theme_font_override("font", _font_heavy)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", _cfg_int(_death_cfg, "title_size", 40))
	title.add_theme_color_override("font_color", Style.COLOR_DEATH_TITLE)
	_death_panel.add_child(title)
	var hint := Label.new()
	hint.text = _label("death_hint", "按 R 重来")
	hint.theme = _theme
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_size_override("font_size", _cfg_int(_death_cfg, "hint_size", 16))
	hint.add_theme_color_override("font_color", Style.COLOR_DEATH_HINT)
	_death_panel.add_child(hint)
	_death_panel.visible = false
	add_child(_death_panel)
	# 受伤红闪（全屏，最上层）
	_dmgflash = ColorRect.new()
	_dmgflash.color = Style.COLOR_DMG_FLASH
	_dmgflash.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_dmgflash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_dmgflash)
	# 低血量血雾（最上层）
	_vignette = ColorRect.new()
	_vignette.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_vignette_mat = ShaderMaterial.new()
	_vignette_mat.shader = load("res://assets/ui/shaders/health_vignette.gdshader")
	_vignette.material = _vignette_mat
	_vignette.visible = false
	add_child(_vignette)
	_build_hud_extras()
	_build_buff_bar()

## 原项目补充 HUD：顶部状态栏 / 体力条 / 经验条 / 操作提示 / 侧边菜单
func _build_hud_extras() -> void:
	_build_top_bar()
	_build_exp_bar()
	_build_controls_hint()
	_build_side_menu()


func _build_top_bar() -> void:
	_top_bar = PanelContainer.new()
	_top_bar.name = "TopBar"
	_top_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_top_bar.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_top_bar.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_top_bar.offset_top = 8
	# 原项目 top-bar 模块：深色玻璃 + 2px 边框 + 12px 圆角 + 阴影
	var tb_sb := Style.make_style(Style.COLOR_HUD_BG, Style.COLOR_HUD_BORDER, 12, 2)
	tb_sb.shadow_color = Color(Style.COLOR_BLACK, 0.35)
	tb_sb.shadow_size = 10
	tb_sb.shadow_offset = Vector2(0, 2)
	tb_sb.content_margin_left = 20
	tb_sb.content_margin_right = 20
	tb_sb.content_margin_top = 6
	tb_sb.content_margin_bottom = 6
	_top_bar.add_theme_stylebox_override("panel", tb_sb)
	add_child(_top_bar)
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 12)
	hb.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_top_bar.add_child(hb)
	# 名称 / 等级 / 职业 / 击杀：固定宽 + 居中 + 分隔线，值变化不跳动
	_top_name_lbl = _add_top_stat(hb, "名称", "character_name", false)
	_add_top_divider(hb)
	_top_level_lbl = _add_top_stat(hb, "等级", "level", false)
	_add_top_divider(hb)
	_top_class_lbl = _add_top_stat(hb, "职业", "character_class", false)
	_add_top_divider(hb)
	_top_kills_lbl = _add_top_stat(hb, "击杀", "", true)
	_add_top_divider(hb)
	# 生命 / 魔法小条（标题 + 圆角轨道 + 数值）
	var hp_box := _add_top_meter_box(hb, "生命", Style.COLOR_HP_HIGH)
	_top_hp_fill = hp_box[1]
	_add_top_divider(hb)
	var mp_box := _add_top_meter_box(hb, "魔法", Style.THEME_MP_BLUE)
	_top_mp_fill = mp_box[1]
	_add_top_divider(hb)
	var sta_box := _add_top_meter_box(hb, "体力", Style.COLOR_STAMINA_FILL)
	_top_stamina_fill = sta_box[1]


func _make_top_caption(parent: Node, text: String) -> Label:
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", 11)
	l.add_theme_color_override("font_color", Style.COLOR_HUD_DIM)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l


func _add_top_stat(parent: Node, caption: String, prop: String, mono: bool) -> Label:
	var box := VBoxContainer.new()
	box.custom_minimum_size = Vector2(52, 0)
	box.mouse_filter = Control.MOUSE_FILTER_STOP
	_make_top_caption(box, caption)
	var v := Label.new()
	v.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_theme_font_size_override("font_size", 13)
	v.add_theme_font_override("font", _font_mono if mono else _font_bold)
	v.add_theme_color_override("font_color", Style.COLOR_HUD_GOLD if mono else Style.COLOR_HUD_TEXT)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	box.add_child(v)
	var tip: String = {"名称": "角色名称", "等级": "角色等级，经验满升级", "职业": "角色职业", "击杀": "本局累计击杀"}.get(caption, "")
	box.mouse_entered.connect(func() -> void:
		_show_tooltip(caption, tip, [], box.global_position + Vector2(0, box.size.y + 6)))
	box.mouse_exited.connect(func() -> void:
		if _tip != null:
			_tip.visible = false)
	parent.add_child(box)
	return v


func _add_top_divider(parent: Node) -> void:
	var d := ColorRect.new()
	d.custom_minimum_size = Vector2(1, 24)
	d.color = Color(Style.COLOR_HUD_BORDER, 0.5)
	d.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(d)


func _add_top_meter_box(parent: Node, caption: String, color: Color) -> Array:
	var box := VBoxContainer.new()
	box.custom_minimum_size = Vector2(88, 0)
	box.mouse_filter = Control.MOUSE_FILTER_STOP
	_make_top_caption(box, caption)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	box.add_child(row)
	var fill := _make_top_meter(row, color)
	parent.add_child(box)
	box.mouse_entered.connect(func() -> void:
		var rows: Array
		var desc := "角色的生命，归零时死亡。"
		if caption == "生命":
			rows = [["当前", "%d / %d" % [_hp_now, _hp_max]]]
		elif caption == "魔法":
			rows = [["当前", "%d / %d" % [_mp_now, _mp_max]]]
			desc = "释放技能消耗的魔力，随时间自动恢复。"
		else:
			rows = [["当前", "%d / %d" % [_stamina_now, _stamina_max]]]
			desc = "冲刺、闪避、攻击消耗体力，停止消耗后自动恢复。"
		_show_tooltip(caption + "值", desc, rows,
			box.global_position + Vector2(0, box.size.y + 6)))
	box.mouse_exited.connect(func() -> void:
		if _tip != null:
			_tip.visible = false)
	return [box, fill]


func _make_top_meter(parent: Node, color: Color) -> ColorRect:
	var track := Panel.new()
	track.custom_minimum_size = Vector2(76, 10)
	track.mouse_filter = Control.MOUSE_FILTER_IGNORE
	track.add_theme_stylebox_override("panel",
		Style.make_style(Style.COLOR_HUD_TRACK, Color(Style.COLOR_HUD_BORDER, 0.6), 5, 1))
	parent.add_child(track)
	var fill := ColorRect.new()
	fill.color = color
	fill.anchor_top = 0.0
	fill.anchor_bottom = 1.0
	fill.offset_left = 1
	fill.offset_top = 1
	fill.offset_right = -1
	fill.offset_bottom = -1
	fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
	track.add_child(fill)
	return fill


func _build_exp_bar() -> void:
	var track := ColorRect.new()
	track.color = Color(Style.COLOR_HUD_BG, 0.55)
	track.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	track.offset_top = -6
	track.offset_bottom = 0
	track.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(track)
	_exp_bar = ColorRect.new()
	_exp_bar.color = Style.THEME_GOLD
	_exp_bar.anchor_top = 1.0
	_exp_bar.anchor_bottom = 1.0
	_exp_bar.offset_top = -6
	_exp_bar.offset_bottom = 0
	_exp_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_exp_bar)


func _build_controls_hint() -> void:
	var p := PanelContainer.new()
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	p.offset_left = 10
	p.offset_top = -150
	p.offset_bottom = -78
	p.add_theme_stylebox_override("panel",
		Style.make_style(Color(Style.COLOR_HUD_BG, 0.5), Color(Style.COLOR_HUD_BORDER, 0.4), 8, 1))
	add_child(p)
	var l := Label.new()
	l.text = "WASD 移动 · 左键攻击 · 空格闪避 · Shift 冲刺\n1~4 快捷栏 · Q/E/X/C 技能 · R 换弹\nTab 背包 · CapsLock 状态 · K 技能 · O 图鉴 · L 任务"
	l.add_theme_font_size_override("font_size", 11)
	l.add_theme_color_override("font_color", Color(Style.COLOR_HUD_TEXT, 0.75))
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.add_child(l)


func _build_side_menu() -> void:
	var menu := VBoxContainer.new()
	menu.mouse_filter = Control.MOUSE_FILTER_IGNORE
	menu.set_anchors_and_offsets_preset(Control.PRESET_CENTER_RIGHT)
	menu.offset_left = -86
	menu.offset_right = -14
	menu.add_theme_constant_override("separation", 8)
	add_child(menu)
	for spec in [
			["res://assets/ui/icons/user.svg", "Caps", "状态", "status"],
			["res://assets/ui/icons/backpack.svg", "Tab", "背包", "equip"],
			["res://assets/ui/icons/zap.svg", "K", "技能", "skill"],
			["res://assets/ui/icons/map.svg", "O", "图鉴", "codex"],
			["res://assets/ui/icons/flag.svg", "L", "任务", "quest"]]:
		var b := Button.new()
		b.custom_minimum_size = Vector2(72, 64)
		# 深色 HUD 模块按钮（原项目 side-menu-btn，hover 金色发光）
		b.add_theme_stylebox_override("normal",
			Style.make_style(Color(Style.COLOR_HUD_BG, 0.72), Color(Style.COLOR_HUD_BORDER, 0.6), 8, 1))
		b.add_theme_stylebox_override("hover",
			Style.make_style(Color(Style.COLOR_HUD_BG, 0.92), Style.COLOR_HUD_GOLD, 8, 1))
		b.add_theme_stylebox_override("pressed",
			Style.make_style(Color(Style.COLOR_HUD_BG, 0.95), Style.COLOR_HUD_GOLD, 8, 2))
		var vb := VBoxContainer.new()
		vb.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var icon := TextureRect.new()
		icon.texture = load(str(spec[0]))
		icon.custom_minimum_size = Vector2(30, 30)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.modulate = Style.COLOR_HUD_TEXT
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		vb.add_child(icon)
		var hint := Label.new()
		hint.text = str(spec[1])
		hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		hint.add_theme_font_override("font", _font_mono)
		hint.add_theme_font_size_override("font_size", 14)
		hint.add_theme_color_override("font_color", Style.COLOR_HUD_GOLD)
		hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
		vb.add_child(hint)
		b.add_child(vb)
		var tab := str(spec[3])
		b.pressed.connect(func() -> void: _open_hud_tab(tab))
		menu.add_child(b)

## ---------- Buff 图标栏（旧版 StatusBar：图标/名称/剩余时间/底部进度条/悬停浮窗） ----------

func _build_buff_bar() -> void:
	_emoji_font = SystemFont.new()
	_emoji_font.font_names = PackedStringArray(["Segoe UI Emoji", "Microsoft YaHei", "SimHei"])
	_buff_bar = HBoxContainer.new()
	_buff_bar.position = Vector2(16, 108)
	_buff_bar.add_theme_constant_override("separation", 6)
	_buff_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_buff_bar)

func _sync_buffs() -> void:
	var player: Node = get_tree().root.find_child("Player", true, false) if get_tree() != null else null
	if player == null or not player.has_method("buff_snapshot"):
		if _buff_bar != null and not _buff_bar.get_children().is_empty():
			_clear_buff_items()
		return
	var snap: Array = player.buff_snapshot()
	var sig := ""
	for e in snap:
		sig += "%s:%d:%d;" % [String(e["type"]), int(e["stacks"]), int(float(e["remaining_s"]) * 10.0)]
	if sig == _buff_sig:
		_update_buff_times(snap)
		return
	_clear_buff_items()
	_buff_sig = sig
	for e in snap:
		_add_buff_item(e)

func _clear_buff_items() -> void:
	if _buff_bar == null:
		return
	for ch in _buff_bar.get_children():
		_buff_bar.remove_child(ch)
		ch.queue_free()
	_buff_items.clear()
	_buff_sig = ""

func _add_buff_item(e: Dictionary) -> void:
	var raw_color := String(e.get("color", ""))
	var color: Color = Color.html(raw_color) if raw_color.is_valid_html_color() else Style.COLOR_HUD_BORDER
	var panel := Panel.new()
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	var sb := StyleBoxFlat.new()
	sb.bg_color = Style.COLOR_HUD_BG
	sb.border_color = color
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(8)
	sb.content_margin_left = 8
	sb.content_margin_right = 10
	sb.content_margin_top = 4
	sb.content_margin_bottom = 6
	panel.add_theme_stylebox_override("panel", sb)
	var row := HBoxContainer.new()
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_theme_constant_override("separation", 4)
	panel.add_child(row)
	var icon := Label.new()
	icon.text = String(e["icon"])
	icon.add_theme_font_override("font", _emoji_font)
	icon.add_theme_font_size_override("font_size", 16)
	icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(icon)
	var name_lbl := Label.new()
	var stacks_n := int(e["stacks"])
	name_lbl.text = String(e["name"]) + (" x%d" % stacks_n if stacks_n > 1 else "")
	name_lbl.add_theme_font_override("font", _font_bold)
	name_lbl.add_theme_font_size_override("font_size", 12)
	name_lbl.add_theme_color_override("font_color", Style.COLOR_HUD_TEXT)
	name_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(name_lbl)
	var time_lbl := Label.new()
	time_lbl.add_theme_font_override("font", _font_mono)
	time_lbl.add_theme_font_size_override("font_size", 11)
	time_lbl.add_theme_color_override("font_color", Style.COLOR_HUD_DIM)
	time_lbl.custom_minimum_size = Vector2(24, 0)
	time_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	time_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(time_lbl)
	var progress := ColorRect.new()
	progress.color = color
	progress.anchor_top = 1.0
	progress.anchor_bottom = 1.0
	progress.offset_top = -2
	progress.offset_bottom = 0
	progress.offset_left = 0
	progress.offset_right = 0
	progress.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(progress)
	_buff_bar.add_child(panel)
	var battle: Variant = e.get("battle_remaining")
	_buff_items[String(e["type"])] = { "time": time_lbl, "progress": progress, "dur": float(e["duration_s"]), "battle": battle != null }
	_update_buff_item(e, panel, color, battle)

func _update_buff_item(e: Dictionary, panel: Control, color: Color, battle: Variant) -> void:
	var item: Dictionary = _buff_items[String(e["type"])]
	var time_lbl: Label = item["time"]
	if battle != null:
		time_lbl.text = "%d场" % int(battle)
	else:
		var secs := int(ceil(float(e["remaining_s"])))
		time_lbl.text = "%ds" % secs
	var progress: ColorRect = item["progress"]
	var dur := float(e["duration_s"])
	if dur > 0.0 and battle == null:
		progress.anchor_right = clampf(float(e["remaining_s"]) / dur, 0.0, 1.0)
	else:
		progress.anchor_right = 0.0
	# 悬停浮窗（旧版 StatusBar tooltip：名称/描述/层数/剩余时间）
	var rows: Array = []
	var stacks_n := int(e["stacks"])
	if stacks_n > 1:
		rows.append(["层数", "x%d" % stacks_n])
	rows.append(["剩余", "%d 秒" % int(ceil(float(e["remaining_s"]))) if battle == null else "%d 场" % int(battle)])
	panel.mouse_entered.connect(func() -> void:
		_show_tooltip(String(e["icon"]) + " " + String(e["name"]), String(e["desc"]), rows,
			panel.global_position + Vector2(0, panel.size.y + 6)))
	panel.mouse_exited.connect(func() -> void:
		if _tip != null:
			_tip.visible = false)

func _update_buff_times(snap: Array) -> void:
	for e in snap:
		var type := String(e["type"])
		if not _buff_items.has(type):
			continue
		var item: Dictionary = _buff_items[type]
		var battle: Variant = e.get("battle_remaining")
		var time_lbl: Label = item["time"]
		if battle != null:
			time_lbl.text = "%d场" % int(battle)
		else:
			time_lbl.text = "%ds" % int(ceil(float(e["remaining_s"])))
		var progress: ColorRect = item["progress"]
		var dur := float(e["duration_s"])
		progress.anchor_right = clampf(float(e["remaining_s"]) / dur, 0.0, 1.0) if dur > 0.0 and battle == null else 0.0


func _open_hud_tab(tab: String) -> void:
	var hud := get_parent()
	var bph: Control = hud.get("backpack_hud") if hud != null else null
	if bph == null:
		return
	if tab in ["status", "equip", "skill", "codex"]:
		bph.set_panel_open(true)
		bph.set_tab(tab)
	else:
		show_status("%s 系统未移植" % tab, 1.5)


func _make_crosshair_line(dir: Vector2) -> ColorRect:
	var r := ColorRect.new()
	r.color = Style.COLOR_CROSSHAIR
	r.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	r.grow_horizontal = Control.GROW_DIRECTION_BOTH
	r.grow_vertical = Control.GROW_DIRECTION_BOTH
	add_child(r)
	return r

## ---------- HUD 解释浮窗（源项目状态栏 hover 说明） ----------

func _build_tooltip() -> void:
	_tip = PanelContainer.new()
	_tip.visible = false
	_tip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_tip.z_index = 100
	var sb := Style.make_style(Style.COLOR_TT_BG, Style.COLOR_TT_BORDER, 8, 2)
	sb.shadow_color = Style.COLOR_TT_SHADOW
	sb.shadow_size = 12
	sb.shadow_offset = Vector2(0, 4)
	_tip.add_theme_stylebox_override("panel", sb)
	add_child(_tip)
	var m := MarginContainer.new()
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	m.add_theme_constant_override("margin_left", 12)
	m.add_theme_constant_override("margin_right", 12)
	m.add_theme_constant_override("margin_top", 10)
	m.add_theme_constant_override("margin_bottom", 10)
	_tip.add_child(m)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	m.add_child(v)
	_tip_title = Label.new()
	_tip_title.add_theme_font_override("font", Style.tt_font_title())
	_tip_title.add_theme_font_size_override("font_size", Style.tt_size_title())
	_tip_title.add_theme_color_override("font_color", Style.COLOR_TT_NAME)
	v.add_child(_tip_title)
	_tip_desc = Label.new()
	_tip_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_tip_desc.custom_minimum_size = Vector2(200, 0)
	_tip_desc.add_theme_font_override("font", Style.tt_font_body())
	_tip_desc.add_theme_font_size_override("font_size", Style.tt_size_body())
	_tip_desc.add_theme_color_override("font_color", Style.COLOR_TT_DESC)
	v.add_child(_tip_desc)
	_tip_body = VBoxContainer.new()
	_tip_body.add_theme_constant_override("separation", 2)
	v.add_child(_tip_body)

func _bind_hover(target: Control, title: String, desc: String, rows: Callable) -> void:
	target.mouse_filter = Control.MOUSE_FILTER_STOP
	target.mouse_entered.connect(func() -> void:
		_show_tooltip(title, desc, rows.call(), target.global_position + Vector2(0, target.size.y + 6)))
	target.mouse_exited.connect(func() -> void:
		if _tip != null:
			_tip.visible = false)

func _show_tooltip(title: String, desc: String, rows: Array, at: Vector2) -> void:
	if _tip == null:
		return
	_tip_title.text = title
	_tip_desc.text = desc
	for c in _tip_body.get_children():
		c.queue_free()
	for row in rows:
		var r := HBoxContainer.new()
		r.add_theme_constant_override("separation", 12)
		var n := Label.new()
		n.text = String(row[0])
		n.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		n.add_theme_font_override("font", Style.tt_font_body())
		n.add_theme_font_size_override("font_size", Style.tt_size_body())
		n.add_theme_color_override("font_color", Style.COLOR_TT_TYPE)
		r.add_child(n)
		var vv := Label.new()
		vv.text = String(row[1])
		vv.add_theme_font_override("font", Style.tt_font_value())
		vv.add_theme_font_size_override("font_size", Style.tt_size_value())
		vv.add_theme_color_override("font_color", Style.COLOR_TT_VAL)
		r.add_child(vv)
		_tip_body.add_child(r)
	_tip.visible = true
	_place_tooltip(at)

func _place_tooltip(at: Vector2) -> void:
	var ts := _tip.get_combined_minimum_size()
	var vp := get_viewport().get_visible_rect().size
	var pos := at + Vector2(0, 6)
	if pos.y + ts.y > vp.y - 8:
		pos.y = at.y - ts.y - 6
	if pos.x + ts.x > vp.x - 8:
		pos.x = vp.x - ts.x - 8
	pos.x = maxf(8, pos.x)
	pos.y = maxf(8, pos.y)
	_tip.position = pos

func _set_crosshair(ratio: float) -> void:
	var gap0 := _cfg_num(_cross_cfg, "gap", 4.0)
	var spread := _cfg_num(_cross_cfg, "spread", 24.0)
	var len := _cfg_num(_cross_cfg, "len", 9.0)
	var thick := _cfg_num(_cross_cfg, "thick", 1.5)
	_ch_gap = gap0 + ratio * spread
	if _ch_up == null:
		return
	_ch_up.offset_left = -thick
	_ch_up.offset_top = -_ch_gap - len
	_ch_up.offset_right = thick
	_ch_up.offset_bottom = -_ch_gap
	_ch_down.offset_left = -thick
	_ch_down.offset_top = _ch_gap
	_ch_down.offset_right = thick
	_ch_down.offset_bottom = _ch_gap + len
	_ch_left.offset_left = -_ch_gap - len
	_ch_left.offset_top = -thick
	_ch_left.offset_right = -_ch_gap
	_ch_left.offset_bottom = thick
	_ch_right.offset_left = _ch_gap
	_ch_right.offset_top = -thick
	_ch_right.offset_right = _ch_gap + len

## ADS 时隐藏准星（main.gd _on_ads_changed 调用）
func set_crosshair_visible(v: bool) -> void:
	_ch_up.visible = v
	_ch_down.visible = v
	_ch_left.visible = v
	_ch_right.visible = v
	_ch_right.offset_bottom = 1.5

func _center(c: Label) -> void:
	c.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	c.grow_horizontal = Control.GROW_DIRECTION_BOTH
	c.grow_vertical = Control.GROW_DIRECTION_BOTH
	c.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	c.vertical_alignment = VERTICAL_ALIGNMENT_CENTER

func _make_label(text: String, pos: Vector2, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.position = pos
	l.theme = _theme
	l.add_theme_font_override("font", _font_bold)
	l.add_theme_color_override("font_color", color)
	l.add_theme_font_size_override("font_size", size)
	add_child(l)
	return l

## ---- 供 main.gd 调用的公开接口（数据来自稳定信号） ----

func set_hp(hp: int, max_hp: int) -> void:
	_hp_now = maxi(0, hp)
	_hp_max = maxi(1, max_hp)
	var m := maxi(1, max_hp)
	var pct := clampf(float(hp) / float(m), 0.0, 1.0)
	var low_ratio := _cfg_num(_hp_cfg, "low_ratio", 0.25)
	if _top_hp_fill != null:
		_top_hp_fill.anchor_right = pct
		_top_hp_fill.color = Style.COLOR_HP_HIGH if pct > 0.5 \
			else (Style.COLOR_HP_MID if pct > low_ratio else Style.COLOR_HP_LOW)
	_low_hp = pct <= low_ratio
	if _vignette != null:
		_vignette.visible = _low_hp
		if not _low_hp:
			_vignette_mat.set_shader_parameter("intensity", 0.0)

## 魔法值（技能系统移植后由 main 调用；首次调用点亮蓝条）
func set_mp(mp: int, max_mp: int) -> void:
	_mp_now = maxi(0, mp)
	_mp_max = maxi(1, max_mp)
	var m := maxi(1, max_mp)
	var pct := clampf(float(mp) / float(m), 0.0, 1.0)
	if _top_mp_fill != null:
		_top_mp_fill.anchor_right = pct

func set_weapon_name(name: String) -> void:
	_weapon_name = name
	_weapon_label.text = name

func set_kills(n: int) -> void:
	_kills = maxi(0, n)

func set_ammo(ammo: int, reserve: int) -> void:
	_ammo_now = maxi(0, ammo)
	_ammo_reserve = maxi(0, reserve)
	var changed := ammo != _last_ammo
	_last_ammo = ammo
	_ammo_label.text = str(maxi(0, ammo))
	_ammo_label.add_theme_color_override("font_color",
		Style.THEME_DANGER_RED if ammo <= 0 else Style.COLOR_AMMO)
	_ammo_reserve_label.text = " / %d" % maxi(0, reserve)
	if changed:
		_pulse_label(_ammo_label)

func set_stamina(st: int, max_st: int) -> void:
	_stamina_now = maxi(0, st)
	_stamina_max = maxi(1, max_st)
	if _top_stamina_fill != null:
		_top_stamina_fill.anchor_right = clampf(float(_stamina_now) / float(_stamina_max), 0.0, 1.0)

func set_exp(v: int, max_v: int) -> void:
	_exp_now = maxi(0, v)
	_exp_max = maxi(1, max_v)
	if _exp_bar != null:
		_exp_bar.anchor_right = clampf(float(_exp_now) / float(_exp_max), 0.0, 1.0)

func _pulse_label(l: Label) -> void:
	var tw := create_tween()
	tw.tween_property(l, "modulate",
		Color(Style.THEME_WHITE.r * 1.35, Style.THEME_WHITE.g * 1.35, Style.THEME_WHITE.b * 1.35, 1.0), 0.07)
	tw.tween_property(l, "modulate", Color.WHITE, 0.12)

func show_status(text: String, duration: float) -> void:
	_status_label.text = text
	_status_t = duration
	_status_label.visible = true

func clear_status() -> void:
	_status_t = 0.0
	_status_label.visible = false

func hitmark() -> void:
	_hitmarker.visible = true
	_hitmark_t = _cfg_num(_hitmark_cfg, "ms", 0.12)

func damage_flash() -> void:
	_dmgflash_t = _cfg_num(_dmg_cfg, "ms", 0.18)

func show_death() -> void:
	_death_panel.visible = true
