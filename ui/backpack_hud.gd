extends Control
## 背包/装备 HUD（从旧 2D 项目 QuickBar + EquipManager 装备背包页迁移到 Godot 4）
##
## 布局（全部代码构建，遵循项目"少手写 .tscn"约定）：
## - 底部快捷栏：1~4 号槽（旧版 itemGroup），数字键/左键使用，拖拽绑定/交换
## - Tab / B：装备与背包面板（旧版 gear-layout）：
##   左 = 装备栏 3x5（15 槽，竖排稀有度/已强化/已改造/已附魔徽章/双手锁定）
##   右 = 背包 6x6（36 格）
## - 右键背包格 = 使用消耗品；右键装备槽 = 卸下；拖拽 = 装备/卸下/交换/绑定
##
## 复刻的旧版弹出效果与格式：
## - 面板右侧滑入 + 遮罩淡入 + 毛玻璃背景
## - 新物品 equipPop、装备 equipFlash、数字键闪烁、0 数量抖动、冷却遮罩
## - 悬停/拖拽高亮、物品浮窗（主信息+改造+附魔三段式）、背包已满提示

signal player_healed(hp: int)
signal skill_triggered(skill_id: String, phase: String)

const BackpackScript := preload("res://ui/backpack.gd")
const EquipmentScript := preload("res://ui/equipment.gd")
const Style := preload("res://ui/style.gd")
const ItemTooltipScript := preload("res://ui/item_tooltip.gd")
const StatusPageScript := preload("res://ui/status_page.gd")
const SkillBarScript := preload("res://ui/skillbar.gd")
const SkillPageScript := preload("res://ui/skill_page.gd")
const PANEL_BLUR_SHADER := preload("res://assets/ui/shaders/panel_blur.gdshader")

const HOTBAR_SIZE := 4
const SKILL_SIZE := 4
const SKILL_KEY_HINTS := ["Q", "E", "X", "C"]
const SKILL_KEYCODES := [KEY_Q, KEY_E, KEY_X, KEY_C]
# 旧版技能位配色（quick-slot.skill：#6b5d4f / #3d342b；待 palette.json 落地后并入 style.gd）
const COLOR_SKILL_SLOT_BG := Color(0.2392, 0.2039, 0.1686)
const COLOR_SKILL_SLOT_BORDER := Color(0.4196, 0.3647, 0.3098)
const INV_COLS := 5
const HOTBAR_SLOT := 52
const CELL_SLOT := 60
const EQUIP_SLOT_SIZE := Vector2(250, 84)
const EQUIP_COLS := 3
const BAR_PAD := 8
const BAR_GAP := 8
const PANEL_MARGIN := 12
const PANEL_W_RATIO := 0.45

const EQUIP_SLOT_LABELS := {
	"earring": "左耳环", "helmet": "头盔", "ring1": "右耳环", "gloves": "手套",
	"necklace": "项链", "cloak": "披风", "weapon": "主手武器1", "armor": "铠甲",
	"offhand": "副手武器1", "weapon2": "主手武器2", "belt": "腰带", "ring2": "副手武器2",
	"extra": "额外物品", "boots": "靴子", "backpack": "背包装备",
}

var backpack: BackpackScript
var equipment: EquipmentScript
var skillbar: SkillBarScript
var _player_status: RefCounted

var _hotbar_root: HBoxContainer
var _hotbar_slots: Array = []
var _skill_slots: Array = []
var _special_slot: Control
var _skill_cd_last := {}
var _grid: GridContainer
var _cells: Array = []
var _equip_grid: GridContainer
var _equip_cells := {}
var _panel_title: Label
var _tab_status: Button
var _tab_equip: Button
var _tab_skill: Button
var _page_stack: Control
var _equip_page: VBoxContainer
var _status_page: Control
var _skill_page: Control
var _current_tab := "equip"
var _panel_root: Control
var _panel: PanelContainer
var _panel_w := 720.0
var _panel_anim: Tween
var _panel_open := false
var _count_label: Label
var _status_label: Label
var _notice_label: Label
var _status_timer: Timer
var _notice_tween: Tween
var _drag_clear_timer: Timer
var _tooltip: Control
var _tooltip_tween: Tween
var _font_title: Font
var _font_section: Font
var _font_mono: Font
var _tex_cache := {}
var _cd_last := {}
var _hovered_cell := -1
var _hovered_hotbar := -1
var _hovered_equip := ""
var _drag_over_cell := -1
var _drag_over_hotbar := -1
var _drag_over_equip := ""

var _s_hotbar_empty: StyleBoxFlat
var _s_hotbar_item: StyleBoxFlat
var _s_hotbar_hover: StyleBoxFlat
var _s_skill_empty: StyleBoxFlat
var _s_cell_empty: StyleBoxFlat
var _s_cell_item: StyleBoxFlat
var _s_cell_hover: StyleBoxFlat
var _s_cell_drag_over: StyleBoxFlat
var _s_equip_empty: StyleBoxFlat
var _s_equip_equipped: StyleBoxFlat
var _s_equip_hover: StyleBoxFlat
var _s_equip_locked: StyleBoxFlat

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_panel_w = get_viewport_rect().size.x * PANEL_W_RATIO
	theme = Style.make_theme()
	_font_title = Style.make_font(700)
	_font_section = Style.make_font(400)
	_font_mono = Style.make_mono_font(600)
	_s_hotbar_empty = Style.make_style(Style.COLOR_SLOT_BG, Style.COLOR_SLOT_BORDER, 8, 2)
	_s_hotbar_item = Style.make_style(Style.COLOR_ITEM_BG, Style.COLOR_ITEM_BORDER, 8, 2)
	_s_hotbar_hover = Style.make_style(Style.COLOR_SLOT_HOVER_BG, Style.COLOR_SLOT_HOVER_BORDER, 8, 2)
	_s_skill_empty = Style.make_style(COLOR_SKILL_SLOT_BG, COLOR_SKILL_SLOT_BORDER, 8, 2)
	_s_cell_empty = Style.make_style(Style.COLOR_SLOT_BG, Style.COLOR_SLOT_BORDER, 8, 2)
	_s_cell_item = Style.make_style(Style.COLOR_ITEM_BG, Style.COLOR_ITEM_BORDER, 8, 2)
	_s_cell_hover = Style.make_style(Style.COLOR_SLOT_HOVER_BG, Style.COLOR_SLOT_HOVER_BORDER, 8, 2)
	_s_cell_drag_over = Style.make_style(Style.COLOR_DRAG_OVER_BG, Style.COLOR_DRAG_OVER_BORDER, 8, 2)
	_s_equip_empty = Style.make_style(Style.COLOR_EQUIP_SLOT_BG, Style.COLOR_EQUIP_SLOT_BORDER, 8, 2)
	_s_equip_equipped = Style.make_style(Style.COLOR_EQUIP_EQUIPPED_BG, Style.COLOR_EQUIP_EQUIPPED_BORDER, 8, 2)
	_s_equip_hover = Style.make_style(Style.COLOR_SLOT_HOVER_BG, Style.COLOR_SLOT_HOVER_BORDER, 8, 2)
	_s_equip_locked = Style.make_style(Style.COLOR_EQUIP_LOCKED_BG, Style.COLOR_EQUIP_LOCKED_BORDER, 8, 2)
	_build_status_label()
	_status_timer = Timer.new()
	_status_timer.one_shot = true
	_status_timer.timeout.connect(func() -> void: _status_label.visible = false)
	add_child(_status_timer)
	_drag_clear_timer = Timer.new()
	_drag_clear_timer.one_shot = true
	_drag_clear_timer.timeout.connect(_clear_all_drag_over)
	add_child(_drag_clear_timer)
	_build_hotbar()
	_build_panel()
	_build_tooltip()
	_build_notice()

func setup(bp: BackpackScript, eq: EquipmentScript, st: RefCounted = null, sb: SkillBarScript = null) -> void:
	backpack = bp
	equipment = eq
	skillbar = sb
	_player_status = st
	backpack.changed.connect(_refresh)
	backpack.item_added.connect(_on_item_added)
	backpack.bound.connect(_on_bound)
	if equipment != null:
		equipment.changed.connect(_refresh_equip)
		equipment.equipped.connect(_on_equipped)
	if st != null:
		_status_page = StatusPageScript.new()
		_status_page.name = "StatusPage"
		_status_page.visible = false
		_status_page.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		_page_stack.add_child(_status_page)
		_status_page.setup(st)
	if skillbar != null:
		skillbar.changed.connect(_refresh_skill_slots)
		_refresh_skill_slots()
		_skill_page = SkillPageScript.new()
		_skill_page.name = "SkillPage"
		_skill_page.visible = false
		_skill_page.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		_page_stack.add_child(_skill_page)
		_skill_page.setup(skillbar)
	set_tab("equip")
	_refresh()

