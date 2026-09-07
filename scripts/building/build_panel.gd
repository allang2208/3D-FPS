extends "res://ui/npc_panel.gd"
signal build_requested(kind: String)
signal stop_requested
const Costs := preload("res://scripts/building/build_costs.gd")
const Catalog := preload("res://scripts/building/build_piece_catalog.gd")
var cost_label: Label

var CATALOG: Array[Resource]=Catalog.panel_definitions()
var selection := "wood"
var category := "全部"
var cards: Dictionary = {}
var tabs: Dictionary = {}
var detail_name: Label
var detail_text: Label
var detail_image: TextureRect
var detail_meta: Label
var build_button: Button

func label(text: String, role: StringName = &"body") -> Label:
	var result := Label.new()
	result.text = text
	result.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	Style.apply_text_role(result, role)
	result.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if role == &"caption": result.add_theme_color_override("font_color", Style.COLOR_DIM_TEXT)
	return result

func thumbnail() -> TextureRect:
	var result := TextureRect.new()
	result.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	result.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	result.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return result

func _build_body() -> void:
	set_title("建筑工坊")
	Style.apply_text_role(title_label, &"title")
	body.add_child(label("主神空间 / 体素构筑 · 单格 0.5 米 · 自动保存", &"caption"))
	var filters := HBoxContainer.new()
	body.add_child(filters)
	for key in ["全部", "木材", "石材", "构件"]:
		var tab := _make_button(key)
		tab.toggle_mode = true
		tab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		tab.pressed.connect(func(): set_category(key))
		filters.add_child(tab)
		tabs[key] = tab
	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation", 16)
	body.add_child(columns)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.size_flags_stretch_ratio = 1.15
	columns.add_child(grid)
	for definition in CATALOG:
		var key: String = str(definition.stable_id)
		var card := _make_button("")
		card.name = "Build_" + key
		card.set_meta("build_kind", key)
		card.toggle_mode = true
		card.custom_minimum_size = Vector2(148, 126)
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		card.tooltip_text = "%s · %s\n%s" % [definition.display_name, definition.category, definition.description]
		var content := VBoxContainer.new()
		content.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		content.offset_left = 8
		content.offset_right = -8
		content.offset_top = 4
		content.offset_bottom = -6
		content.mouse_filter = Control.MOUSE_FILTER_IGNORE
		card.add_child(content)
		var picture := thumbnail()
		picture.custom_minimum_size.y = 72
		picture.texture = load(definition.thumbnail_path)
		content.add_child(picture)
		var name_text := label(definition.display_name, &"name_body")
		name_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		content.add_child(name_text)
		var info := label("%s · %s ×%d" % [definition.form_label,Costs.NAMES[Costs.item_for(key)],Costs.amount_for(key)], &"caption")
		info.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		content.add_child(info)
		card.pressed.connect(func(): select_kind(key))
		grid.add_child(card)
		cards[key] = card
	var detail := VBoxContainer.new()
	detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	detail.add_theme_constant_override("separation", 10)
	columns.add_child(detail)
	detail.add_child(label("构件详情", &"section"))
	detail_image = thumbnail()
	detail_image.custom_minimum_size.y = 108
	detail.add_child(detail_image)
	detail_name = label("", &"name")
	detail.add_child(detail_name)
	detail_meta = label("", &"caption")
	detail.add_child(detail_meta)
	detail_text = label("")
	detail.add_child(detail_text)
	cost_label=label("")
	detail.add_child(cost_label)
	detail.add_child(HSeparator.new())
	detail.add_child(label("搭建规则", &"section"))
	detail.add_child(label("连接地基或已有支撑，木石可混搭。\n围栏按邻接自动生成端柱、转角、T形和十字；门占用2×4格，靠近按 E 开关。\n拆除返还材料，Ctrl+Z/Y撤销/重做；F切换吸附，滚轮旋转。"))
	# Keep primary actions outside the base panel content scroll.
	var footer := VBoxContainer.new()
	panel.get_node("Root").add_child(footer)
	footer.add_child(HSeparator.new())
	footer.add_child(label("左键放置 · 右键拆除/退款 · Ctrl+Z/Y 撤销/重做 · 滚轮旋转 · F 吸附/手动 · Esc 退出", &"caption"))
	var actions := HBoxContainer.new()
	footer.add_child(actions)
	var stop := _make_button("退出建造")
	stop.pressed.connect(func():
		close()
		stop_requested.emit())
	actions.add_child(stop)
	build_button = _make_button("")
	build_button.custom_minimum_size.y = 36
	build_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	build_button.pressed.connect(func():
		close()
		build_requested.emit(selection))
	actions.add_child(build_button)
	set_category(category)
	select_kind(selection)
	var bp:=Costs.stock(self)
	if bp!=null: bp.changed.connect(refresh_cost)

func set_category(value: String) -> void:
	if not tabs.has(value): return
	category = value
	for key in tabs: tabs[key].set_pressed_no_signal(key == category)
	for definition in CATALOG:
		var key:=str(definition.stable_id)
		cards[key].visible = category == "全部" or definition.category == category
	if not cards[selection].visible:
		for definition in CATALOG:
			var key:=str(definition.stable_id)
			if cards[key].visible:
				select_kind(key)
				break

func select_kind(value: String) -> void:
	if not cards.has(value): return
	selection = value
	for key in cards: cards[key].set_pressed_no_signal(key == value)
	for definition in CATALOG:
		if str(definition.stable_id) != value: continue
		detail_name.text = definition.display_name
		var behavior := "自动端柱/转角/T形/十字" if value=="railing" else ("占用2×4格，E键开关" if value=="door" else "外露圆角，拼接面完整对齐")
		detail_meta.text = "%s / %s · %s" % [definition.category, definition.form_label,behavior]
		detail_text.text = definition.description
		detail_image.texture = load(definition.thumbnail_path)
		build_button.text = "开始建造 · " + definition.display_name
	refresh_cost()

func _refresh() -> void:
	refresh_cost()

func refresh_cost() -> void:
	if cost_label==null: return
	var id:=Costs.item_for(selection)
	var definition:=Catalog.definition(selection)
	var bp:=Costs.stock(self)
	var count: int=bp.count_item(id) if bp!=null else 0
	var size: Vector3=definition.collision_size
	var dimensions := "尺寸 %.1f × %.2f × %.1f 米 · 耐久 %d" % [size.x,size.z,size.y,definition.max_health]
	var amount:=Costs.amount_for(selection)
	cost_label.text="每次消耗：%s ×%d\n背包持有：%d\n%s" % [Costs.NAMES[id],amount,count,dimensions]
	build_button.disabled=count<amount
	cost_label.add_theme_color_override("font_color",Style.THEME_DANGER_RED if count<amount else Style.COLOR_TEXT)
