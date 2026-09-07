extends Control
## 背包/装备 HUD（从旧 2D 项目 QuickBar + EquipManager 装备背包页迁移到 Godot 4）
##
## 布局（全部代码构建，遵循项目"少手写 .tscn"约定）：
## - 底部快捷栏：1~4 号槽（旧版 itemGroup），数字键/左键使用，拖拽绑定/交换
## - Tab / B：装备与背包面板（旧版 gear-layout）：
##   上 = 装备栏 3x5（15 槽，竖排稀有度/已强化/已改造/已附魔徽章/双手锁定）
##   下 = 背包 16x8 空间格（物品按尺寸占格）
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
const ReferenceStyle := preload("res://ui/backpack_reference_style.gd")
const Spatial := preload("res://ui/spatial_inventory.gd")
var _reference_equip_col: VBoxContainer

const PANEL_BLUR_SHADER := preload("res://assets/ui/shaders/panel_blur.gdshader")

const HOTBAR_SIZE := 4
const SKILL_SIZE := 3
const SKILL_KEY_HINTS := ["Q", "E", "X"]
const SKILL_KEYCODES := [KEY_Q, KEY_E, KEY_X]
# 旧版技能位配色（quick-slot.skill：#6b5d4f / #3d342b；待 palette.json 落地后并入 style.gd）
const INV_COLS := Spatial.COLUMNS
const HOTBAR_SLOT := 52
const CELL_SLOT := 52
var _drag_origin_rect := Rect2()
var _drag_active := false

const EQUIP_SLOT_SIZE := Vector2(80, 32)
const EQUIP_COLS := 3
const BAR_PAD := 8
const BAR_GAP := 8
const PANEL_MARGIN := 0
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
var _grid: Control
var _cells: Array = []
var _equip_grid: GridContainer
var _equip_cells := {}
var _panel_title: Label
var _tab_status: Button
var _tab_equip: Button
var _tab_skill: Button
var _tab_codex: Button
var _page_stack: Control
var _equip_page: VBoxContainer
var _status_page: Control
var _skill_page: Control
var _codex_page: Control
var _current_tab := "equip"
var _panel_root: Control
var _panel: PanelContainer
var _panel_w := 720.0
var _panel_anim: Tween
var _panel_open := false
var _split_dialog: ConfirmationDialog
var _split_name: Label
var _split_slider: HSlider
var _split_count: SpinBox
var _split_instance := ""
var _context: PopupMenu
var _context_instance := ""
var _discard_dialog: ConfirmationDialog
var _discard_instance := ""
var _blur_size_synced := false
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
var _cropped_tex_cache := {}
var _cd_last := {}
var _hovered_cell := -1
var _hovered_hotbar := -1
var _hovered_equip := ""
var _drag_over_cell := -1
var _drag_over_cells: Array[int] = []
var _drag_over_valid := true
var _drag_over_hotbar := -1
var _drag_over_equip := ""

var _s_hotbar_empty: StyleBox
var _s_hotbar_item: StyleBox
var _s_hotbar_hover: StyleBox
var _s_skill_empty: StyleBox
var _s_cell_empty: StyleBox
var _s_cell_item_tile: StyleBox
var _s_cell_item: StyleBox
var _s_cell_empty_hover: StyleBox
var _s_cell_item_hover: StyleBox
var _s_cell_drag_over: StyleBox
var _s_cell_drag_invalid: StyleBox
var _s_equip_empty: StyleBox
var _s_equip_equipped: StyleBox
var _s_equip_hover: StyleBox
var _s_equip_locked: StyleBox

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_panel_w = get_viewport_rect().size.x * PANEL_W_RATIO
	theme = Style.make_theme()
	_font_title = Style.make_font(700)
	_font_section = Style.make_font(400)
	_font_mono = Style.make_mono_font(600)
	# 贴图化槽位：panel_slot 底纹 + modulate 状态色（hover=金、拖放=强金、装备=暖亮、锁定=灰）
	# 快捷栏/技能槽 = 深色 HUD 模块（原项目 quick-slot：深底 + 2px 边框 + 8px 圆角）
	_s_hotbar_empty = Style.make_style(Style.COLOR_HUD_SLOT_BG, Style.COLOR_HUD_BORDER, 8, 2)
	_s_hotbar_item = Style.make_style(Style.COLOR_HUD_SLOT_BG, Style.COLOR_HUD_BORDER, 8, 2)
	_s_hotbar_hover = Style.make_style(Style.COLOR_HUD_SLOT_HOVER, Style.COLOR_HUD_SLOT_HOVER_BORDER, 8, 2)
	_s_skill_empty = Style.make_style(Style.COLOR_HUD_SLOT_BG, Style.COLOR_HUD_BORDER, 8, 2)
	_s_cell_empty = ReferenceStyle.slot_surface(ReferenceStyle.BACKPACK_EMPTY_TOP, ReferenceStyle.BACKPACK_EMPTY_BOTTOM, ReferenceStyle.BACKPACK_EMPTY_LIGHT_EDGE, ReferenceStyle.BACKPACK_EMPTY_DARK_EDGE)
	_s_cell_item_tile = ReferenceStyle.slot_surface(ReferenceStyle.BACKPACK_ITEM_TILE_TOP, ReferenceStyle.BACKPACK_ITEM_TILE_BOTTOM, ReferenceStyle.BACKPACK_ITEM_DARK_EDGE, ReferenceStyle.BACKPACK_ITEM_LIGHT_EDGE)
	_s_cell_item = ReferenceStyle.slot_surface(ReferenceStyle.BACKPACK_ITEM_TOP, ReferenceStyle.BACKPACK_ITEM_BOTTOM, ReferenceStyle.BACKPACK_ITEM_DARK_EDGE, ReferenceStyle.BACKPACK_ITEM_LIGHT_EDGE)
	_s_cell_empty_hover = ReferenceStyle.slot_surface(ReferenceStyle.BACKPACK_EMPTY_HOVER_TOP, ReferenceStyle.BACKPACK_EMPTY_HOVER_BOTTOM, ReferenceStyle.BACKPACK_EMPTY_LIGHT_EDGE, ReferenceStyle.BACKPACK_ITEM_LIGHT_EDGE)
	_s_cell_item_hover = ReferenceStyle.slot_surface(ReferenceStyle.BACKPACK_ITEM_TOP, ReferenceStyle.BACKPACK_ITEM_HOVER_BOTTOM, ReferenceStyle.BACKPACK_ITEM_DARK_EDGE, ReferenceStyle.BACKPACK_EMPTY_LIGHT_EDGE)
	_s_cell_drag_over = ReferenceStyle.slot_surface(ReferenceStyle.BACKPACK_ITEM_TOP, ReferenceStyle.BACKPACK_DRAG_BOTTOM, ReferenceStyle.BACKPACK_ITEM_DARK_EDGE, ReferenceStyle.BACKPACK_EMPTY_LIGHT_EDGE)
	_s_cell_drag_invalid = ReferenceStyle.slot_surface(ReferenceStyle.BACKPACK_INVALID_TOP, ReferenceStyle.BACKPACK_INVALID_BOTTOM, ReferenceStyle.BACKPACK_INVALID_DARK_EDGE, ReferenceStyle.BACKPACK_INVALID_LIGHT_EDGE)
	_s_equip_empty = ReferenceStyle.surface(ReferenceStyle.EQUIP_EMPTY_TOP, ReferenceStyle.EQUIP_EMPTY_BOTTOM, ReferenceStyle.EQUIP_EMPTY_BORDER)
	_s_equip_equipped = ReferenceStyle.surface(ReferenceStyle.EQUIP_EQUIPPED_TOP, ReferenceStyle.EQUIP_EQUIPPED_BOTTOM, ReferenceStyle.EQUIP_EQUIPPED_BORDER)
	_s_equip_hover = ReferenceStyle.surface(ReferenceStyle.EQUIP_HOVER_TOP, ReferenceStyle.EQUIP_HOVER_BOTTOM, ReferenceStyle.EQUIP_HOVER_BORDER)
	_s_equip_locked = ReferenceStyle.surface(ReferenceStyle.EQUIP_LOCKED_TOP, ReferenceStyle.EQUIP_LOCKED_BOTTOM, ReferenceStyle.EQUIP_LOCKED_BORDER)
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
	_build_inventory_actions()
	get_viewport().size_changed.connect(_resize_inventory)
	_resize_inventory()

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
	_codex_page = Control.new()
	_codex_page.name = "CodexPage"
	_codex_page.visible = false
	_codex_page.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_page_stack.add_child(_codex_page)
	var codex_scroll := Style.make_scroll_container()
	codex_scroll.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_codex_page.add_child(codex_scroll)
	var codex_v := VBoxContainer.new()
	codex_v.add_theme_constant_override("separation", 8)
	codex_scroll.add_child(codex_v)
	var codex_title := _make_label(codex_v, "图鉴", 20, Style.COLOR_TITLE_TEXT, Vector2(24, 18))
	codex_title.add_theme_font_override("font", _font_title)
	_make_label(codex_v, "装备图鉴 / 怪物图鉴系统移植中……", 14, Style.COLOR_DIM_TEXT, Vector2(26, 52))
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
		_count_label.text = "%d/%d 格 · %d 件" % [backpack.used_cell_count(), backpack.max_slots, backpack.item_count()]

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
			icon.texture = _icon_tex(preload("res://ui/item_icon.gd").path(item))
			var count: int = item.get("stack", 0)
			stack.text = str(count)
			stack.add_theme_color_override("font_color", Style.COLOR_ZERO_TEXT if count <= 0 else Style.COLOR_TEXT)
			stack.add_theme_font_override("font", _font_mono)
			slot.add_theme_stylebox_override("panel", _s_hotbar_hover if i == _hovered_hotbar else _s_hotbar_item)
			slot.tooltip_text = ""