## ---------- 数据变化刷新 ----------

func _refresh() -> void:
	if backpack == null:
		return
	_refresh_hotbar()
	_refresh_grid()
	_refresh_equip()
	if _count_label != null:
		_count_label.text = "%d/%d" % [backpack.item_count(), backpack.max_slots]

func _refresh_hotbar() -> void:
	for i in _hotbar_slots.size():
		var slot: HotbarSlot = _hotbar_slots[i]
		var item := backpack.resolve_hotbar(i)
		var icon := slot.get_node("Content/Icon") as TextureRect
		var stack := slot.get_node("Content/Stack") as Label
		if item.is_empty():
			icon.texture = null
			stack.text = ""
			slot.add_theme_stylebox_override("panel", _s_hotbar_hover if i == _hovered_hotbar else _s_hotbar_empty)
			slot.tooltip_text = ""
		else:
			icon.texture = _icon_tex(String(item.get("icon", "")))
			var count: int = item.get("stack", 0)
			stack.text = str(count)
			stack.add_theme_color_override("font_color", Style.COLOR_ZERO_TEXT if count <= 0 else Style.COLOR_TEXT)
			stack.add_theme_font_override("font", _font_mono)
			slot.add_theme_stylebox_override("panel", _s_hotbar_hover if i == _hovered_hotbar else _s_hotbar_item)
			slot.tooltip_text = ""

func _refresh_grid() -> void:
	for i in _cells.size():
		var cell: BackpackCell = _cells[i]
		var icon := cell.get_node("Content/Icon") as TextureRect
		var fallback := cell.get_node("Content/Fallback") as Label
		var name_lbl := cell.get_node("Content/Name") as Label
		var stack_lbl := cell.get_node("Content/Stack") as Label
		var rarity_lbl := cell.get_node("Content/Rarity") as Label
		if backpack.slots[i] == null:
			icon.texture = null
			fallback.visible = false
			name_lbl.text = ""
			stack_lbl.text = ""
			rarity_lbl.text = ""
			rarity_lbl.remove_theme_stylebox_override("normal")
			cell.add_theme_stylebox_override("panel", _s_cell_hover if i == _hovered_cell else _s_cell_empty)
		else:
			var item: Dictionary = backpack.slots[i]
			_set_icon(icon, fallback, item)
			name_lbl.text = String(item.get("name", ""))
			var count: int = item.get("stack", 1)
			stack_lbl.text = str(count) if count > 1 else ""
			var rarity_key := String(item.get("rarity", "common"))
			rarity_lbl.text = _vertical_text(Style.rarity_label(rarity_key))
			rarity_lbl.add_theme_stylebox_override("normal", Style.make_style(Style.RARITY_BADGE_COLORS.get(rarity_key, Color.GRAY), Color(0, 0, 0, 0), 3, 0))
			cell.add_theme_stylebox_override("panel", _s_cell_drag_over if i == _drag_over_cell else (_s_cell_hover if i == _hovered_cell else _s_cell_item))

func _refresh_equip() -> void:
	if equipment == null:
		return
	for key in equipment.SLOT_ORDER:
		if not _equip_cells.has(key):
			continue
		var cell: EquipSlot = _equip_cells[key]
		var item: Dictionary = equipment.get_item(key)
		var icon := cell.get_node("Content/Icon") as TextureRect
		var fallback := cell.get_node("Content/Fallback") as Label
		var name_lbl := cell.get_node("Content/Name") as Label
		var rarity_lbl := cell.get_node("Content/Rarity") as Label
		var badges := cell.get_node("Content/Badges") as VBoxContainer
		var lock := cell.get_node("Content/Lock") as Control
		var locked := equipment.is_locked(key)
		lock.visible = locked
		var hover: bool = key == _hovered_equip and not locked
		if locked:
			cell.add_theme_stylebox_override("panel", _s_equip_locked)
		elif item.is_empty():
			cell.add_theme_stylebox_override("panel", _s_equip_hover if hover else _s_equip_empty)
		else:
			cell.add_theme_stylebox_override("panel", _s_equip_hover if hover else _s_equip_equipped)
		if item.is_empty():
			icon.texture = null
			fallback.visible = false
			name_lbl.text = String(EQUIP_SLOT_LABELS.get(key, key))
			name_lbl.add_theme_color_override("font_color", Style.COLOR_DIM_TEXT)
			rarity_lbl.text = ""
			rarity_lbl.remove_theme_stylebox_override("normal")
			_set_badges(badges, {})
		else:
			_set_icon(icon, fallback, item)
			name_lbl.text = String(item.get("name", ""))
			name_lbl.add_theme_color_override("font_color", Style.COLOR_WHITE)
			var rarity_key := String(item.get("rarity", "common"))
			rarity_lbl.text = _vertical_text(Style.rarity_label(rarity_key))
			rarity_lbl.add_theme_stylebox_override("normal", Style.make_style(Style.RARITY_BADGE_COLORS.get(rarity_key, Color.GRAY), Color(0, 0, 0, 0), 3, 0))
			_set_badges(badges, item)

## ---------- 输入 ----------

## 面板开关键放 _input（早于 GUI 焦点导航，Tab 不会被焦点吃掉；K 对齐旧版技能体系键）
func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_TAB:
				get_viewport().set_input_as_handled()
				if _panel_open and _current_tab == "equip":
					set_panel_open(false)
				else:
					set_tab("equip")
					set_panel_open(true)
			KEY_K:
				get_viewport().set_input_as_handled()
				set_tab("skill")
				set_panel_open(true)
			KEY_B:
				get_viewport().set_input_as_handled()
				toggle_panel()
			KEY_CAPSLOCK:
				get_viewport().set_input_as_handled()
				set_tab("status")
				set_panel_open(true)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_1, KEY_2, KEY_3, KEY_4:
				use_hotbar(event.keycode - KEY_1)
			KEY_Q, KEY_E, KEY_X, KEY_C:
				use_skill_slot(SKILL_KEYCODES.find(event.keycode))
			KEY_ESCAPE:
				if _tooltip != null and _tooltip.visible:
					hide_tooltip()
				elif _panel_open:
					set_panel_open(false)
	elif event is InputEventMouseButton and event.pressed:
		if _tooltip != null and _tooltip.is_pinned():
			var m := get_viewport().get_mouse_position()
			if not _tooltip.get_global_rect().has_point(m):
				hide_tooltip()

func use_hotbar(index: int) -> void:
	if backpack == null or _panel_open:
		return
	var player := _get_player()
	if player == null or bool(player.get("is_dead")):
		return
	var item := backpack.resolve_hotbar(index)
	if item.is_empty():
		return
	if int(item.get("stack", 0)) <= 0:
		_shake_hotbar(index)
		return
	var result := backpack.use_hotbar(index, player)
	if result.get("ok", false):
		_notify_heal(player)
	else:
		_flash_status(String(result.get("message", "")))

func on_skill_click(_key: String) -> void:
	if _panel_open:
		return
	if skillbar == null:
		_flash_status("技能未移植")
		return
	var index := SKILL_KEY_HINTS.find(_key)
	use_skill_slot(index)

## 技能位触发（旧版 useSlot 技能侧：冷却/法杖门槛判定，通过后设冷却）
func use_skill_slot(index: int) -> void:
	if _panel_open or index < 0 or index >= SKILL_SIZE:
		return
	var key_name: String = SKILL_KEY_HINTS[index]
	_pulse_skill_slot(index)
	if skillbar == null:
		_flash_status("技能未移植（%s）" % key_name)
		return
	var r := skillbar.trigger(index, _player_status)
	var msg := String(r.get("reason", ""))
	if msg == "空槽":
		msg = "技能未移植（%s）" % key_name
	if bool(r.get("ok", false)):
		var skill_id := String(r.get("skill_id", ""))
		var phase := String(r.get("phase", "cast"))
		var def: Dictionary = skillbar.skills.get(skill_id, {})
		msg = "凝聚 %s（%s）" % [String(def.get("name", skill_id)), key_name] if phase == "spawn" \
			else "投掷 %s（%s）" % [String(def.get("name", skill_id)), key_name]
		if skill_id != "":
			skill_triggered.emit(skill_id, phase)
	_flash_status(msg)

