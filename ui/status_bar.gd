extends CanvasLayer
## 状态栏（UI 迁移线）：把 three.js 原型的 HUD 迁到 Godot 的代码版。
## 只消费 player.gd / gun.gd 的稳定信号（damaged/died/hp、shot/reloaded/reloading/empty/hit/ammo/reserve），
## 不改任何动画线接口；后续金币/波次/技能栏在这个文件里扩展。
## 配色/字体统一走 ui/style.gd（换肤只改那一处）。

const Style := preload("res://ui/style.gd")

const BAR_W := 220.0
const BAR_H := 16.0

var _hp_fill: ColorRect
var _hp_label: Label
var _kill_label: Label
var _ammo_label: Label
var _status_label: Label
var _hitmarker: Label
var _death_panel: VBoxContainer
var _dmgflash: ColorRect
var _theme: Theme

var _hitmark_t := 0.0
var _dmgflash_t := 0.0
var _status_t := 0.0

func _ready() -> void:
	_theme = Style.make_theme()
	_build()

func _process(delta: float) -> void:
	_hitmark_t = maxf(0.0, _hitmark_t - delta)
	_hitmarker.visible = _hitmark_t > 0.0
	_dmgflash_t = maxf(0.0, _dmgflash_t - delta)
	_dmgflash.color.a = 0.25 * (_dmgflash_t / 0.18)
	_status_t = maxf(0.0, _status_t - delta)
	_status_label.visible = _status_t > 0.0

func _build() -> void:
	# 左上：生命条（背景 + 填充 + 数值）
	var hp_bg := ColorRect.new()
	hp_bg.color = Style.COLOR_HP_BG
	hp_bg.position = Vector2(16, 12)
	hp_bg.size = Vector2(BAR_W, BAR_H)
	add_child(hp_bg)
	_hp_fill = ColorRect.new()
	_hp_fill.color = Style.COLOR_HP_HIGH
	_hp_fill.position = Vector2(18, 14)
	_hp_fill.size = Vector2(BAR_W - 4, BAR_H - 4)
	add_child(_hp_fill)
	_hp_label = _make_label("生命 100/100", Vector2(16, 34), 16, Style.COLOR_AMMO)
	_kill_label = _make_label("击杀: 0", Vector2(16, 58), 16, Style.COLOR_KILL)
	# 右下：弹药 + 状态提示
	_ammo_label = _make_label("弹药: --", Vector2.ZERO, 22, Style.COLOR_AMMO)
	_ammo_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	_ammo_label.position = Vector2(-170, -42)
	_ammo_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_status_label = _make_label("", Vector2.ZERO, 16, Style.COLOR_STATUS)
	_status_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	_status_label.position = Vector2(-170, -68)
	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_status_label.visible = false
	# 中央：准星 + 命中标记
	_center(_make_label("+", Vector2.ZERO, 26, Style.COLOR_CROSSHAIR))
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
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 40)
	title.add_theme_color_override("font_color", Style.COLOR_DEATH_TITLE)
	_death_panel.add_child(title)
	var hint := Label.new()
	hint.text = "按 R 重来"
	hint.theme = _theme
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_size_override("font_size", 18)
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
	l.add_theme_color_override("font_color", color)
	l.add_theme_font_size_override("font_size", size)
	add_child(l)
	return l

## ---- 供 main.gd 调用的公开接口（数据来自稳定信号） ----

func set_hp(hp: int, max_hp: int) -> void:
	var m := maxi(1, max_hp)
	var pct := clampf(float(hp) / float(m), 0.0, 1.0)
	_hp_fill.size.x = (BAR_W - 4) * pct
	if pct > 0.5:
		_hp_fill.color = Style.COLOR_HP_HIGH
	elif pct > 0.25:
		_hp_fill.color = Style.COLOR_HP_MID
	else:
		_hp_fill.color = Style.COLOR_HP_LOW
	_hp_label.text = "生命 %d/%d" % [maxi(0, hp), m]

func set_kills(n: int) -> void:
	_kill_label.text = "击杀: %d" % n

func set_ammo(ammo: int, reserve: int) -> void:
	_ammo_label.text = "弹药: %d/%d" % [ammo, reserve]

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