func _refresh_grid() -> void:
	_sync_grid_cells()
	_layout_grid_geometry()
	var occupied := Spatial.occupancy(backpack.slots)
	for i in _cells.size():
		var cell: BackpackCell = _cells[i]
		var occupied_slot: int = occupied[i]
		var footprint := Spatial.footprint(backpack.slots[i]) if occupied_slot == i else Vector2i.ONE
		var icon := cell.get_node("Content/Icon") as TextureRect
		var fallback := cell.get_node("Content/Fallback") as Label
		var name_lbl := cell.get_node("Content/Name") as Label
		var stack_lbl := cell.get_node("Content/Stack") as Label
		var rarity_lbl := cell.get_node("Content/Rarity") as ReferenceStyle.VerticalBadge
		ReferenceStyle.hide_item_badges(cell.get_node("Content"))
		name_lbl.anchor_right = 1.0
		name_lbl.offset_right = -4
		rarity_lbl.visible = false
		rarity_lbl.text = ""
		rarity_lbl.remove_theme_stylebox_override("normal")
		cell.tooltip_text = ""
		if occupied_slot >= 0 and occupied_slot != i:
			icon.texture = null
			icon.modulate.a = 1.0
			fallback.visible = false
			fallback.modulate.a = 1.0
			name_lbl.text = ""
			stack_lbl.text = ""
			cell.add_theme_stylebox_override("panel", _drag_cell_style(i, _s_cell_item_tile))
			continue
		if backpack.slots[i] == null:
			icon.texture = null
			icon.modulate.a = 1.0
			fallback.visible = false
			fallback.modulate.a = 1.0
			name_lbl.text = ""
			stack_lbl.text = ""
			cell.add_theme_stylebox_override("panel", _drag_cell_style(i, _s_cell_empty_hover if i == _hovered_cell else _s_cell_empty))
		else:
			var item: Dictionary = backpack.slots[i]
			_set_icon(icon, fallback, item, true)
			icon.modulate.a = 0.82
			fallback.modulate.a = 0.82
			var compact := footprint == Vector2i.ONE
			var firearm := _is_firearm(item)
			name_lbl.visible = not compact and not firearm
			name_lbl.text = String(item.get("name", "")) if name_lbl.visible else ""
			icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			icon.anchor_left = 0.0 if firearm else (0.12 if compact else 0.25)
			icon.anchor_right = 1.0 if firearm else (0.88 if compact else 0.44)
			icon.anchor_top = 0.0
			icon.anchor_bottom = 1.0
			icon.offset_left = 0
			icon.offset_right = 0
			icon.offset_top = 0 if firearm else 6
			icon.offset_bottom = 0 if firearm else -6
			fallback.anchor_left = 0.0 if firearm else (0.12 if compact else 0.25)
			fallback.anchor_right = 1.0 if firearm else (0.88 if compact else 0.4)
			var count: int = item.get("stack", 1)
			stack_lbl.text = str(count) if count > 1 else ""
			cell.add_theme_stylebox_override("panel", _drag_cell_style(i, _s_cell_item_hover if i == _hovered_cell else _s_cell_item))

func _drag_cell_style(cell_index: int, normal: StyleBox) -> StyleBox:
	if _drag_over_cells.has(cell_index):
		return _s_cell_drag_over if _drag_over_valid else _s_cell_drag_invalid
	return normal

func _grid_cell_side() -> float:
	if _grid == null:
		return CELL_SLOT * 0.5
	return maxf(CELL_SLOT * 0.5, _grid.size.x / float(INV_COLS))

func _layout_grid_geometry() -> void:
	if _grid == null or backpack == null or _cells.is_empty():
		return
	var cell_side := _grid_cell_side()
	_grid.custom_minimum_size.y = cell_side * Spatial.ROWS
	var occupied := Spatial.occupancy(backpack.slots)
	var anchors: Array[Control] = []
	for i in _cells.size():
		var cell: BackpackCell = _cells[i]
		var occupied_slot: int = occupied[i]
		cell.position = Vector2((i % INV_COLS) * cell_side, (i / INV_COLS) * cell_side)
		cell.visible = true
		cell.mouse_filter = Control.MOUSE_FILTER_IGNORE if occupied_slot >= 0 and occupied_slot != i else Control.MOUSE_FILTER_STOP
		var footprint := Spatial.footprint(backpack.slots[i]) if occupied_slot == i else Vector2i.ONE
		var cell_size := Vector2(footprint.x * cell_side, footprint.y * cell_side)
		cell.custom_minimum_size = cell_size
		cell.size = cell_size
		if occupied_slot == i:
			anchors.append(cell)
	for cell in anchors:
		_grid.move_child(cell, _grid.get_child_count() - 1)

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
		var rarity_lbl := cell.get_node("Content/Rarity") as ReferenceStyle.VerticalBadge
		var content := cell.get_node("Content") as Control
		ReferenceStyle.update_item_badges(content, item, true)
		var lock := cell.get_node("Content/Lock") as Control
		name_lbl.add_theme_font_override("font", _make_item_name_font())
		name_lbl.anchor_left = 0.0 if item.is_empty() else 0.4
		name_lbl.anchor_right = 1.0
		name_lbl.offset_left = 8 if item.is_empty() else 2
		name_lbl.offset_right = -ReferenceStyle.name_right_inset(content, true)
		name_lbl.offset_top = 0
		name_lbl.offset_bottom = 0
		name_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		ReferenceStyle.item_shadow(name_lbl, item.is_empty())
		var locked := equipment.is_locked(key)
		lock.visible = locked
		cell.modulate.a = 0.6 if locked else 1.0
		cell.mouse_filter = Control.MOUSE_FILTER_IGNORE if locked else Control.MOUSE_FILTER_STOP
		icon.material = ReferenceStyle.locked_icon_material() if locked else null
		icon.modulate.a = 0.5 if locked else 1.0
		fallback.modulate.a = 0.5 if locked else 1.0
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
			name_lbl.add_theme_color_override("font_color", ReferenceStyle.EQUIP_TEXT_MUTED if locked else ReferenceStyle.EQUIP_TEXT)
			rarity_lbl.text = ""
			rarity_lbl.remove_theme_stylebox_override("normal")
		else:
			_set_icon(icon, fallback, item, false)
			name_lbl.text = String(item.get("name", ""))
			name_lbl.add_theme_color_override("font_color", ReferenceStyle.EQUIP_TEXT_MUTED if locked else ReferenceStyle.EQUIP_TEXT)
			var rarity_key := String(item.get("rarity", "common"))
			rarity_lbl.text = _vertical_text(Style.rarity_label(rarity_key))
			rarity_lbl.add_theme_stylebox_override("normal", Style.make_style(ReferenceStyle.RARITY_BADGES.get(rarity_key, Color.GRAY), Color(0, 0, 0, 0), 3, 0))

## ---------- 输入 ----------