## 技能键按下反馈：槽位大脉冲 + 金色边框闪（无技能时也让玩家看到按键生效）
func _pulse_skill_slot(index: int) -> void:
	if index < 0 or index >= _skill_slots.size():
		return
	var slot: SkillSlot = _skill_slots[index]
	slot.pivot_offset = Vector2(HOTBAR_SLOT, HOTBAR_SLOT) * 0.5
	var tw := create_tween()
	tw.tween_property(slot, "scale", Vector2(1.25, 1.25), 0.1)
	tw.tween_property(slot, "scale", Vector2.ONE, 0.18).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	slot.add_theme_stylebox_override("panel", Style.make_style(Style.COLOR_SKILL_SLOT_BG, Style.THEME_GOLD, Style.RADIUS_SM, 2))
	tw.tween_callback(func() -> void:
		slot.add_theme_stylebox_override("panel", _s_skill_empty))

func on_skill_hover(enter: bool, key: String) -> void:
	for s in _skill_slots:
		if String(s.key) == key:
			s.add_theme_stylebox_override("panel", _s_hotbar_hover if enter else _s_skill_empty)

## 技能槽刷新（旧版 _updateSlot：图标/灰化/冷却遮罩）
func _refresh_skill_slots() -> void:
	if skillbar == null:
		return
	for i in _skill_slots.size():
		var slot: SkillSlot = _skill_slots[i]
		var icon := slot.get_node("Content/Icon") as TextureRect
		var dim := slot.get_node("Content/Dim") as ColorRect
		var id := skillbar.resolve(i)
		if id == "":
			icon.texture = null
			dim.visible = false
			slot.add_theme_stylebox_override("panel", _s_skill_empty)
		else:
			var def: Dictionary = skillbar.skills.get(id, {})
			icon.texture = _icon_tex(String(def.get("icon", "")))
			var req_ok: bool = int(def.get("tier", 1)) < 2 or skillbar.staff_equipped
			dim.visible = not req_ok
			slot.add_theme_stylebox_override("panel", _s_hotbar_item if not req_ok else _s_skill_empty)
		_update_skill_cd(slot, i)

func _update_skill_cd(slot: SkillSlot, index: int) -> void:
	var cd := slot.get_node("Content/CD") as ColorRect
	var cd_text := slot.get_node("Content/CDText") as Label
	var id := skillbar.resolve(index)
	if id == "":
		cd.visible = false
		cd_text.visible = false
		_skill_cd_last[index] = 0.0
		return
	var remaining := skillbar.get_cooldown(id)
	var total := skillbar.get_cooldown_total(id)
	var prev := float(_skill_cd_last.get(index, 0.0))
	if total > 0.0 and remaining > 0.0:
		var pct := clampf(remaining / total, 0.0, 1.0)
		cd.visible = true
		cd.offset_top = -HOTBAR_SLOT * pct
		cd_text.visible = true
		cd_text.text = "%.1f" % (remaining / 1000.0)
	elif prev > 0.0 and remaining <= 0.0:
		cd.visible = true
		cd_text.visible = false
		cd.color = Color(1, 1, 1, 0.85)
		var tw := create_tween()
		tw.tween_property(cd, "color", Color(0, 0, 0, 0.55), 0.18)
	else:
		cd.visible = false
		cd_text.visible = false
	_skill_cd_last[index] = remaining

## 技能槽拖放（旧版：技能↔技能交换；外部技能投放接口；拖出解绑）
func drop_on_skill(index: int, data: Dictionary) -> void:
	if skillbar == null:
		return
	match String(data.get("type", "")):
		"skill":
			skillbar.swap(index, int(data.get("slot", -1)))
		"skillbar":
			skillbar.assign(index, String(data.get("skill_id", "")))

func use_backpack_item(slot: int) -> void:
	if backpack == null or slot < 0 or slot >= backpack.slots.size() or backpack.slots[slot] == null:
		return
	var item: Dictionary = backpack.slots[slot]
	if String(item.get("category", "")).begins_with("weapon") or String(item.get("equipSlot", "")) != "":
		# 装备类物品右键 = 装备（旧版右键菜单"装备"）
		if equipment != null and equipment.equip_from_backpack(slot):
			return
		_flash_status("无法装备")
		return
	var player := _get_player()
	if player == null or bool(player.get("is_dead")):
		return
	var result := backpack.use_item(String(item.get("instance_id", "")), player)
	if result.get("ok", false):
		_notify_heal(player)
	else:
		_flash_status(String(result.get("message", "")))

func _notify_heal(player: Node) -> void:
	if player != null and player.get("hp") != null:
		player_healed.emit(int(player.get("hp")))

## ---------- 面板开关（右侧滑入 + 遮罩淡入） ----------

func toggle_panel() -> void:
	set_panel_open(not _panel_open)

func set_panel_open(open: bool) -> void:
	if _panel_open == open:
		return
	_panel_open = open
	if _panel_anim != null and _panel_anim.is_valid():
		_panel_anim.kill()
	var dim := _panel_root.get_node("Dim") as ColorRect
	if open:
		_panel_root.visible = true
		dim.modulate.a = 0.0
		_apply_panel_slide(0.0)
		_panel_anim = create_tween()
		_panel_anim.tween_property(dim, "modulate:a", 1.0, 0.22)
		_panel_anim.parallel().tween_method(_apply_panel_slide, 0.0, 1.0, 0.25) \
			.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	else:
		_panel_anim = create_tween()
		_panel_anim.tween_property(dim, "modulate:a", 0.0, 0.16)
		_panel_anim.parallel().tween_method(_apply_panel_slide, 1.0, 0.0, 0.18) \
			.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
		_panel_anim.tween_callback(func() -> void: _panel_root.visible = false)
		var player := _get_player()
		if player == null or not bool(player.get("is_dead")):
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	hide_tooltip()

## ---------- 页签（角色状态 / 装备背包，复刻旧版 SystemUI 页签） ----------

func set_tab(tab: String) -> void:
	if tab != "status" and tab != "equip" and tab != "skill":
		return
	_current_tab = tab
	if _status_page != null:
		_status_page.visible = tab == "status"
	if _equip_page != null:
		_equip_page.visible = tab == "equip"
	if _skill_page != null:
		_skill_page.visible = tab == "skill"
	if _panel_title != null:
		_panel_title.text = "角色状态" if tab == "status" else ("装备与背包" if tab == "equip" else "技能")
	_update_tab_styles()

func _update_tab_styles() -> void:
	if _tab_status == null or _tab_equip == null or _tab_skill == null:
		return
	_tab_status.add_theme_stylebox_override("normal", _tab_style(_current_tab == "status"))
	_tab_equip.add_theme_stylebox_override("normal", _tab_style(_current_tab == "equip"))
	_tab_skill.add_theme_stylebox_override("normal", _tab_style(_current_tab == "skill"))
	_tab_status.add_theme_color_override("font_color", Style.COLOR_TEXT if _current_tab == "status" else Style.COLOR_DIM_TEXT)
	_tab_equip.add_theme_color_override("font_color", Style.COLOR_TEXT if _current_tab == "equip" else Style.COLOR_DIM_TEXT)
	_tab_skill.add_theme_color_override("font_color", Style.COLOR_TEXT if _current_tab == "skill" else Style.COLOR_DIM_TEXT)

func _tab_style(active: bool) -> StyleBoxFlat:
	if active:
		var sb := Style.make_style(Style.COLOR_ITEM_BG, Style.COLOR_ITEM_BORDER, 6, 2)
		return sb
	return Style.make_style(Style.COLOR_BAR_BG, Style.COLOR_PANEL_BORDER, 6, 2)

## 右侧贴边滑入（复刻旧版 system-panel：translateX(100%)→0，0.25s cubic-bezier）
func _apply_panel_slide(t: float) -> void:
	_panel.offset_left = -_panel_w * t
	_panel.offset_right = _panel_w * (1.0 - t)

## ---------- 获取/添加物品 ----------

func try_add(id: String, count := 1) -> bool:
	if backpack == null:
		return false
	var ok := backpack.add_item(id, count)
	if not ok:
		_show_notice("背包已满")
	return ok

func _get_player() -> Node:
	var scene := get_tree().current_scene
	if scene == null:
		return null
	return scene.get_node_or_null("Player")

## ---------- 拖拽落点 ----------

func drop_on_hotbar(index: int, data: Dictionary) -> void:
	if backpack == null:
		return
	match String(data.get("type", "")):
		"hotbar":
			backpack.swap_hotbar(index, int(data.get("index", -1)))
		"backpack":
			var src := int(data.get("slot", -1))
			if src >= 0 and src < backpack.slots.size() and backpack.slots[src] != null:
				backpack.bind_hotbar(index, String(backpack.slots[src].get("instance_id", "")))

func drop_on_backpack(slot: int, data: Dictionary) -> void:
	if backpack == null:
		return
	match String(data.get("type", "")):
		"backpack":
			backpack.swap_items(slot, int(data.get("slot", -1)))
		"hotbar":
			backpack.unbind_hotbar(int(data.get("index", -1)))
		"equip":
			if equipment != null:
				equipment.unequip(String(data.get("key", "")))
		"skill":
			if skillbar != null:
				skillbar.unassign(int(data.get("slot", -1)))

