extends CanvasLayer
## 状态栏（UI 迁移线）：把 three.js 原型的 HUD 迁到 Godot 的代码版。
## 只消费 player.gd / gun.gd 的稳定信号（damaged/died/hp、shot/reloaded/reloading/empty/hit/ammo/reserve），
## 不改任何动画线接口；后续金币/波次/技能栏在这个文件里扩展。
## 配色/字体统一走 ui/style.gd（换肤只改那一处）。

const Style := preload("res://ui/style.gd")

const BAR_W := 220.0
const BAR_H := 18.0

var _hp_fill: ColorRect
var _hp_trail: ColorRect
var _hp_label: Label
var _mp_fill: ColorRect
var _mp_label: Label
var _kill_label: Label
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

func _ready() -> void:
	_theme = Style.make_theme()
	_font_bold = Style.make_font(600)
	_font_heavy = Style.make_font(700)
	_font_regular = Style.make_font(400)
	_font_mono = Style.make_mono_font(600)
	_build()

func _process(delta: float) -> void:
	_hitmark_t = maxf(0.0, _hitmark_t - delta)
	_hitmarker.visible = _hitmark_t > 0.0
	_dmgflash_t = maxf(0.0, _dmgflash_t - delta)
	_dmgflash.color.a = 0.25 * (_dmgflash_t / 0.18)
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
		_set_crosshair(clampf(total / 0.035, 0.0, 1.0))
	# 低血量血雾呼吸
	if _low_hp and _vignette_mat != null:
		var v := 0.30 + 0.22 * (0.5 + 0.5 * sin(Time.get_ticks_msec() / 1000.0 * 2.4))
		_vignette_mat.set_shader_parameter("intensity", v)

func _build() -> void:
	# 左上：生命（图标 + 血条 + 数值）
	var hp_bg := Panel.new()
	hp_bg.position = Vector2(16, 10)
	hp_bg.size = Vector2(BAR_W, BAR_H)
	hp_bg.add_theme_stylebox_override("panel",
		Style.make_style(Style.COLOR_HP_BG, Style.COLOR_BAR_BORDER, Style.RADIUS_SM, 1))
	add_child(hp_bg)
	_hp_fill = ColorRect.new()
	_hp_fill.position = Vector2(18, 12)
	_hp_fill.size = Vector2(BAR_W - 4, BAR_H - 4)
	add_child(_hp_fill)
	_hp_trail = ColorRect.new()
	_hp_trail.color = Color(Style.COLOR_WHITE, 0.85)
	_hp_trail.position = Vector2(18, 12)
	_hp_trail.size = Vector2(BAR_W - 4, BAR_H - 4)
	_hp_trail.visible = false
	add_child(_hp_trail)
	_hp_label = _make_label("100/100", Vector2(244, 8), 22, Style.COLOR_WHITE)
	_hp_label.add_theme_font_override("font", _font_mono)
	# 左上第二行：魔力（蓝条，技能系统移植后由 set_mp 点亮）
	var mp_bg := Panel.new()
	mp_bg.position = Vector2(16, 40)
	mp_bg.size = Vector2(BAR_W, 14)
	mp_bg.add_theme_stylebox_override("panel",
		Style.make_style(Style.COLOR_HP_BG, Style.COLOR_BAR_BORDER, Style.RADIUS_SM, 1))
	add_child(mp_bg)
	_mp_fill = ColorRect.new()
	_mp_fill.color = Style.THEME_MP_BLUE
	_mp_fill.position = Vector2(18, 42)
	_mp_fill.size = Vector2(BAR_W - 4, 10)
	add_child(_mp_fill)
	_mp_label = _make_label("", Vector2(244, 37), 16, Style.THEME_MP_BLUE)
	mp_bg.visible = false
	_mp_fill.visible = false
	_mp_label.visible = false
	_kill_label = _make_label("击杀: 0", Vector2(16, 64), 16, Style.COLOR_KILL)
	_kill_label.add_theme_font_override("font", _font_mono)
	# 右下：武器名 + 弹药 + 状态提示
	_weapon_label = _make_label("AK-74", Vector2.ZERO, 14,
		Style.THEME_GRAY_LIGHT if Style.theme_active() == "gold_white_gray" else Style.COLOR_DIM_TEXT)
	_weapon_label.add_theme_font_override("font", _font_regular)
	_weapon_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	_weapon_label.offset_left = -320
	_weapon_label.offset_top = -116
	_weapon_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	var ammo_row := HBoxContainer.new()
	ammo_row.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	ammo_row.offset_left = -220
	ammo_row.offset_top = -82
	ammo_row.offset_right = -16
	ammo_row.offset_bottom = -40
	ammo_row.alignment = BoxContainer.ALIGNMENT_END
	ammo_row.add_theme_constant_override("separation", 6)
	add_child(ammo_row)
	_ammo_label = Label.new()
	_ammo_label.theme = _theme
	_ammo_label.add_theme_font_override("font", _font_mono)
	_ammo_label.add_theme_color_override("font_color", Style.COLOR_AMMO)
	_ammo_label.add_theme_font_size_override("font_size", 34)
	_ammo_label.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	ammo_row.add_child(_ammo_label)
	_ammo_reserve_label = Label.new()
	_ammo_reserve_label.theme = _theme
	_ammo_reserve_label.add_theme_font_override("font", _font_mono)
	_ammo_reserve_label.add_theme_color_override("font_color", Style.COLOR_DIM_TEXT)
	_ammo_reserve_label.add_theme_font_size_override("font_size", 16)
	_ammo_reserve_label.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	ammo_row.add_child(_ammo_reserve_label)
	_status_label = _make_label("", Vector2.ZERO, 16, Style.COLOR_STATUS)
	_status_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	_status_label.offset_left = -300
	_status_label.offset_top = -34
	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_status_label.visible = false
	# 中央：四段式准星（随扩散张开）+ 命中标记
	_ch_up = _make_crosshair_line(Vector2(0, -1))
	_ch_down = _make_crosshair_line(Vector2(0, 1))
	_ch_left = _make_crosshair_line(Vector2(-1, 0))
	_ch_right = _make_crosshair_line(Vector2(1, 0))
	_set_crosshair(0.0)
	_hitmarker = _make_label("✕", Vector2.ZERO, 30, Style.COLOR_HITMARKER)
	_center(_hitmarker)
	_hitmarker.visible = false
	# 死亡面板
	_death_panel = VBoxContainer.new()
	_death_panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_death_panel.custom_minimum_size = Vector2(320, 140)
	_death_panel.alignment = BoxContainer.ALIGNMENT_CENTER
	_death_panel.add_theme_constant_override("separation", 10)
	var title := Label.new()
	title.text = "你死了"
	title.theme = _theme
	title.add_theme_font_override("font", _font_heavy)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 40)
	title.add_theme_color_override("font_color", Style.COLOR_DEATH_TITLE)
	_death_panel.add_child(title)
	var hint := Label.new()
	hint.text = "按 R 重来"
	hint.theme = _theme
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_size_override("font_size", 16)
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