## 面板开关键放 _input（早于 GUI 焦点导航，Tab 不会被焦点吃掉；K 对齐旧版技能体系键）
func _input(event: InputEvent) -> void:
	if event is InputEventKey and get_viewport().gui_is_dragging():
		get_viewport().set_input_as_handled()
		if event.pressed and event.keycode == KEY_ESCAPE:
			get_viewport().gui_cancel_drag()
		return
	if _split_dialog != null and (_split_dialog.visible or _discard_dialog.visible or _context.visible):
		return
	var hud := get_node_or_null("/root/HUD")
	if hud != null:
		for ref in hud._inventory_panels.values():
			var npc: Node = ref.get_ref()
			if npc != null and npc.is_open():
				return
	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE and _panel_open:
		get_viewport().set_input_as_handled()
		if get_viewport().gui_is_dragging():
			get_viewport().gui_cancel_drag()
		elif _tooltip != null and _tooltip.visible:
			hide_tooltip()
		else:
			set_panel_open(false)
		return
	# Codex search and level fields own text/navigation keys; Esc still closes above.
	if _panel_open and _current_tab == "codex":
		var focus := get_viewport().gui_get_focus_owner()
		if focus is LineEdit and _codex_page.is_ancestor_of(focus):
			return
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
				var should_open := not (_panel_open and _current_tab == "skill")
				set_tab("skill")
				set_panel_open(should_open)
			KEY_B:
				get_viewport().set_input_as_handled()
				# 通用语义：任何界面按 B 都打开"装备与背包"页（已开则关闭）
				if _panel_open and _current_tab == "equip":
					set_panel_open(false)
				else:
					set_tab("equip")
					set_panel_open(true)
			KEY_CAPSLOCK:
				get_viewport().set_input_as_handled()
				var should_open := not (_panel_open and _current_tab == "status")
				set_tab("status")
				set_panel_open(should_open)

func _unhandled_input(event: InputEvent) -> void:
	var host := get_node_or_null("/root/HUD")
	if host != null:
		for ref in host._inventory_panels.values():
			var npc = ref.get_ref()
			if npc != null and npc.is_open():
				return
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_1, KEY_2, KEY_3, KEY_4:
				use_hotbar(event.keycode - KEY_1)
			KEY_Q, KEY_E, KEY_X:
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
	var result := backpack.use_hotbar(index, player, _player_status)
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
		# 快捷栏技能位不显示图标（用户定稿：原项目快捷栏无图标，键位+冷却即可）
		icon.texture = null
		icon.visible = false
		var id := skillbar.resolve(i)
		if id == "":
			dim.visible = false
			slot.add_theme_stylebox_override("panel", _s_skill_empty)
		else:
			var def: Dictionary = skillbar.skills.get(id, {})
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
		cd.color = Style.COLOR_CD_FLASH
		var tw := create_tween()
		tw.tween_property(cd, "color", Style.COLOR_CD_DIM, 0.18)
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
	var host := get_node_or_null("/root/HUD")
	var item: Dictionary = backpack.slots[slot]
	if host != null:
		for key in ["enchant", "shop", "enhance", "craft", "warehouse", "fusion"]:
			if not host._inventory_panels.has(key):
				continue
			var active: Node = host._inventory_panels[key].get_ref()
			if active == null or not active.is_open():
				continue
			match key:
				"enchant":
					if not str(item.get("scroll_id", "")).is_empty():
						active._place_scroll("backpack", slot)
					else:
						active._place_equip("backpack", slot)
				"shop": active._add_to_sell(slot)
				"enhance", "craft":
					if not preload("res://ui/item_rules.gd").is_gold(item):
						active._equip_from_backpack(slot)
				"warehouse": active._store_item(slot)
				"fusion": active._place_from_backpack(slot)
			return
	if String(item.get("category", "")).begins_with("weapon") or String(item.get("equipSlot", "")) != "":
		# 装备类物品右键 = 装备（旧版右键菜单"装备"）
		if equipment != null and equipment.equip_from_backpack(slot):
			return
		_flash_status("无法装备")
		return
	var player := _get_player()
	if player == null or bool(player.get("is_dead")):
		return
	var result := backpack.use_item(String(item.get("instance_id", "")), player, _player_status)
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
		_panel_anim.parallel().tween_method(func(t: float): _apply_panel_slide(preload("res://ui/source_panel_motion.gd").standard(t)), 0.0, 1.0, 0.25)
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	else:
		_panel_anim = create_tween()
		_panel_anim.tween_property(dim, "modulate:a", 0.0, 0.16)
		_panel_anim.parallel().tween_method(func(t: float): _apply_panel_slide(1.0 - preload("res://ui/source_panel_motion.gd").standard(t)), 0.0, 1.0, 0.25)
		_panel_anim.tween_callback(func() -> void: _panel_root.visible = false)
		var player := _get_player()
		if player == null or not bool(player.get("is_dead")):
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	hide_tooltip()

## ---------- 页签（角色状态 / 装备背包，复刻旧版 SystemUI 页签） ----------

func set_tab(tab: String) -> void:
	if tab != "status" and tab != "equip" and tab != "skill" and tab != "codex":
		return
	_current_tab = tab
	if _status_page != null:
		_status_page.visible = tab == "status"
	if _equip_page != null:
		_equip_page.visible = tab == "equip"
	if _skill_page != null:
		_skill_page.visible = tab == "skill"
	if _codex_page != null:
		_codex_page.visible = tab == "codex"
		if tab == "codex": _codex_page.refresh()
	if _panel_title != null:
		_panel_title.text = "角色状态" if tab == "status" else (
			"装备与背包" if tab == "equip" else ("技能" if tab == "skill" else "图鉴"))
	_update_tab_styles()

func _update_tab_styles() -> void:
	if _tab_status == null or _tab_equip == null or _tab_skill == null or _tab_codex == null:
		return
	_tab_status.add_theme_stylebox_override("normal", _tab_style(_current_tab == "status"))
	_tab_equip.add_theme_stylebox_override("normal", _tab_style(_current_tab == "equip"))
	_tab_skill.add_theme_stylebox_override("normal", _tab_style(_current_tab == "skill"))
	_tab_codex.add_theme_stylebox_override("normal", _tab_style(_current_tab == "codex"))
	_tab_status.add_theme_color_override("font_color", Style.COLOR_TEXT if _current_tab == "status" else Color("#888888"))
	_tab_equip.add_theme_color_override("font_color", Style.COLOR_TEXT if _current_tab == "equip" else Color("#888888"))
	_tab_skill.add_theme_color_override("font_color", Style.COLOR_TEXT if _current_tab == "skill" else Color("#888888"))
	_tab_codex.add_theme_color_override("font_color", Style.COLOR_TEXT if _current_tab == "codex" else Color("#888888"))
	_tab_status.add_theme_font_override("font", _font_title if _current_tab == "status" else _font_section)
	_tab_equip.add_theme_font_override("font", _font_title if _current_tab == "equip" else _font_section)
	_tab_skill.add_theme_font_override("font", _font_title if _current_tab == "skill" else _font_section)
	_tab_codex.add_theme_font_override("font", _font_title if _current_tab == "codex" else _font_section)

func _tab_style(active: bool) -> StyleBox:
	if active:
		# 原项目 panel-tab：底部 3px 下划线 + 半透明底（灰白/暗金主题自动取色）
		var sb := StyleBoxFlat.new()
		sb.bg_color = ReferenceStyle.PANEL_TAB_BG
		sb.set_corner_radius_all(0)
		sb.set_border_width_all(0)
		sb.border_color = ReferenceStyle.PANEL_TAB_BORDER
		sb.border_width_bottom = 5
		return sb
	return Style.make_style(Style.COLOR_TRANSPARENT, Style.COLOR_TRANSPARENT, 0, 0)

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

# Resolve the instance again at release: sorting/equipment changes can move the source.
func _drag_backpack_slot(data: Dictionary) -> int:
	var identity := str(data.get("item", {}).get("instance_id", ""))
	return backpack.find_slot(identity) if not identity.is_empty() else int(data.get("slot", -1))

func _drag_equip_key(data: Dictionary) -> String:
	var identity := str(data.get("item", {}).get("instance_id", ""))
	if identity.is_empty():
		return str(data.get("key", ""))
	for key in equipment.SLOT_ORDER:
		if str(equipment.get_item(key).get("instance_id", "")) == identity:
			return key
	return ""

func drop_on_hotbar(index: int, data: Dictionary) -> void:
	if backpack == null:
		return
	match String(data.get("type", "")):
		"hotbar":
			backpack.swap_hotbar(index, int(data.get("index", -1)))
		"backpack":
			var src := _drag_backpack_slot(data)
			if src >= 0 and src < backpack.slots.size() and backpack.slots[src] != null:
				backpack.bind_hotbar(index, String(backpack.slots[src].get("instance_id", "")))