func drop_on_equip(key: String, data: Dictionary) -> void:
	if equipment == null or equipment.is_locked(key):
		return
	match String(data.get("type", "")):
		"equip":
			equipment.swap_equip(key, String(data.get("key", "")))
		"backpack":
			equipment.equip_to_slot(key, int(data.get("slot", -1)))

## ---------- 动画回调 ----------

func _on_item_added(slot: int) -> void:
	if slot >= 0 and slot < _cells.size():
		_pop_cell(slot)

func _on_bound(index: int) -> void:
	if index >= 0 and index < _hotbar_slots.size():
		_flash_hotbar(index)

func _on_equipped(key: String) -> void:
	if _equip_cells.has(key):
		var cell: EquipSlot = _equip_cells[key]
		cell.pivot_offset = EQUIP_SLOT_SIZE * 0.5
		var tw := create_tween()
		tw.tween_property(cell, "scale", Vector2(1.12, 1.12), 0.14)
		tw.tween_property(cell, "scale", Vector2.ONE, 0.16).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

func _pop_cell(slot: int) -> void:
	var cell: BackpackCell = _cells[slot]
	var s := cell.size
	if s == Vector2.ZERO:
		s = Vector2(72, CELL_SLOT)
	cell.pivot_offset = s * 0.5
	var tw := create_tween()
	tw.tween_property(cell, "scale", Vector2(1.2, 1.2), 0.18).from(Vector2(0.5, 0.5))
	tw.tween_property(cell, "scale", Vector2(0.95, 0.95), 0.12)
	tw.tween_property(cell, "scale", Vector2.ONE, 0.12)

func _flash_hotbar(index: int) -> void:
	var slot: HotbarSlot = _hotbar_slots[index]
	slot.pivot_offset = Vector2(HOTBAR_SLOT, HOTBAR_SLOT) * 0.5
	var tw := create_tween()
	tw.tween_property(slot, "scale", Vector2(1.15, 1.15), 0.14)
	tw.tween_property(slot, "scale", Vector2.ONE, 0.16).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

func _shake_hotbar(index: int) -> void:
	var slot: HotbarSlot = _hotbar_slots[index]
	slot.pivot_offset = Vector2(HOTBAR_SLOT, HOTBAR_SLOT) * 0.5
	var tw := create_tween()
	tw.tween_property(slot, "scale", Vector2(0.95, 0.95), 0.06)
	tw.tween_property(slot, "scale", Vector2.ONE, 0.1).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

func _flash_cd_end(slot: HotbarSlot) -> void:
	var overlay := slot.get_node("Content/CD") as ColorRect
	overlay.color = Color(1, 1, 1, 0.85)
	var tw := create_tween()
	tw.tween_property(overlay, "color", Color(0, 0, 0, 0.55), 0.18)

## ---------- 悬停 / 拖拽高亮 ----------

func on_cell_mouse(enter: bool, slot: int) -> void:
	if slot < 0 or slot >= _cells.size():
		return
	_hovered_cell = slot if enter else -1
	var cell: BackpackCell = _cells[slot]
	if enter:
		cell.add_theme_stylebox_override("panel", _s_cell_drag_over if slot == _drag_over_cell else _s_cell_hover)
		if backpack != null and backpack.slots[slot] != null:
			show_item_tooltip(backpack.slots[slot], get_viewport().get_mouse_position())
	else:
		cell.add_theme_stylebox_override("panel", _s_cell_drag_over if slot == _drag_over_cell else (_s_cell_item if backpack.slots[slot] != null else _s_cell_empty))
		if _tooltip != null and not _tooltip.is_pinned():
			hide_tooltip()

func on_hotbar_mouse(enter: bool, index: int) -> void:
	if index < 0 or index >= _hotbar_slots.size():
		return
	_hovered_hotbar = index if enter else -1
	var slot: HotbarSlot = _hotbar_slots[index]
	var item := backpack.resolve_hotbar(index) if backpack != null else {}
	if enter:
		slot.add_theme_stylebox_override("panel", _s_hotbar_hover)
		if not item.is_empty():
			show_item_tooltip(item, get_viewport().get_mouse_position())
	else:
		slot.add_theme_stylebox_override("panel", _s_hotbar_item if not item.is_empty() else _s_hotbar_empty)
		if _tooltip != null and not _tooltip.is_pinned():
			hide_tooltip()

func on_equip_mouse(enter: bool, key: String) -> void:
	_hovered_equip = key if enter else ""
	if not _equip_cells.has(key):
		return
	var cell: EquipSlot = _equip_cells[key]
	var item: Dictionary = equipment.get_item(key) if equipment != null else {}
	var locked := equipment != null and equipment.is_locked(key)
	if enter:
		if not locked:
			cell.add_theme_stylebox_override("panel", _s_equip_hover)
		if not item.is_empty():
			show_item_tooltip(item, get_viewport().get_mouse_position())
	else:
		if locked:
			cell.add_theme_stylebox_override("panel", _s_equip_locked)
		else:
			cell.add_theme_stylebox_override("panel", _s_equip_equipped if not item.is_empty() else _s_equip_empty)
		if _tooltip != null and not _tooltip.is_pinned():
			hide_tooltip()

func on_equip_click_pin(key: String) -> void:
	if _tooltip == null or equipment == null:
		return
	var item := equipment.get_item(key)
	if item.is_empty():
		return
	show_item_tooltip(item, get_viewport().get_mouse_position())
	_tooltip.set_pinned(true)

func on_equip_right_click(key: String) -> void:
	if equipment != null and not equipment.get_item(key).is_empty():
		equipment.unequip(key)

func set_cell_drag_over(slot: int, on: bool) -> void:
	if slot < 0 or slot >= _cells.size():
		return
	_drag_over_cell = slot if on else -1
	var cell: BackpackCell = _cells[slot]
	if on:
		cell.add_theme_stylebox_override("panel", _s_cell_drag_over)
		_drag_clear_timer.start(0.25)
	else:
		cell.add_theme_stylebox_override("panel", _s_cell_hover if slot == _hovered_cell else (_s_cell_item if backpack.slots[slot] != null else _s_cell_empty))

func set_hotbar_drag_over(index: int, on: bool) -> void:
	if index < 0 or index >= _hotbar_slots.size():
		return
	_drag_over_hotbar = index if on else -1
	var slot: HotbarSlot = _hotbar_slots[index]
	var item := backpack.resolve_hotbar(index) if backpack != null else {}
	if on:
		slot.add_theme_stylebox_override("panel", _s_hotbar_hover)
		_drag_clear_timer.start(0.25)
	else:
		slot.add_theme_stylebox_override("panel", _s_hotbar_item if not item.is_empty() else _s_hotbar_empty)

func set_equip_drag_over(key: String, on: bool) -> void:
	if not _equip_cells.has(key):
		return
	_drag_over_equip = key if on else ""
	var cell: EquipSlot = _equip_cells[key]
	var item: Dictionary = equipment.get_item(key) if equipment != null else {}
	if on:
		cell.add_theme_stylebox_override("panel", _s_cell_drag_over)
		_drag_clear_timer.start(0.25)
	else:
		cell.add_theme_stylebox_override("panel", _s_equip_hover if key == _hovered_equip else (_s_equip_equipped if not item.is_empty() else _s_equip_empty))

func _clear_all_drag_over() -> void:
	if backpack == null:
		return
	_drag_over_cell = -1
	_drag_over_hotbar = -1
	_drag_over_equip = ""
	for i in _cells.size():
		var cell: BackpackCell = _cells[i]
		cell.add_theme_stylebox_override("panel", _s_cell_hover if i == _hovered_cell else (_s_cell_item if backpack.slots[i] != null else _s_cell_empty))
	for i in _hotbar_slots.size():
		var slot: HotbarSlot = _hotbar_slots[i]
		var item := backpack.resolve_hotbar(i) if backpack != null else {}
		slot.add_theme_stylebox_override("panel", _s_hotbar_item if not item.is_empty() else _s_hotbar_empty)
	for key in _equip_cells.keys():
		var cell: EquipSlot = _equip_cells[key]
		var it: Dictionary = equipment.get_item(key) if equipment != null else {}
		var locked := equipment != null and equipment.is_locked(key)
		cell.add_theme_stylebox_override("panel", _s_equip_locked if locked else (_s_equip_equipped if not it.is_empty() else _s_equip_empty))

func on_cell_click_pin(slot: int) -> void:
	if _tooltip == null or backpack == null or backpack.slots[slot] == null:
		return
	show_item_tooltip(backpack.slots[slot], get_viewport().get_mouse_position())
	_tooltip.set_pinned(true)