func _make_crosshair_line(dir: Vector2) -> ColorRect:
	var r := ColorRect.new()
	r.color = Style.COLOR_CROSSHAIR
	r.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	r.grow_horizontal = Control.GROW_DIRECTION_BOTH
	r.grow_vertical = Control.GROW_DIRECTION_BOTH
	add_child(r)
	return r

func _set_crosshair(ratio: float) -> void:
	_ch_gap = 4.0 + ratio * 24.0
	if _ch_up == null:
		return
	_ch_up.offset_left = -1.5
	_ch_up.offset_top = -_ch_gap - 9.0
	_ch_up.offset_right = 1.5
	_ch_up.offset_bottom = -_ch_gap
	_ch_down.offset_left = -1.5
	_ch_down.offset_top = _ch_gap
	_ch_down.offset_right = 1.5
	_ch_down.offset_bottom = _ch_gap + 9.0
	_ch_left.offset_left = -_ch_gap - 9.0
	_ch_left.offset_top = -1.5
	_ch_left.offset_right = -_ch_gap
	_ch_left.offset_bottom = 1.5
	_ch_right.offset_left = _ch_gap
	_ch_right.offset_top = -1.5
	_ch_right.offset_right = _ch_gap + 9.0
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
	var m := maxi(1, max_hp)
	var pct := clampf(float(hp) / float(m), 0.0, 1.0)
	var target_w := (BAR_W - 4) * pct
	if _hp_fill.size.x > target_w + 0.5:
		# 掉血：白色后滞条从旧值缓动到新值
		_hp_trail.size.x = _hp_fill.size.x
		_hp_trail.visible = true
		var tw := create_tween()
		tw.tween_property(_hp_trail, "size:x", target_w, 0.45) \
			.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		tw.tween_callback(func() -> void: _hp_trail.visible = false)
	_hp_fill.size.x = target_w
	if pct > 0.5:
		_hp_fill.color = Style.COLOR_HP_HIGH
	elif pct > 0.25:
		_hp_fill.color = Style.COLOR_HP_MID
	else:
		_hp_fill.color = Style.COLOR_HP_LOW
	_hp_label.text = "%d/%d" % [maxi(0, hp), m]
	_hp_label.add_theme_color_override("font_color",
		Style.THEME_DANGER_RED if pct <= 0.25 else Style.COLOR_WHITE)
	_low_hp = pct <= 0.25
	if _vignette != null:
		_vignette.visible = _low_hp
		if not _low_hp:
			_vignette_mat.set_shader_parameter("intensity", 0.0)

## 魔法值（技能系统移植后由 main 调用；首次调用点亮蓝条）
func set_mp(mp: int, max_mp: int) -> void:
	var m := maxi(1, max_mp)
	var pct := clampf(float(mp) / float(m), 0.0, 1.0)
	_mp_fill.size.x = (BAR_W - 4) * pct
	_mp_label.text = "%d/%d" % [maxi(0, mp), m]
	_mp_fill.visible = true
	_mp_label.visible = true

func set_weapon_name(name: String) -> void:
	_weapon_label.text = name

func set_kills(n: int) -> void:
	_kill_label.text = "击杀: %d" % n

func set_ammo(ammo: int, reserve: int) -> void:
	var changed := ammo != _last_ammo
	_last_ammo = ammo
	_ammo_label.text = str(maxi(0, ammo))
	_ammo_label.add_theme_color_override("font_color",
		Style.THEME_DANGER_RED if ammo <= 0 else Style.COLOR_AMMO)
	_ammo_reserve_label.text = " / %d" % maxi(0, reserve)
	if changed:
		_pulse_label(_ammo_label)

func _pulse_label(l: Label) -> void:
	var tw := create_tween()
	tw.tween_property(l, "modulate", Color(1.35, 1.35, 1.35, 1.0), 0.07)
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
	_hitmark_t = 0.12

func damage_flash() -> void:
	_dmgflash_t = 0.18

func show_death() -> void:
	_death_panel.visible = true