func drop_on_backpack(slot: int, data: Dictionary) -> void:
	if backpack == null:
		return
	match String(data.get("type", "")):
		"panel_item":
			preload("res://ui/panel_item_transfer.gd").to_backpack(data, backpack, slot)
		"npc_item":
			var host := get_node_or_null("/root/HUD")
			if data.get("source", "") == "warehouse" and host != null:
				host.warehouse.retrieve_to_backpack(backpack, host.warehouse.find_instance(data.get("item", {})), slot)
			else:
				backpack.swap_items(backpack.find_slot(str(data.get("item", {}).get("instance_id", ""))), slot)
		"backpack":
			backpack.swap_items(_drag_backpack_slot(data), slot)
		"hotbar":
			backpack.unbind_hotbar(int(data.get("index", -1)))
		"equip":
			if equipment != null:
				equipment.unequip(_drag_equip_key(data), slot)
		"skill":
			if skillbar != null:
				skillbar.unassign(int(data.get("slot", -1)))

func drop_on_equip(key: String, data: Dictionary) -> void:
	if equipment != null and equipment.is_locked(key):
		return
	if equipment == null:
		return
	match String(data.get("type", "")):
		"panel_item":
			preload("res://ui/panel_item_transfer.gd").to_equipment(data, equipment, key)
		"equip":
			equipment.swap_equip(key, _drag_equip_key(data))
		"backpack":
			equipment.equip_to_slot(key, _drag_backpack_slot(data))

## ---------- 动画回调 ----------

func _on_item_added(slot: int) -> void:
	if slot >= 0 and slot < _cells.size():
		_pop_cell(slot)

func _on_bound(index: int) -> void:
	if index >= 0 and index < _hotbar_slots.size():
		_flash_hotbar(index)

func _on_equipped(key: String) -> void:
	if Style.theme_active() == "cold_steel":
		return
	if _equip_cells.has(key):
		var cell: EquipSlot = _equip_cells[key]
		cell.pivot_offset = EQUIP_SLOT_SIZE * 0.5
		var tw := create_tween()
		tw.tween_property(cell, "scale", Vector2(1.12, 1.12), 0.14)
		tw.tween_property(cell, "scale", Vector2.ONE, 0.16).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

func _pop_cell(slot: int) -> void:
	if Style.theme_active() == "cold_steel":
		return
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
	overlay.color = Style.COLOR_CD_FLASH
	var tw := create_tween()
	tw.tween_property(overlay, "color", Style.COLOR_CD_DIM, 0.18)

## ---------- 悬停 / 拖拽高亮 ----------

func on_cell_mouse(enter: bool, slot: int) -> void:
	if slot < 0 or slot >= _cells.size():
		return
	_hovered_cell = slot if enter else -1
	var cell: BackpackCell = _cells[slot]
	if enter:
		var hover_style := _s_cell_item_hover if backpack != null and backpack.slots[slot] != null else _s_cell_empty_hover
		cell.add_theme_stylebox_override("panel", _s_cell_drag_over if slot == _drag_over_cell else hover_style)
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

func _drag_item(data: Dictionary) -> Dictionary:
	var direct = data.get("item", {})
	if direct is Dictionary and not direct.is_empty():
		return direct
	match String(data.get("type", "")):
		"panel_item":
			var source := preload("res://ui/panel_item_transfer.gd").resolve(data)
			return source.item if not source.is_empty() else {}
		"hotbar":
			return backpack.resolve_hotbar(int(data.get("index", -1))) if backpack != null else {}
	return {}

func grid_cell_from_local(control_slot: int, local_position: Vector2) -> int:
	var origin := Spatial.anchor_position(control_slot)
	var offset := Vector2i(floori(local_position.x / _grid_cell_side()), floori(local_position.y / _grid_cell_side()))
	var cell := origin + offset
	if cell.x < 0 or cell.x >= Spatial.COLUMNS or cell.y < 0 or cell.y >= Spatial.ROWS:
		return -1
	return Spatial.anchor_index(cell)

func drag_target_anchor(hovered_cell: int, data: Dictionary) -> int:
	if hovered_cell < 0:
		return -1
	var target := _drag_target_position(hovered_cell, data)
	if target.x < 0 or target.y < 0 or target.x >= Spatial.COLUMNS or target.y >= Spatial.ROWS:
		return -1
	return Spatial.anchor_index(target)

func _drag_target_position(hovered_cell: int, data: Dictionary) -> Vector2i:
	if hovered_cell < 0:
		return Vector2i(-Spatial.COLUMNS, -Spatial.ROWS)
	var grab: Vector2i = data.get("grab_cell", Vector2i.ZERO)
	return Spatial.anchor_position(hovered_cell) - grab

func _footprint_cells(item: Dictionary, origin: Vector2i) -> Array[int]:
	var result: Array[int] = []
	if item.is_empty():
		return result
	var footprint := Spatial.footprint(item)
	for y in footprint.y:
		for x in footprint.x:
			var point := origin + Vector2i(x, y)
			if point.x >= 0 and point.x < Spatial.COLUMNS and point.y >= 0 and point.y < Spatial.ROWS:
				result.append(Spatial.anchor_index(point))
	return result

func _drag_target_is_valid(item: Dictionary, anchor: int, data: Dictionary) -> bool:
	if backpack == null or item.is_empty() or anchor < 0:
		return false
	if String(data.get("type", "")) == "backpack":
		var source_anchor := _drag_backpack_slot(data)
		return source_anchor >= 0 and not Spatial.move(backpack.slots, source_anchor, anchor).is_empty()
	return Spatial.can_place(backpack.slots, item, anchor)

func set_cell_drag_over(hovered_cell: int, on: bool, data: Dictionary = {}) -> void:
	if not on:
		_drag_over_cell = -1
		_drag_over_cells.clear()
		_drag_over_valid = true
		_refresh_grid()
		return
	var item := _drag_item(data)
	var target_position := _drag_target_position(hovered_cell, data)
	var anchor := drag_target_anchor(hovered_cell, data)
	_drag_over_cell = anchor
	_drag_over_cells = _footprint_cells(item, target_position)
	_drag_over_valid = _drag_target_is_valid(item, anchor, data)
	_refresh_grid()
	_drag_clear_timer.start(0.25)

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
	if equipment != null and equipment.is_locked(key):
		return
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
	_drag_over_cells.clear()
	_drag_over_valid = true
	_drag_over_hotbar = -1
	_drag_over_equip = ""
	_refresh_grid()
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
	_tooltip.z_index = 160  # Above the backpack shade (110) and quickbar (150).
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
	_tooltip.place_at(at)

## ---------- 冷却 ----------