## ---------- 浮窗 ----------

func _build_tooltip() -> void:
	_tooltip = ItemTooltipScript.new()
	_tooltip.name = "ItemTooltip"
	_tooltip.visible = false
	_tooltip.close_requested.connect(hide_tooltip)
	add_child(_tooltip)

func show_item_tooltip(item: Dictionary, at_pos: Vector2) -> void:
	if _tooltip == null or item.is_empty():
		return
	_tooltip.render(item)
	_tooltip.set_pinned(false)
	_tooltip.visible = true
	_tooltip.modulate.a = 1.0
	if _tooltip_tween != null and _tooltip_tween.is_valid():
		_tooltip_tween.kill()
	_tooltip_tween = create_tween()
	_tooltip_tween.tween_property(_tooltip, "modulate:a", 1.0, 0.12).from(0.0)
	_place_tooltip(at_pos)

func hide_tooltip() -> void:
	if _tooltip == null or not _tooltip.visible:
		return
	if _tooltip_tween != null and _tooltip_tween.is_valid():
		_tooltip_tween.kill()
	_tooltip_tween = create_tween()
	_tooltip_tween.tween_property(_tooltip, "modulate:a", 0.0, 0.1)
	_tooltip_tween.tween_callback(func() -> void: _tooltip.visible = false)

func _place_tooltip(at: Vector2) -> void:
	if _tooltip == null:
		return
	var ts := _tooltip.get_combined_minimum_size()
	var vp := get_viewport_rect().size
	var pos := at + Vector2(16, 16)
	if pos.x + ts.x > vp.x - 8:
		pos.x = at.x - ts.x - 12
	if pos.y + ts.y > vp.y - 8:
		pos.y = at.y - ts.y - 12
	pos.x = clampf(pos.x, 8, maxf(8, vp.x - ts.x - 8))
	pos.y = clampf(pos.y, 8, maxf(8, vp.y - ts.y - 8))
	_tooltip.position = pos

## ---------- 冷却 ----------

func _process(delta: float) -> void:
	if backpack != null:
		backpack.tick_cooldowns(delta)
		_update_cooldown_overlays()
	if skillbar != null:
		skillbar.tick(delta * 1000.0)
		for i in _skill_slots.size():
			_update_skill_cd(_skill_slots[i], i)
	if _tooltip != null and _tooltip.visible and not _tooltip.is_pinned():
		_place_tooltip(get_viewport().get_mouse_position())

func _update_cooldown_overlays() -> void:
	for i in _hotbar_slots.size():
		var slot: HotbarSlot = _hotbar_slots[i]
		var overlay := slot.get_node("Content/CD") as ColorRect
		var item := backpack.resolve_hotbar(i)
		if item.is_empty():
			overlay.visible = false
			_cd_last[i] = 0.0
			continue
		var inst := String(item.get("instance_id", ""))
		var remaining := backpack.get_cooldown(inst)
		var total := backpack.get_cooldown_total(inst)
		var prev := float(_cd_last.get(i, 0.0))
		if total > 0.0 and remaining > 0.0:
			var pct := clampf(remaining / total, 0.0, 1.0)
			overlay.visible = true
			overlay.offset_top = -HOTBAR_SLOT * pct
			overlay.color = Color(0, 0, 0, 0.55)
		elif prev > 0.0 and remaining <= 0.0:
			overlay.visible = true
			_flash_cd_end(slot)
		else:
			overlay.visible = false
		_cd_last[i] = remaining

## ---------- 构建：快捷栏 ----------

func _build_hotbar() -> void:
	var bar := PanelContainer.new()
	bar.name = "Hotbar"
	bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bar.add_theme_stylebox_override("panel", Style.make_style(Style.COLOR_BAR_BG, Style.COLOR_BAR_BORDER, 12, 2))
	bar.add_theme_constant_override("margin_left", BAR_PAD)
	bar.add_theme_constant_override("margin_right", BAR_PAD)
	bar.add_theme_constant_override("margin_top", BAR_PAD)
	bar.add_theme_constant_override("margin_bottom", BAR_PAD)
	add_child(bar)
	_hotbar_root = HBoxContainer.new()
	_hotbar_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hotbar_root.add_theme_constant_override("separation", BAR_GAP)
	bar.add_child(_hotbar_root)
	# 技能组（旧版 skillGroup：Q/E/X/C 占位，技能系统未移植前为空槽）
	_hotbar_root.add_child(_make_divider())
	for i in SKILL_SIZE:
		var slot := SkillSlot.new()
		slot.hud = self
		slot.key = SKILL_KEY_HINTS[i]
		slot.index = i
		slot.custom_minimum_size = Vector2(HOTBAR_SLOT, HOTBAR_SLOT)
		slot.add_theme_stylebox_override("panel", _s_skill_empty)
		var content := Control.new()
		content.name = "Content"
		content.custom_minimum_size = Vector2(HOTBAR_SLOT, HOTBAR_SLOT)
		content.mouse_filter = Control.MOUSE_FILTER_IGNORE
		slot.add_child(content)
		var icon := TextureRect.new()
		icon.name = "Icon"
		icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		content.add_child(icon)
		var key := _make_label(content, SKILL_KEY_HINTS[i], 11, Style.COLOR_KEY_HINT, Vector2(HOTBAR_SLOT - 14, HOTBAR_SLOT - 17))
		key.name = "Key"
		var blink := create_tween()
		blink.set_loops()
		blink.tween_property(key, "modulate:a", 0.35, 0.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		blink.tween_property(key, "modulate:a", 1.0, 0.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		var cd := ColorRect.new()
		cd.name = "CD"
		cd.color = Color(0, 0, 0, 0.55)
		cd.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cd.anchor_left = 0.0
		cd.anchor_right = 1.0
		cd.anchor_top = 1.0
		cd.anchor_bottom = 1.0
		cd.offset_bottom = 0
		cd.offset_top = 0
		cd.visible = false
		content.add_child(cd)
		var cd_text := _make_label(content, "", 10, Color.WHITE, Vector2(HOTBAR_SLOT - 18, HOTBAR_SLOT - 28))
		cd_text.name = "CDText"
		cd_text.add_theme_font_override("font", _font_mono)
		cd_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		cd_text.visible = false
		var dim := ColorRect.new()
		dim.name = "Dim"
		dim.color = Color(0.2, 0.2, 0.2, 0.55)
		dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
		dim.visible = false
		content.add_child(dim)
		_hotbar_root.add_child(slot)
		_skill_slots.append(slot)
	# 特殊攻击槽（旧版 special：右击，默认隐藏；右键已被机瞄占用，仅做显示位）
	var sp := SkillSlot.new()
	sp.hud = self
	sp.key = "右击"
	sp.index = -1
	sp.custom_minimum_size = Vector2(HOTBAR_SLOT, HOTBAR_SLOT)
	sp.add_theme_stylebox_override("panel", Style.make_style(Color(0.231, 0.208, 0.29), Color(0.353, 0.353, 0.541), 8, 2))
	sp.visible = false
	var sp_content := Control.new()
	sp_content.name = "Content"
	sp_content.custom_minimum_size = Vector2(HOTBAR_SLOT, HOTBAR_SLOT)
	sp_content.mouse_filter = Control.MOUSE_FILTER_IGNORE
	sp.add_child(sp_content)
	var sp_icon := TextureRect.new()
	sp_icon.name = "Icon"
	sp_icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	sp_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	sp_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	sp_icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	sp_content.add_child(sp_icon)
	var sp_key := _make_label(sp_content, "右击", 10, Style.COLOR_KEY_HINT, Vector2(0, HOTBAR_SLOT - 17))
	sp_key.name = "Key"
	sp_key.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_hotbar_root.add_child(sp)
	_special_slot = sp
	# 分隔 + 物品组（旧版 itemGroup：1~4）
	_hotbar_root.add_child(_make_divider())
	for i in HOTBAR_SIZE:
		var slot := HotbarSlot.new()
		slot.hud = self
		slot.index = i
		slot.custom_minimum_size = Vector2(HOTBAR_SLOT, HOTBAR_SLOT)
		slot.add_theme_stylebox_override("panel", _s_hotbar_empty)
		var content := Control.new()
		content.name = "Content"
		content.custom_minimum_size = Vector2(HOTBAR_SLOT, HOTBAR_SLOT)
		content.mouse_filter = Control.MOUSE_FILTER_IGNORE
		slot.add_child(content)
		var icon := TextureRect.new()
		icon.name = "Icon"
		icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 3)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		content.add_child(icon)
		var stack := _make_label(content, "", 12, Style.COLOR_TEXT, Vector2(3, HOTBAR_SLOT - 18))
		stack.name = "Stack"
		stack.add_theme_font_override("font", _font_mono)
		var key := _make_label(content, str(i + 1), 11, Style.COLOR_KEY_HINT, Vector2(HOTBAR_SLOT - 14, HOTBAR_SLOT - 17))
		key.name = "Key"
		var blink := create_tween()
		blink.set_loops()
		blink.tween_property(key, "modulate:a", 0.35, 0.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		blink.tween_property(key, "modulate:a", 1.0, 0.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		var cd := ColorRect.new()
		cd.name = "CD"
		cd.color = Color(0, 0, 0, 0.55)
		cd.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cd.anchor_left = 0.0
		cd.anchor_right = 1.0
		cd.anchor_top = 1.0
		cd.anchor_bottom = 1.0
		cd.offset_left = 0
		cd.offset_right = 0
		cd.offset_bottom = 0
		cd.offset_top = 0
		cd.visible = false
		content.add_child(cd)
		_hotbar_root.add_child(slot)
		_hotbar_slots.append(slot)
	var w := (HOTBAR_SIZE + SKILL_SIZE) * HOTBAR_SLOT + (HOTBAR_SIZE + SKILL_SIZE + 2) * BAR_GAP + 2 * 2 + BAR_PAD * 2
	var h := HOTBAR_SLOT + BAR_PAD * 2
	bar.anchor_left = 0.5
	bar.anchor_right = 0.5
	bar.anchor_top = 1.0
	bar.anchor_bottom = 1.0
	bar.grow_horizontal = Control.GROW_DIRECTION_BOTH
	bar.grow_vertical = Control.GROW_DIRECTION_BOTH
	bar.offset_left = -w / 2.0
	bar.offset_right = w / 2.0
	bar.offset_top = -h - 14.0
	bar.offset_bottom = -14.0

## ---------- 构建：装备与背包面板 ----------

func _build_panel() -> void:
	_panel_root = Control.new()
	_panel_root.name = "BackpackPanel"
	_panel_root.mouse_filter = Control.MOUSE_FILTER_STOP
	_panel_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_panel_root.visible = false
	add_child(_panel_root)
	var dim := ColorRect.new()
	dim.name = "Dim"
	dim.color = Style.COLOR_OVERLAY
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_panel_root.add_child(dim)
	_panel = PanelContainer.new()
	_panel.name = "Panel"
	_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	var panel_sb := Style.make_style(Style.COLOR_PANEL_BG, Style.COLOR_PANEL_BORDER, 12, 2)
	panel_sb.set_corner_radius_all(0)
	panel_sb.set_corner_radius(CORNER_TOP_LEFT, 12)
	panel_sb.set_corner_radius(CORNER_BOTTOM_LEFT, 12)
	panel_sb.border_width_left = 3
	_panel.add_theme_stylebox_override("panel", panel_sb)
	_panel_root.add_child(_panel)
	var content := Control.new()
	content.name = "Content"
	content.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel.add_child(content)
	var blur := ColorRect.new()
	blur.name = "Blur"
	blur.mouse_filter = Control.MOUSE_FILTER_IGNORE
	blur.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var mat := ShaderMaterial.new()
	mat.shader = PANEL_BLUR_SHADER
	blur.material = mat
	content.add_child(blur)
	var margin := MarginContainer.new()
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_theme_constant_override("margin_left", PANEL_MARGIN)
	margin.add_theme_constant_override("margin_right", PANEL_MARGIN)
	margin.add_theme_constant_override("margin_top", PANEL_MARGIN)
	margin.add_theme_constant_override("margin_bottom", PANEL_MARGIN)
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	content.add_child(margin)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 10)
	vbox.alignment = BoxContainer.ALIGNMENT_CENTER
	margin.add_child(vbox)
	var title_row := HBoxContainer.new()
	vbox.add_child(title_row)
	_panel_title = _make_label(title_row, "装备与背包", 24, Style.COLOR_TITLE_TEXT, Vector2.ZERO)
	_panel_title.add_theme_font_override("font", _font_title)
	_panel_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var divider := HSeparator.new()
	divider.modulate = Style.COLOR_PANEL_BORDER
	vbox.add_child(divider)
	# 页签栏（旧版 SystemUI 页签）
	var tab_bar := HBoxContainer.new()
	tab_bar.add_theme_constant_override("separation", 6)
	vbox.add_child(tab_bar)
	_tab_status = _make_tab_button("角色状态")
	_tab_equip = _make_tab_button("装备背包")
	_tab_skill = _make_tab_button("技能")
	tab_bar.add_child(_tab_status)
	tab_bar.add_child(_tab_equip)
	tab_bar.add_child(_tab_skill)
	_tab_status.pressed.connect(func() -> void: set_tab("status"))
	_tab_equip.pressed.connect(func() -> void: set_tab("equip"))
	_tab_skill.pressed.connect(func() -> void: set_tab("skill"))
	# 页面栈
	_page_stack = Control.new()
	_page_stack.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_page_stack.mouse_filter = Control.MOUSE_FILTER_IGNORE
	vbox.add_child(_page_stack)
	_equip_page = VBoxContainer.new()
	_equip_page.name = "EquipPage"
	_equip_page.add_theme_constant_override("separation", 8)
	_equip_page.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_equip_page.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_page_stack.add_child(_equip_page)
	# 上：装备栏（旧版 gear-equip-col，占上半区，3x5 大宽格）
	var equip_col := VBoxContainer.new()
	equip_col.add_theme_constant_override("separation", 6)
	_equip_page.add_child(equip_col)
	var equip_title := _make_label(equip_col, "装备栏", 14, Style.COLOR_TEXT, Vector2.ZERO)
	equip_title.add_theme_font_override("font", _font_section)
	equip_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_equip_grid = GridContainer.new()
	_equip_grid.columns = EQUIP_COLS
	_equip_grid.add_theme_constant_override("h_separation", 8)
	_equip_grid.add_theme_constant_override("v_separation", 8)
	_equip_grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	equip_col.add_child(_equip_grid)
	var total_slots := backpack.max_slots if backpack != null else 30
	for key in EquipmentScript.SLOT_ORDER:
		var cell := EquipSlot.new()
		cell.hud = self
		cell.key = key
		cell.custom_minimum_size = EQUIP_SLOT_SIZE
		cell.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		cell.add_theme_stylebox_override("panel", _s_equip_empty)
		var cell_content := Control.new()
		cell_content.name = "Content"
		cell_content.custom_minimum_size = EQUIP_SLOT_SIZE
		cell_content.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell.add_child(cell_content)
		var icon := TextureRect.new()
		icon.name = "Icon"
		icon.anchor_left = 0.0
		icon.anchor_top = 0.0
		icon.anchor_right = 0.0
		icon.anchor_bottom = 1.0
		icon.offset_left = 20
		icon.offset_top = 6
		icon.offset_right = 118
		icon.offset_bottom = -6
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell_content.add_child(icon)
		var fallback := Label.new()
		fallback.name = "Fallback"
		fallback.anchor_left = 0.0
		fallback.anchor_top = 0.0
		fallback.anchor_right = 0.0
		fallback.anchor_bottom = 1.0
		fallback.offset_left = 20
		fallback.offset_top = 6
		fallback.offset_right = 118
		fallback.offset_bottom = -6
		fallback.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		fallback.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		fallback.add_theme_font_override("font", Style.make_emoji_font())
		fallback.add_theme_font_size_override("font_size", 26)
		fallback.mouse_filter = Control.MOUSE_FILTER_IGNORE
		fallback.visible = false
		cell_content.add_child(fallback)
		var name_lbl := Label.new()
		name_lbl.name = "Name"
		name_lbl.anchor_left = 1.0
		name_lbl.anchor_top = 0.0
		name_lbl.anchor_right = 1.0
		name_lbl.anchor_bottom = 1.0
		name_lbl.offset_left = -118
		name_lbl.offset_top = 8
		name_lbl.offset_right = -10
		name_lbl.offset_bottom = -8
		name_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		name_lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		name_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		name_lbl.add_theme_font_size_override("font_size", 13)
		name_lbl.add_theme_color_override("font_color", Style.COLOR_DIM_TEXT)
		name_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell_content.add_child(name_lbl)
		var rarity_lbl := Label.new()
		rarity_lbl.name = "Rarity"
		rarity_lbl.anchor_left = 0.0
		rarity_lbl.anchor_top = 0.0
		rarity_lbl.anchor_right = 0.0
		rarity_lbl.anchor_bottom = 1.0
		rarity_lbl.offset_left = 4
		rarity_lbl.offset_top = 4
		rarity_lbl.offset_right = 20
		rarity_lbl.offset_bottom = -4
		rarity_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		rarity_lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		rarity_lbl.add_theme_font_size_override("font_size", 12)
		rarity_lbl.add_theme_color_override("font_color", Style.COLOR_RARITY_TEXT)
		rarity_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell_content.add_child(rarity_lbl)
		var badges := VBoxContainer.new()
		badges.name = "Badges"
		badges.anchor_left = 1.0
		badges.anchor_right = 1.0
		badges.offset_left = -38
		badges.offset_right = -6
		badges.offset_top = 4
		badges.add_theme_constant_override("separation", 2)
		badges.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell_content.add_child(badges)
		var lock := Control.new()
		lock.name = "Lock"
		lock.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		lock.mouse_filter = Control.MOUSE_FILTER_IGNORE
		lock.visible = false
		cell_content.add_child(lock)
		var lock_bg := ColorRect.new()
		lock_bg.color = Style.COLOR_EQUIP_LOCK_OVERLAY
		lock_bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		lock_bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
		lock.add_child(lock_bg)
		var x_lbl := Label.new()
		x_lbl.text = "✕"
		x_lbl.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
		x_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		x_lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		x_lbl.add_theme_font_size_override("font_size", 30)
		x_lbl.add_theme_color_override("font_color", Style.COLOR_BLACK)
		x_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		lock.add_child(x_lbl)
		_equip_grid.add_child(cell)
		_equip_cells[key] = cell
	# 下：背包（旧版 gear-inventory-col：表头 背包+0/36，5 列小方格）
	var inv_col := VBoxContainer.new()
	inv_col.add_theme_constant_override("separation", 4)
	_equip_page.add_child(inv_col)
	var inv_header := HBoxContainer.new()
	inv_col.add_child(inv_header)
	var inv_title := _make_label(inv_header, "背包", 14, Style.COLOR_TEXT, Vector2.ZERO)
	inv_title.add_theme_font_override("font", _font_section)
	inv_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_count_label = _make_label(inv_header, "", 14, Style.COLOR_DIM_TEXT, Vector2.ZERO)
	_count_label.add_theme_font_override("font", _font_mono)
	_grid = GridContainer.new()
	_grid.columns = INV_COLS
	_grid.add_theme_constant_override("h_separation", 6)
	_grid.add_theme_constant_override("v_separation", 6)
	_grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inv_col.add_child(_grid)
	for i in total_slots:
		var cell := BackpackCell.new()
		cell.hud = self
		cell.slot = i
		cell.custom_minimum_size = Vector2(72, CELL_SLOT)
		cell.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		cell.add_theme_stylebox_override("panel", _s_cell_empty)
		var cell_content := Control.new()
		cell_content.name = "Content"
		cell_content.custom_minimum_size = Vector2(72, CELL_SLOT)
		cell_content.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell.add_child(cell_content)
		var icon := TextureRect.new()
		icon.name = "Icon"
		icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 4)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell_content.add_child(icon)
		var fallback := Label.new()
		fallback.name = "Fallback"
		fallback.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		fallback.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		fallback.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		fallback.add_theme_font_override("font", Style.make_emoji_font())
		fallback.add_theme_font_size_override("font_size", 22)
		fallback.mouse_filter = Control.MOUSE_FILTER_IGNORE
		fallback.visible = false
		cell_content.add_child(fallback)
		var stack := _make_label(cell_content, "", 12, Style.COLOR_STACK_TEXT, Vector2.ZERO)
		stack.name = "Stack"
		stack.add_theme_font_override("font", _font_mono)
		stack.anchor_left = 1.0
		stack.anchor_right = 1.0
		stack.anchor_top = 1.0
		stack.anchor_bottom = 1.0
		stack.offset_left = -30
		stack.offset_top = -20
		stack.offset_right = -4
		stack.offset_bottom = -2
		stack.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		var name_lbl := _make_label(cell_content, "", 13, Style.COLOR_WHITE, Vector2.ZERO)
		name_lbl.name = "Name"
		name_lbl.anchor_left = 0.0
		name_lbl.anchor_right = 1.0
		name_lbl.anchor_top = 1.0
		name_lbl.anchor_bottom = 1.0
		name_lbl.offset_left = 4
		name_lbl.offset_top = -20
		name_lbl.offset_right = -4
		name_lbl.offset_bottom = -2
		name_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		var rarity_lbl := Label.new()
		rarity_lbl.name = "Rarity"
		rarity_lbl.anchor_left = 0.0
		rarity_lbl.anchor_right = 0.0
		rarity_lbl.anchor_top = 0.0
		rarity_lbl.anchor_bottom = 1.0
		rarity_lbl.offset_left = 2
		rarity_lbl.offset_top = 2
		rarity_lbl.offset_right = 15
		rarity_lbl.offset_bottom = -2
		rarity_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		rarity_lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		rarity_lbl.add_theme_font_size_override("font_size", 12)
		rarity_lbl.add_theme_color_override("font_color", Style.COLOR_RARITY_TEXT)
		rarity_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell_content.add_child(rarity_lbl)
		_grid.add_child(cell)
		_cells.append(cell)
	# 右侧贴边：固定 PANEL_W 宽、全高，初始在屏幕外右侧（复刻旧版 system-panel）
	_panel.anchor_left = 1.0
	_panel.anchor_right = 1.0
	_panel.anchor_top = 0.0
	_panel.anchor_bottom = 1.0
	_panel.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_panel.offset_top = 0
	_panel.offset_bottom = 0
	_apply_panel_slide(0.0)

func _build_status_label() -> void:
	_status_label = _make_label(self, "", Style.font_size("label"), Style.COLOR_STATUS, Vector2.ZERO)
	_status_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_status_label.offset_top = -92
	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_status_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_status_label.visible = false

func _build_notice() -> void:
	_notice_label = _make_label(self, "", 36, Style.COLOR_NOTICE, Vector2.ZERO)
	_notice_label.add_theme_font_override("font", _font_title)
	_notice_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_notice_label.offset_top = 210
	_notice_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_notice_label.visible = false

func _show_notice(text: String) -> void:
	if _notice_label == null:
		return
	_notice_label.text = text
	_notice_label.visible = true
	_notice_label.modulate.a = 1.0
	if _notice_tween != null and _notice_tween.is_valid():
		_notice_tween.kill()
	_notice_tween = create_tween()
	_notice_tween.tween_interval(1.2)
	_notice_tween.tween_property(_notice_label, "modulate:a", 0.0, 1.8)
	_notice_tween.tween_callback(func() -> void: _notice_label.visible = false)

## ---------- 工具 ----------

func _make_label(parent: Node, text: String, font_size: int, color: Color, pos: Vector2) -> Label:
	var l := Label.new()
	l.text = text
	l.position = pos
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l

func _make_tab_button(label: String) -> Button:
	var b := Button.new()
	b.text = label
	b.custom_minimum_size = Vector2(120, 30)
	b.add_theme_font_size_override("font_size", 13)
	b.add_theme_font_override("font", _font_section)
	var idle := _tab_style(false)
	b.add_theme_stylebox_override("normal", idle)
	b.add_theme_stylebox_override("hover", idle)
	b.add_theme_stylebox_override("pressed", idle)
	b.add_theme_stylebox_override("focus", Style.make_style(Style.COLOR_TRANSPARENT, Style.COLOR_TRANSPARENT, 0, 0))
	b.add_theme_color_override("font_color", Style.COLOR_DIM_TEXT)
	b.add_theme_color_override("font_hover_color", Style.COLOR_TEXT)
	b.add_theme_color_override("font_pressed_color", Style.COLOR_TEXT)
	return b

func _make_divider() -> ColorRect:
	var d := ColorRect.new()
	d.custom_minimum_size = Vector2(2, HOTBAR_SLOT - 10)
	d.color = Style.COLOR_BAR_BORDER
	d.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return d

func _icon_tex(path: String) -> Texture2D:
	if path == "":
		return null
	if not _tex_cache.has(path):
		var res := load(path)
		_tex_cache[path] = res if res is Texture2D else null
	return _tex_cache[path]

func _set_icon(icon: TextureRect, fallback: Label, item: Dictionary) -> void:
	var tex := _icon_tex(String(item.get("icon", "")))
	icon.texture = tex
	var emoji := String(item.get("icon_fallback", ""))
	fallback.visible = tex == null and emoji != ""
	fallback.text = emoji

func _vertical_text(s: String) -> String:
	if s.length() <= 1:
		return s
	var out := ""
	for i in s.length():
		out += s[i] + ("\n" if i < s.length() - 1 else "")
	return out

func _set_badges(box: VBoxContainer, item: Dictionary) -> void:
	_clear_children(box)
	if int(item.get("enhanceLevel", 0)) > 0:
		box.add_child(_make_badge("强", Style.COLOR_BADGE_GOLD_BG, Style.COLOR_BADGE_GOLD_TEXT))
	if bool(item.get("_isCrafted", false)) or (item.has("_craftData") and not item["_craftData"].is_empty()):
		box.add_child(_make_badge("改", Style.COLOR_BADGE_CRAFT_BG, Style.COLOR_BADGE_CRAFT_TEXT))
	if bool(item.get("_isEnchanted", false)):
		box.add_child(_make_badge("附", Style.COLOR_BADGE_ENCHANT_BG, Style.COLOR_BADGE_ENCHANT_TEXT))

func _make_badge(text: String, bg: Color, fg: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.custom_minimum_size = Vector2(22, 13)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", 9)
	l.add_theme_color_override("font_color", fg)
	l.add_theme_stylebox_override("normal", Style.make_style(bg, Color(0, 0, 0, 0), 3, 0))
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l

func _clear_children(box: Node) -> void:
	for child in box.get_children():
		child.queue_free()

func make_slot_preview(item: Dictionary) -> Control:
	var p := PanelContainer.new()
	p.custom_minimum_size = Vector2(44, 44)
	p.add_theme_stylebox_override("panel", Style.make_style(Style.COLOR_DRAG_PREVIEW_BG, Style.COLOR_ITEM_BORDER, 6, 2))
	var tr := TextureRect.new()
	tr.texture = _icon_tex(String(item.get("icon", "")))
	tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	p.add_child(tr)
	return p

func make_skill_preview(skill_id: String) -> Control:
	var p := PanelContainer.new()
	p.custom_minimum_size = Vector2(44, 44)
	p.add_theme_stylebox_override("panel", Style.make_style(Style.COLOR_DRAG_PREVIEW_BG, COLOR_SKILL_SLOT_BORDER, 6, 2))
	var def: Dictionary = skillbar.skills.get(skill_id, {})
	var tex := _icon_tex(String(def.get("icon", "")))
	if tex != null:
		var tr := TextureRect.new()
		tr.texture = tex
		tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		p.add_child(tr)
	else:
		var lbl := Label.new()
		lbl.text = String(def.get("icon_fallback", "⚔"))
		lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		lbl.add_theme_font_override("font", Style.make_emoji_font())
		p.add_child(lbl)
	return p

func _flash_status(text: String) -> void:
	if _status_label == null or text == "":
		return
	_status_label.text = text
	_status_label.visible = true
	_status_timer.start(1.6)

func flash_status(text: String) -> void:
	_flash_status(text)

## ---------- 内部控件 ----------

class SkillSlot:
	extends PanelContainer

	var hud
	var key := ""
	var index := 0
	var _press_pos := Vector2.ZERO
	var _pressed := false

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_entered.connect(func() -> void: hud.on_skill_hover(true, key))
		mouse_exited.connect(func() -> void: hud.on_skill_hover(false, key))

	func _gui_input(event: InputEvent) -> void:
		if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_pressed = true
				_press_pos = get_global_mouse_position()
			elif _pressed:
				_pressed = false
				if get_global_mouse_position().distance_to(_press_pos) < 8.0:
					hud.on_skill_click(key)

	func _get_drag_data(_at: Vector2):
		if hud.skillbar == null or index < 0:
			return null
		var skill_id = hud.skillbar.resolve(index)
		if skill_id == "":
			return null
		hud.hide_tooltip()
		hud.set_drag_preview(hud.make_skill_preview(skill_id))
		return {"type": "skill", "slot": index}

	func _can_drop_data(_at: Vector2, data) -> bool:
		var ok := data is Dictionary and (String(data.get("type", "")) == "skill" \
			or String(data.get("type", "")) == "skillbar")
		if ok:
			hud.set_hotbar_drag_over(index, true)
		return ok

	func _drop_data(_at: Vector2, data) -> void:
		hud.set_hotbar_drag_over(index, false)
		hud.drop_on_skill(index, data)

class HotbarSlot:
	extends PanelContainer

	var hud
	var index := 0
	var _press_pos := Vector2.ZERO
	var _pressed := false

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_entered.connect(func() -> void: hud.on_hotbar_mouse(true, index))
		mouse_exited.connect(func() -> void: hud.on_hotbar_mouse(false, index))

	func _gui_input(event: InputEvent) -> void:
		if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_pressed = true
				_press_pos = get_global_mouse_position()
			elif _pressed:
				_pressed = false
				if get_global_mouse_position().distance_to(_press_pos) < 8.0:
					hud.use_hotbar(index)

	func _get_drag_data(_at: Vector2):
		var item = hud.backpack.resolve_hotbar(index)
		if item.is_empty():
			return null
		hud.hide_tooltip()
		hud.set_drag_preview(hud.make_slot_preview(item))
		return {"type": "hotbar", "index": index}

	func _can_drop_data(_at: Vector2, data) -> bool:
		var ok := data is Dictionary and (String(data.get("type", "")) == "hotbar" or String(data.get("type", "")) == "backpack")
		if ok:
			hud.set_hotbar_drag_over(index, true)
		return ok

	func _drop_data(_at: Vector2, data) -> void:
		hud.set_hotbar_drag_over(index, false)
		hud.drop_on_hotbar(index, data)

class BackpackCell:
	extends PanelContainer

	var hud
	var slot := 0
	var _press_pos := Vector2.ZERO
	var _pressed := false

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_entered.connect(func() -> void: hud.on_cell_mouse(true, slot))
		mouse_exited.connect(func() -> void: hud.on_cell_mouse(false, slot))

	func _gui_input(event: InputEvent) -> void:
		if event is InputEventMouseButton:
			if event.button_index == MOUSE_BUTTON_LEFT:
				if event.pressed:
					_pressed = true
					_press_pos = get_global_mouse_position()
				elif _pressed:
					_pressed = false
					if get_global_mouse_position().distance_to(_press_pos) < 8.0:
						hud.on_cell_click_pin(slot)
			elif event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
				hud.use_backpack_item(slot)

	func _get_drag_data(_at: Vector2):
		if hud.backpack == null or hud.backpack.slots[slot] == null:
			return null
		hud.hide_tooltip()
		hud.set_drag_preview(hud.make_slot_preview(hud.backpack.slots[slot]))
		return {"type": "backpack", "slot": slot}

	func _can_drop_data(_at: Vector2, data) -> bool:
		var ok := data is Dictionary and (String(data.get("type", "")) == "backpack" \
			or String(data.get("type", "")) == "hotbar" or String(data.get("type", "")) == "equip" \
			or String(data.get("type", "")) == "skill")
		if ok:
			hud.set_cell_drag_over(slot, true)
		return ok

	func _drop_data(_at: Vector2, data) -> void:
		hud.set_cell_drag_over(slot, false)
		hud.drop_on_backpack(slot, data)

class EquipSlot:
	extends PanelContainer

	var hud
	var key := ""
	var _press_pos := Vector2.ZERO
	var _pressed := false

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_entered.connect(func() -> void: hud.on_equip_mouse(true, key))
		mouse_exited.connect(func() -> void: hud.on_equip_mouse(false, key))

	func _gui_input(event: InputEvent) -> void:
		if event is InputEventMouseButton:
			if event.button_index == MOUSE_BUTTON_LEFT:
				if event.pressed:
					_pressed = true
					_press_pos = get_global_mouse_position()
				elif _pressed:
					_pressed = false
					if get_global_mouse_position().distance_to(_press_pos) < 8.0:
						hud.on_equip_click_pin(key)
			elif event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
				hud.on_equip_right_click(key)

	func _get_drag_data(_at: Vector2):
		if hud.equipment == null or hud.equipment.get_item(key).is_empty() or hud.equipment.is_locked(key):
			return null
		var item: Dictionary = hud.equipment.get_item(key)
		hud.hide_tooltip()
		hud.set_drag_preview(hud.make_slot_preview(item))
		return {"type": "equip", "key": key}

	func _can_drop_data(_at: Vector2, data) -> bool:
		if hud.equipment == null or hud.equipment.is_locked(key):
			return false
		var ok := false
		if data is Dictionary:
			match String(data.get("type", "")):
				"equip":
					ok = true
				"backpack":
					var src := int(data.get("slot", -1))
					ok = hud.backpack != null and src >= 0 and src < hud.backpack.slots.size() \
						and hud.backpack.slots[src] != null \
						and hud.equipment.can_equip_to(key, hud.backpack.slots[src])
		if ok:
			hud.set_equip_drag_over(key, true)
		return ok

	func _drop_data(_at: Vector2, data) -> void:
		hud.set_equip_drag_over(key, false)
		hud.drop_on_equip(key, data)