func _process(delta: float) -> void:
	if _drag_active and _hotbar_root != null and not _drag_origin_rect.has_point(get_global_mouse_position()):
		_hotbar_root.z_index = 150
	if not _blur_size_synced and _panel_root != null:
		var blur := _panel_root.get_node_or_null("Panel/Content/Blur") as ColorRect
		if blur != null and blur.size.x > 0.0:
			var mat := blur.material as ShaderMaterial
			if mat != null:
				mat.set_shader_parameter("node_size", blur.size)
				_blur_size_synced = true
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
			overlay.color = Style.COLOR_CD_DIM
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
	# 快捷栏容器：半透明玻璃底（与面板毛玻璃一致）
	bar.add_theme_stylebox_override("panel",
		Style.make_style(Color(Style.COLOR_HUD_BG, 0.35), Color(Style.COLOR_HUD_BORDER, 0.5), 12, 2))
	bar.add_theme_constant_override("margin_left", BAR_PAD)
	bar.add_theme_constant_override("margin_right", BAR_PAD)
	bar.add_theme_constant_override("margin_top", BAR_PAD)
	bar.add_theme_constant_override("margin_bottom", BAR_PAD)
	bar.z_index = 100  # 快捷栏通用置顶：任何界面（含面板打开）都可见
	add_child(bar)
	_hotbar_root = HBoxContainer.new()
	_hotbar_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hotbar_root.add_theme_constant_override("separation", BAR_GAP)
	bar.add_child(_hotbar_root)
	# 技能组（旧版 skillGroup：Q/E/X 占位，技能系统未移植前为空槽）
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
		icon.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
		icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		content.add_child(icon)
		var key := _make_label(content, SKILL_KEY_HINTS[i], 11, Style.COLOR_HUD_GOLD, Vector2(HOTBAR_SLOT - 14, HOTBAR_SLOT - 17))
		key.name = "Key"
		var blink := create_tween()
		blink.set_loops()
		blink.tween_property(key, "modulate:a", 0.35, 0.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		blink.tween_property(key, "modulate:a", 1.0, 0.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		var cd := ColorRect.new()
		cd.name = "CD"
		cd.color = Style.COLOR_CD_DIM
		cd.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cd.anchor_left = 0.0
		cd.anchor_right = 1.0
		cd.anchor_top = 1.0
		cd.anchor_bottom = 1.0
		cd.offset_bottom = 0
		cd.offset_top = 0
		cd.visible = false
		content.add_child(cd)
		var cd_text := _make_label(content, "", 10, Style.COLOR_HUD_TEXT, Vector2(HOTBAR_SLOT - 18, HOTBAR_SLOT - 28))
		cd_text.name = "CDText"
		cd_text.add_theme_font_override("font", _font_mono)
		cd_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		cd_text.visible = false
		var dim := ColorRect.new()
		dim.name = "Dim"
		dim.color = Style.COLOR_CD_DIM
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
	var sp_key := _make_label(sp_content, "右击", 10, Style.COLOR_HUD_GOLD, Vector2(0, HOTBAR_SLOT - 17))
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
		icon.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
		icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 3)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		content.add_child(icon)
		var stack := _make_label(content, "", 12, Style.COLOR_HUD_TEXT, Vector2(3, HOTBAR_SLOT - 18))
		stack.name = "Stack"
		stack.add_theme_font_override("font", _font_mono)
		var key := _make_label(content, str(i + 1), 11, Style.COLOR_HUD_GOLD, Vector2(HOTBAR_SLOT - 14, HOTBAR_SLOT - 17))
		key.name = "Key"
		var blink := create_tween()
		blink.set_loops()
		blink.tween_property(key, "modulate:a", 0.35, 0.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		blink.tween_property(key, "modulate:a", 1.0, 0.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		var cd := ColorRect.new()
		cd.name = "CD"
		cd.color = Style.COLOR_CD_DIM
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
	_panel_root = preload("res://ui/inventory_scene_drop.gd").new()
	_panel_root.backpack_view = self
	_panel_root.name = "BackpackPanel"
	_panel_root.mouse_filter = Control.MOUSE_FILTER_STOP
	_panel_root.z_index = 110  # 背包面板位于快捷栏(z100)之上
	_panel_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_panel_root.visible = false
	add_child(_panel_root)
	var dim := ColorRect.new()
	dim.name = "Dim"
	dim.color = Color.WHITE
	var defocus := ShaderMaterial.new()
	defocus.shader = PANEL_BLUR_SHADER
	defocus.set_shader_parameter("radius", 3.0)
	defocus.set_shader_parameter("tint_color", Vector3.ZERO)
	defocus.set_shader_parameter("tint_amount", 0.65)
	defocus.set_shader_parameter("alpha", 1.0)
	defocus.set_shader_parameter("corner_radius", 0.0)
	defocus.set_shader_parameter("node_size", get_viewport_rect().size)
	dim.material = defocus
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_panel_root.add_child(dim)
	_panel = PanelContainer.new()
	_panel.name = "Panel"
	_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	# 主面板：透明底 + 细框投影，毛玻璃完全由内部 Blur 层提供
	var shell := ReferenceStyle.surface("#151a1e", "#0a0e11", "#71828b", 0, 0)
	shell.content_margin_left = 3
	_panel.add_theme_stylebox_override("panel", shell)
	_panel_root.add_child(_panel)
	var left_border := ColorRect.new()
	left_border.color = ReferenceStyle.PANEL_DIVIDER
	left_border.anchor_bottom = 1.0
	left_border.offset_right = 3
	left_border.mouse_filter = Control.MOUSE_FILTER_IGNORE

	var content := Control.new()
	content.name = "Content"
	content.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel.add_child(content)
	left_border.offset_left = -3
	left_border.offset_right = 0
	content.add_child(left_border)
	var blur := ColorRect.new()
	blur.name = "Blur"
	blur.mouse_filter = Control.MOUSE_FILTER_IGNORE
	blur.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var mat := ShaderMaterial.new()
	mat.shader = PANEL_BLUR_SHADER
	if Style.theme_active() == "gray_white":
		mat.set_shader_parameter("tint_color", Style.COLOR_BLUR_TINT)
		mat.set_shader_parameter("tint_amount", 0.42)
		mat.set_shader_parameter("alpha", 0.58)
	blur.material = mat
	blur.visible = Style.theme_active() != "cold_steel"
	content.add_child(blur)
	var tex_layer := Panel.new()
	tex_layer.name = "GlassTex"
	tex_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	tex_layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var tex_style := Style.make_texture_panel_style()
	tex_style.modulate_color = Color(Style.THEME_WHITE, 0.06)
	tex_layer.add_theme_stylebox_override("panel", tex_style)
	content.add_child(tex_layer)
	tex_layer.visible = Style.theme_active() != "cold_steel"
	var margin := MarginContainer.new()
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_theme_constant_override("margin_left", PANEL_MARGIN)
	margin.add_theme_constant_override("margin_right", PANEL_MARGIN)
	margin.add_theme_constant_override("margin_top", PANEL_MARGIN)
	margin.add_theme_constant_override("margin_bottom", PANEL_MARGIN)
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	content.add_child(margin)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 0)
	vbox.alignment = BoxContainer.ALIGNMENT_BEGIN
	margin.add_child(vbox)
	# 标题栏色块（参考图组件：色块底 + 内边距，纯视觉不改交互）
	var title_bar := PanelContainer.new()
	title_bar.custom_minimum_size.y = 56
	var tsb := ReferenceStyle.surface("#29323a", "#1a2127", "#71828b", 0, 0)
	tsb.content_margin_left = 20
	tsb.content_margin_right = 20
	tsb.content_margin_top = 12
	tsb.content_margin_bottom = 12
	title_bar.add_theme_stylebox_override("panel", tsb)
	vbox.add_child(title_bar)
	var title_row := HBoxContainer.new()
	title_row.add_theme_constant_override("separation", 10)
	title_bar.add_child(title_row)
	var title_icon := _make_label(title_row, "⚔", 20, Style.COLOR_TITLE_TEXT, Vector2.ZERO)
	var symbol_font := SystemFont.new()
	symbol_font.font_names = PackedStringArray(["Segoe UI Symbol"])
	title_icon.add_theme_font_override("font", symbol_font)
	title_icon.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_panel_title = _make_label(title_row, "装备与背包", 20, Style.COLOR_TITLE_TEXT, Vector2.ZERO)
	_panel_title.add_theme_font_override("font", Style.make_heading_font(20))
	_panel_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var close_button := Button.new()
	close_button.text = "×"
	close_button.tooltip_text = "关闭背包（Tab / Esc）"
	Style.style_button(close_button)
	close_button.custom_minimum_size = Vector2(32, 32)
	close_button.add_theme_font_size_override("font_size", 24)
	close_button.add_theme_color_override("font_color", ReferenceStyle.PANEL_CLOSE_TEXT)
	close_button.add_theme_stylebox_override("normal", ReferenceStyle.surface("#293239", "#293239", "#45545e", 5, 1))
	close_button.pressed.connect(func(): set_panel_open(false))
	title_row.add_child(close_button)
	var divider := ColorRect.new()
	divider.custom_minimum_size.y = 2
	divider.color = ReferenceStyle.PANEL_DIVIDER
	vbox.add_child(divider)
	# 页签栏（旧版 SystemUI 页签）
	var tab_bar := HBoxContainer.new()
	tab_bar.add_theme_constant_override("separation", 0)
	vbox.add_child(tab_bar)
	_tab_status = _make_tab_button("状态")
	_tab_equip = _make_tab_button("装备")
	_tab_skill = _make_tab_button("技能")
	_tab_codex = _make_tab_button("图鉴")
	tab_bar.add_child(_tab_status)
	tab_bar.add_child(_tab_equip)
	tab_bar.add_child(_tab_skill)
	tab_bar.add_child(_tab_codex)
	_tab_status.pressed.connect(func() -> void: set_tab("status"))
	_tab_equip.pressed.connect(func() -> void: set_tab("equip"))
	_tab_skill.pressed.connect(func() -> void: set_tab("skill"))
	_tab_codex.pressed.connect(func() -> void: set_tab("codex"))
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
	var gear_margin := MarginContainer.new()
	gear_margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for edge in ["left", "right", "top", "bottom"]:
		gear_margin.add_theme_constant_override("margin_" + edge, 4)
	_page_stack.add_child(gear_margin)
	gear_margin.add_child(_equip_page)
	# 上：装备栏（旧版 gear-equip-col，占上半区，3x5 大宽格）
	var equip_col := VBoxContainer.new()
	_reference_equip_col = equip_col
	equip_col.add_theme_constant_override("separation", 4)
	_equip_page.add_child(equip_col)
	var equip_head := HBoxContainer.new()
	equip_head.add_theme_constant_override("separation", 6)
	equip_col.add_child(equip_head)
	var equip_title := _make_label(equip_head, "装备栏", 16, ReferenceStyle.EQUIP_TEXT, Vector2.ZERO)
	equip_title.custom_minimum_size.y = 30
	equip_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	equip_title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	equip_title.add_theme_font_override("font", Style.make_heading_font(16))
	var rule := StyleBoxFlat.new()
	rule.bg_color = Color.TRANSPARENT
	rule.border_color = Color(ReferenceStyle.EQUIP_GLASS_BORDER)
	rule.border_width_bottom = 1
	equip_title.add_theme_stylebox_override("normal", rule)
	equip_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_equip_grid = GridContainer.new()
	_equip_grid.columns = EQUIP_COLS
	_equip_grid.add_theme_constant_override("h_separation", 6)
	_equip_grid.add_theme_constant_override("v_separation", 6)
	_equip_grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	# 用户确认的黑化深青冷钢容器；布局和圆角仍沿用原装备栏。
	var equip_glass := PanelContainer.new()
	equip_glass.mouse_filter = Control.MOUSE_FILTER_IGNORE
	equip_glass.add_theme_stylebox_override("panel",
		ReferenceStyle.surface(ReferenceStyle.EQUIP_GLASS_TOP, ReferenceStyle.EQUIP_GLASS_BOTTOM, ReferenceStyle.EQUIP_GLASS_BORDER, 12, 2, 10))
	equip_glass.size_flags_vertical = Control.SIZE_EXPAND_FILL
	equip_col.add_child(equip_glass)
	_equip_grid.size_flags_vertical = Control.SIZE_EXPAND_FILL
	equip_glass.add_child(_equip_grid)
	for key in EquipmentScript.SLOT_ORDER:
		var cell := EquipSlot.new()
		cell.hud = self
		cell.key = key
		cell.mouse_default_cursor_shape = Control.CURSOR_DRAG
		cell.size_flags_vertical = Control.SIZE_EXPAND_FILL
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
		icon.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
		icon.anchor_left = 0.0
		icon.anchor_top = 0.0
		icon.anchor_right = 0.0
		icon.anchor_bottom = 1.0
		icon.anchor_left = 0.1
		icon.offset_left = 3
		icon.offset_top = 0
		icon.anchor_right = 0.45
		icon.offset_right = 0
		icon.offset_bottom = 0
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
		fallback.anchor_left = 0.1
		fallback.offset_left = 3
		fallback.offset_top = 6
		fallback.anchor_right = 0.45
		fallback.offset_right = 0
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
		name_lbl.anchor_left = 0.4
		name_lbl.offset_left = 2
		name_lbl.offset_top = 12
		name_lbl.anchor_right = 0.8
		name_lbl.offset_right = -2
		name_lbl.offset_bottom = -8
		name_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		name_lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		name_lbl.autowrap_mode = TextServer.AUTOWRAP_OFF
		name_lbl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		name_lbl.add_theme_font_size_override("font_size", Style.font_size("label"))
		name_lbl.add_theme_font_override("font", _make_item_name_font())
		name_lbl.add_theme_color_override("font_color", ReferenceStyle.EQUIP_TEXT)
		name_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell_content.add_child(name_lbl)
		var rarity_lbl := ReferenceStyle.VerticalBadge.new()
		rarity_lbl.name = "Rarity"
		rarity_lbl.add_theme_constant_override("line_spacing", 2)
		rarity_lbl.add_theme_font_override("font", _font_section)
		rarity_lbl.anchor_left = 0.0
		rarity_lbl.anchor_top = 0.0
		rarity_lbl.anchor_right = 0.0
		rarity_lbl.anchor_bottom = 1.0
		rarity_lbl.anchor_left = 0.02
		rarity_lbl.anchor_right = 0.02
		rarity_lbl.offset_left = 0
		rarity_lbl.offset_top = 0
		rarity_lbl.offset_right = 14
		rarity_lbl.offset_bottom = 0
		rarity_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		rarity_lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		rarity_lbl.add_theme_font_size_override("font_size", 10)
		rarity_lbl.add_theme_color_override("font_color", ReferenceStyle.EQUIP_TEXT_MUTED)
		rarity_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell_content.add_child(rarity_lbl)
		var lock := Control.new()
		lock.name = "Lock"
		lock.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		lock.mouse_filter = Control.MOUSE_FILTER_IGNORE
		lock.visible = false
		cell_content.add_child(lock)
		var x_lbl := Label.new()
		x_lbl.text = "✕"
		x_lbl.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		x_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		x_lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		x_lbl.add_theme_font_size_override("font_size", 32)
		x_lbl.add_theme_color_override("font_color", Style.COLOR_BLACK)
		x_lbl.add_theme_font_override("font", Style.make_font(700))
		x_lbl.add_theme_color_override("font_shadow_color", ReferenceStyle.PANEL_GLYPH_SHADOW)
		x_lbl.add_theme_constant_override("shadow_offset_x", 0)
		x_lbl.add_theme_constant_override("shadow_offset_y", 0)
		x_lbl.add_theme_constant_override("shadow_outline_size", 4)
		x_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		lock.add_child(x_lbl)
		_equip_grid.add_child(cell)
		_equip_cells[key] = cell
	# 下：16x8 空间背包；半尺寸单格按背包栏 2:1 比例重新铺满。
	var inv_col := VBoxContainer.new()
	inv_col.add_theme_constant_override("separation", 4)
	inv_col.size_flags_vertical = Control.SIZE_EXPAND_FILL
	var inv_margin := MarginContainer.new()
	inv_margin.size_flags_vertical = Control.SIZE_EXPAND_FILL
	inv_margin.add_theme_constant_override("margin_left", 4)
	inv_margin.add_theme_constant_override("margin_right", 4)
	_equip_page.add_child(inv_margin)
	inv_margin.add_child(inv_col)
	var inv_header := HBoxContainer.new()
	inv_col.add_child(inv_header)
	inv_header.custom_minimum_size.y = 18
	var inv_title := _make_label(inv_header, "背包", Style.font_size("label"), Style.COLOR_TEXT, Vector2.ZERO)
	inv_title.add_theme_font_override("font", Style.make_heading_font(16))
	inv_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inv_title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_count_label = _make_label(inv_header, "", Style.font_size("caption"), Style.COLOR_TEXT, Vector2.ZERO)
	_count_label.add_theme_font_override("font", _font_mono)
	_count_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	# 16列在部分窗口宽度会落在小数像素；使用同源深青底封住栅格化缝隙。
	_grid = Panel.new()
	var grid_backing := StyleBoxFlat.new()
	grid_backing.bg_color = ReferenceStyle.BACKPACK_EMPTY_BOTTOM
	_grid.add_theme_stylebox_override("panel", grid_backing)
	_grid.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_grid.custom_minimum_size = Vector2(INV_COLS * CELL_SLOT * 0.5, Spatial.ROWS * CELL_SLOT * 0.5)
	_grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_grid.resized.connect(_layout_grid_geometry)
	var inv_scroll := Style.make_scroll_container()
	inv_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	inv_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	inv_col.add_child(inv_scroll)
	inv_scroll.add_child(_grid)
	_sync_grid_cells()
	# 右侧贴边：固定 PANEL_W 宽、全高，初始在屏幕外右侧（复刻旧版 system-panel）
	_panel.anchor_left = 1.0
	_panel.anchor_right = 1.0
	_panel.anchor_top = 0.0
	_panel.anchor_bottom = 1.0
	_panel.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_panel.offset_top = 0
	_panel.offset_bottom = 0
	_apply_panel_slide(0.0)

func _sync_grid_cells() -> void:
	var target := backpack.slots.size() if backpack != null else 0
	if _cells.size() == target:
		return
	_hovered_cell = -1
	_drag_over_cell = -1
	_drag_over_cells.clear()
	while _cells.size() > target:
		var removed: Control = _cells.pop_back()
		_grid.remove_child(removed)
		removed.queue_free()
	for i in range(_cells.size(), target):
		var cell := BackpackCell.new()
		cell.hud = self
		cell.slot = i
		cell.mouse_default_cursor_shape = Control.CURSOR_DRAG
		cell.focus_mode = Control.FOCUS_ALL
		var cell_side := _grid_cell_side()
		cell.position = Vector2((i % INV_COLS) * cell_side, (i / INV_COLS) * cell_side)
		cell.custom_minimum_size = Vector2.ONE * cell_side
		cell.size = cell.custom_minimum_size
		cell.add_theme_stylebox_override("panel", _s_cell_empty)
		var cell_content := Control.new()
		cell_content.name = "Content"
		cell_content.custom_minimum_size = Vector2.ZERO
		cell_content.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell.add_child(cell_content)
		var icon := TextureRect.new()
		icon.name = "Icon"
		icon.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
		icon.anchor_left = 0.25
		icon.anchor_right = 0.44
		icon.anchor_bottom = 1.0
		icon.offset_top = 6
		icon.offset_bottom = -6
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell_content.add_child(icon)
		var fallback := Label.new()
		fallback.name = "Fallback"
		fallback.anchor_left = 0.25
		fallback.anchor_right = 0.4
		fallback.anchor_bottom = 1.0
		fallback.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		fallback.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		fallback.add_theme_font_override("font", Style.make_emoji_font())
		fallback.add_theme_font_size_override("font_size", 18)
		fallback.mouse_filter = Control.MOUSE_FILTER_IGNORE
		fallback.visible = false
		cell_content.add_child(fallback)
		var stack := _make_label(cell_content, "", 12, Style.COLOR_WHITE, Vector2.ZERO)
		stack.name = "Stack"
		stack.add_theme_font_override("font", _font_mono)
		stack.anchor_left = 1.0
		stack.anchor_right = 1.0
		stack.anchor_top = 1.0
		stack.anchor_bottom = 1.0
		stack.offset_left = -30
		stack.offset_top = -20
		stack.offset_right = -4
		stack.offset_bottom = -4
		stack.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		var name_lbl := _make_label(cell_content, "", Style.font_size("caption"), Style.COLOR_WHITE, Vector2.ZERO)
		name_lbl.name = "Name"
		name_lbl.add_theme_font_override("font", _make_item_name_font())
		ReferenceStyle.item_shadow(name_lbl)
		name_lbl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		name_lbl.anchor_left = 0.44
		name_lbl.anchor_right = 0.95
		name_lbl.anchor_top = 0.0
		name_lbl.anchor_bottom = 1.0
		name_lbl.offset_left = 2
		name_lbl.offset_top = -2
		name_lbl.offset_right = -4
		name_lbl.offset_bottom = -2
		name_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
		name_lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		var rarity_lbl := ReferenceStyle.VerticalBadge.new()
		rarity_lbl.name = "Rarity"
		rarity_lbl.add_theme_constant_override("line_spacing", 0)
		rarity_lbl.add_theme_font_override("font", _font_section)
		rarity_lbl.anchor_left = 0.0
		rarity_lbl.anchor_right = 0.0
		rarity_lbl.anchor_top = 0.0
		rarity_lbl.anchor_bottom = 1.0
		rarity_lbl.offset_left = 2
		rarity_lbl.offset_top = 0
		rarity_lbl.offset_right = 15
		rarity_lbl.offset_bottom = 0
		rarity_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		rarity_lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		rarity_lbl.add_theme_font_size_override("font_size", 8)
		rarity_lbl.add_theme_color_override("font_color", Color.BLACK)
		rarity_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell_content.add_child(rarity_lbl)
		_grid.add_child(cell)
		_cells.append(cell)

func _build_status_label() -> void:
	_status_label = _make_label(self, "", Style.font_size("label"), Style.COLOR_STATUS, Vector2.ZERO)
	_status_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_status_label.offset_top = -92
	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_status_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_status_label.visible = false

func _build_notice() -> void:
	_notice_label = _make_label(self, "", 20, Style.COLOR_NOTICE, Vector2.ZERO)
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

# SimHei only provides a regular face; reproduce the source CSS synthetic 600/700 weight.
func _make_item_name_font() -> Font:
	return Style.make_item_name_font()

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
	b.custom_minimum_size = Vector2(0, 50)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.add_theme_font_size_override("font_size", 16)
	b.add_theme_font_override("font", _font_section)
	Style._attach_button_anim(b)
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

func _set_icon(icon: TextureRect, fallback: Label, item: Dictionary, in_backpack := false) -> void:
	var resolver := preload("res://ui/item_icon.gd")
	var path: String = resolver.backpack_path(item) if in_backpack else resolver.equipment_path(item)
	# Both role-specific firearm renders are cropped to their visible alpha bounds.
	# The source orientation is preserved; this only removes transparent padding.
	var tex := _cropped_icon_tex(path) if _is_firearm(item) else _icon_tex(path)
	icon.texture = tex
	var emoji := String(item.get("icon_fallback", ""))
	fallback.visible = tex == null and emoji != ""
	fallback.text = emoji

func _cropped_icon_tex(path: String) -> Texture2D:
	if path.is_empty():
		return null
	if _cropped_tex_cache.has(path):
		return _cropped_tex_cache[path]
	var source := _icon_tex(path)
	if source == null:
		_cropped_tex_cache[path] = null
		return null
	var image := source.get_image()
	var used := image.get_used_rect() if image != null else Rect2i()
	if used.size.x <= 0 or used.size.y <= 0:
		_cropped_tex_cache[path] = source
		return source
	var cropped := AtlasTexture.new()
	cropped.atlas = source
	cropped.region = Rect2(used)
	_cropped_tex_cache[path] = cropped
	return cropped

func _is_firearm(item: Dictionary) -> bool:
	return item.has("rangedType") or str(item.get("weaponType", "")) in ["rifle", "pistol"] \
		or str(item.get("category", "")) == "weapon_ranged"

func _vertical_text(s: String) -> String:
	if s.length() <= 1:
		return s
	var out := ""
	for i in s.length():
		out += s[i] + ("\n" if i < s.length() - 1 else "")
	return out

func _clear_children(box: Node) -> void:
	for child in box.get_children():
		child.queue_free()

func make_slot_preview(item: Dictionary, grab_cell := Vector2i.ZERO, spatial := false) -> Control:
	if not spatial:
		return preload("res://ui/item_drag_preview.gd").make(item)
	var footprint := Spatial.footprint(item)
	var icon_path: String = preload("res://ui/item_icon.gd").backpack_path(item)
	var texture := _cropped_icon_tex(icon_path) if _is_firearm(item) else _icon_tex(icon_path)
	return preload("res://ui/item_drag_preview.gd").make(item, footprint, _grid_cell_side(), grab_cell, texture, _s_cell_drag_over)

func make_skill_preview(skill_id: String) -> Control:
	var p := PanelContainer.new()
	p.custom_minimum_size = Vector2(48, 48)
	p.add_theme_stylebox_override("panel", Style.make_style(Style.COLOR_DRAG_PREVIEW_BG, Style.COLOR_SKILL_SLOT_BORDER, 6, 2))
	var def: Dictionary = skillbar.skills.get(skill_id, {})
	var tex := _icon_tex(String(def.get("icon", "")))
	if tex != null:
		var preview_icon := TextureRect.new()
		preview_icon.texture = tex
		preview_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		preview_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		p.add_child(preview_icon)
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
				if get_global_mouse_position().distance_to(_press_pos) < 6.0:
					hud.on_skill_click(key)

	func _get_drag_data(_at: Vector2):
		if hud.skillbar == null or index < 0:
			return null
		var skill_id = hud.skillbar.resolve(index)
		if skill_id == "":
			return null
		_pressed = false
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
				if get_global_mouse_position().distance_to(_press_pos) < 6.0:
					hud.use_hotbar(index)

	func _get_drag_data(_at: Vector2):
		var item = hud.backpack.resolve_hotbar(index)
		if item.is_empty():
			return null
		_pressed = false
		hud.hide_tooltip()
		set_drag_preview(hud.make_slot_preview(item))
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
				if event.pressed and event.double_click and not event.shift_pressed:
					_pressed = false
					hud.hide_tooltip()
					hud.use_backpack_item(slot)
					accept_event()
					return
				if event.pressed:
					_pressed = true
					_press_pos = get_global_mouse_position()
				elif _pressed:
					_pressed = false
					if get_global_mouse_position().distance_to(_press_pos) < 6.0:
						if event.shift_pressed:
							hud._context_instance = str(hud.backpack.slots[slot].get("instance_id", "")) if hud.backpack.slots[slot] != null else ""
							hud._on_item_action(1)
						else:
							hud.on_cell_click_pin(slot)
			elif event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
				if event.shift_pressed:
					hud.open_item_actions(slot)
				else:
					hud.hide_tooltip()
					hud.use_backpack_item(slot)
				accept_event()

	func _notification(what: int) -> void:
		if what == NOTIFICATION_DRAG_END:
			modulate.a = 1.0

	func _get_drag_data(_at: Vector2):
		if hud.backpack == null or hud.backpack.slots[slot] == null:
			return null
		var item: Dictionary = hud.backpack.slots[slot]
		var footprint := Spatial.footprint(item)
		var grab_cell := Vector2i(
			clampi(floori(_at.x / hud._grid_cell_side()), 0, footprint.x - 1),
			clampi(floori(_at.y / hud._grid_cell_side()), 0, footprint.y - 1)
		)
		_pressed = false
		hud.hide_tooltip()
		set_drag_preview(hud.make_slot_preview(item, grab_cell, true))
		modulate.a = 0.3
		return {"type": "backpack", "slot": slot, "item": item.duplicate(true), "grab_cell": grab_cell}

	func _can_drop_data(_at: Vector2, data) -> bool:
		var ok := data is Dictionary and (String(data.get("type", "")) == "backpack" \
			or String(data.get("type", "")) == "hotbar" or String(data.get("type", "")) == "equip" \
			or String(data.get("type", "")) == "skill" or String(data.get("type", "")) == "npc_item" or String(data.get("type", "")) == "panel_item")
		if ok:
			hud.set_cell_drag_over(hud.grid_cell_from_local(slot, _at), true, data)
		return ok

	func _drop_data(_at: Vector2, data) -> void:
		var target: int = hud.drag_target_anchor(hud.grid_cell_from_local(slot, _at), data)
		hud.set_cell_drag_over(slot, false)
		if target >= 0:
			hud.drop_on_backpack(target, data)

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
		if hud.equipment != null and hud.equipment.is_locked(key):
			_pressed = false
			return
		if event is InputEventMouseButton:
			if event.button_index == MOUSE_BUTTON_LEFT:
				if event.pressed:
					_pressed = true
					_press_pos = get_global_mouse_position()
				elif _pressed:
					_pressed = false
					if get_global_mouse_position().distance_to(_press_pos) < 6.0:
						hud.on_equip_click_pin(key)
			elif event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
				hud.on_equip_right_click(key)

	func _notification(what: int) -> void:
		if what == NOTIFICATION_DRAG_END:
			modulate.a = 0.6 if hud.equipment != null and hud.equipment.is_locked(key) else 1.0

	func _get_drag_data(_at: Vector2):
		if hud.equipment == null or hud.equipment.get_item(key).is_empty() or hud.equipment.is_locked(key):
			return null
		var item: Dictionary = hud.equipment.get_item(key)
		_pressed = false
		hud.hide_tooltip()
		set_drag_preview(hud.make_slot_preview(item, Vector2i.ZERO, true))
		modulate.a = 0.3
		return {"type": "equip", "key": key, "item": item.duplicate(true)}

	func _can_drop_data(_at: Vector2, data) -> bool:
		if hud.equipment == null or hud.equipment.is_locked(key):
			return false
		var ok := false
		if data is Dictionary:
			match String(data.get("type", "")):
				"panel_item":
					var source := preload("res://ui/panel_item_transfer.gd").resolve(data)
					ok = not source.is_empty() and (source.field in ["_scroll", "_equip"] or hud.equipment.can_equip_to(key, source.item))
				"equip":
					ok = true
				"backpack":
					var src: int = hud._drag_backpack_slot(data)
					ok = hud.backpack != null and src >= 0 and src < hud.backpack.slots.size() \
						and hud.backpack.slots[src] != null \
						and hud.equipment.can_equip_to(key, hud.backpack.slots[src])
		if ok:
			hud.set_equip_drag_over(key, true)
		return ok

	func _drop_data(_at: Vector2, data) -> void:
		hud.set_equip_drag_over(key, false)
		hud.drop_on_equip(key, data)

func _resize_inventory() -> void:
	if _panel_root != null:
		_panel_root.get_node("Dim").material.set_shader_parameter("node_size", get_viewport_rect().size)
	_panel_w = get_viewport_rect().size.x * PANEL_W_RATIO
	if _reference_equip_col != null:
		_reference_equip_col.custom_minimum_size.y = (get_viewport_rect().size.y - 112) * 0.5 - 2
	_layout_grid_geometry()
	if _panel != null:
		_apply_panel_slide(1.0 if _panel_open else 0.0)

func _build_inventory_actions() -> void:
	_context = PopupMenu.new()
	_context.theme = Style.make_theme()
	_context.add_item("使用 / 装备", 0)
	_context.add_item("拆分", 1)
	_context.add_item("查看详情", 2)
	_context.add_separator()
	_context.add_item("丢弃", 3)
	_context.add_separator()
	_context.add_item("整理背包", 4)
	_context.add_item("保存背包", 5)
	_context.id_pressed.connect(_on_item_action)
	add_child(_context)
	_split_dialog = ConfirmationDialog.new()
	_split_dialog.title = "拆分物品"
	_split_dialog.theme = Style.make_theme()
	_split_dialog.ok_button_text = "确认拆分"
	_split_dialog.cancel_button_text = "取消"
	var split_body := VBoxContainer.new()
	split_body.add_theme_constant_override("separation", 12)
	_split_dialog.add_child(split_body)
	_split_name = Label.new()
	Style.style_item_name(_split_name)
	_split_name.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	split_body.add_child(_split_name)
	_split_slider = HSlider.new()
	_split_slider.min_value = 1
	_split_slider.step = 1
	split_body.add_child(_split_slider)
	_split_count = SpinBox.new()
	_split_count.min_value = 1
	_split_count.step = 1
	_split_count.custom_minimum_size = Vector2(280, 40)
	split_body.add_child(_split_count)
	_split_slider.value_changed.connect(func(value): _split_count.value = value)
	_split_count.value_changed.connect(func(value): _split_slider.value = value)
	_split_dialog.confirmed.connect(func():
		var slot := backpack.find_slot(_split_instance)
		if not backpack.split_stack(slot, int(_split_count.value)):
			_flash_status("拆分失败：检查剩余数量和背包空位"))
	add_child(_split_dialog)
	_discard_dialog = ConfirmationDialog.new()
	_discard_dialog.title = "确认丢弃"
	_discard_dialog.theme = Style.make_theme()
	_discard_dialog.ok_button_text = "丢弃"
	_discard_dialog.cancel_button_text = "保留"
	_discard_dialog.confirmed.connect(func():
		var slot := backpack.find_slot(_discard_instance)
		if slot >= 0:
			var item: Dictionary = backpack.slots[slot]
			var hud := get_node_or_null("/root/HUD")
			if hud != null:
				hud.drop_inventory_item(slot, item))
	add_child(_discard_dialog)

func open_item_actions(slot: int) -> void:
	if slot < 0 or slot >= backpack.slots.size() or backpack.slots[slot] == null:
		return
	var item: Dictionary = backpack.slots[slot]
	_context_instance = str(item.instance_id)
	_context.set_item_disabled(1, int(item.get("stack", 1)) <= 1 or preload("res://ui/item_rules.gd").is_gold(item))
	_context.position = Vector2i(get_viewport().get_mouse_position())
	_context.popup()

func _on_item_action(action: int) -> void:
	if action == 4:
		backpack.sort_items()
		return
	if action == 5:
		var host := get_node_or_null("/root/HUD")
		if host != null:
			_flash_status("背包已保存" if host.save_inventory() == OK else "保存失败")
		return
	var slot := backpack.find_slot(_context_instance)
	if slot < 0:
		return
	var item: Dictionary = backpack.slots[slot]
	if action == 0:
		use_backpack_item(slot)
	elif action == 1:
		if int(item.get("stack", 1)) <= 1 or preload("res://ui/item_rules.gd").is_gold(item):
			return
		_split_instance = _context_instance
		_split_name.text = "%s · 总数量 %d" % [item.get("name", "物品"), int(item.stack)]
		_split_slider.max_value = int(item.stack) - 1
		_split_count.max_value = int(item.stack) - 1
		_split_count.value = maxi(1, int(int(item.stack) / 2.0))
		_split_dialog.popup_centered(Vector2i(320, 200))
		_split_count.get_line_edit().grab_focus()
	elif action == 2:
		on_cell_click_pin(slot)
	elif action == 3:
		_discard_instance = _context_instance
		_discard_dialog.dialog_text = "将 %s × %d 放到脚边？" % [item.get("name", "物品"), int(item.stack)]
		_discard_dialog.popup_centered(Vector2i(340, 160))

func _notification(what: int) -> void:
	if what == NOTIFICATION_DRAG_BEGIN:
		_drag_active = true
		_drag_origin_rect = _panel.get_global_rect() if _panel_open else _hotbar_root.get_global_rect()
	elif what == NOTIFICATION_DRAG_END:
		_drag_active = false
		if _hotbar_root != null:
			_hotbar_root.z_index = 100
		_clear_all_drag_over()
	elif what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		if is_inside_tree() and get_viewport().gui_is_dragging():
			get_viewport().gui_cancel_drag()

func _exit_tree() -> void:
	ReferenceStyle.clear_cache()
