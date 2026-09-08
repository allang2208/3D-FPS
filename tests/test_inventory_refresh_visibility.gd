extends SceneTree
var failures := 0
func _initialize() -> void: call_deferred("run")
func check(ok: bool, label: String) -> void:
	print("PASS " if ok else "FAIL ", label)
	if not ok: failures += 1
func run() -> void:
	var hud = root.get_node("HUD")
	hud._ensure_built()
	var bp = hud.backpack
	var view = hud.backpack_hud
	bp.slots.fill(null)
	bp.add_item("iron_ore", 100)
	var index: int = -1
	for i in bp.slots.size():
		if bp.slots[i] != null: index = i; break
	bp.add_item("hp_potion", 3)
	for item in bp.slots:
		if item != null and item.id == "hp_potion": bp.bind_hotbar(0, str(item.instance_id))
	view.set_panel_open(true)
	var stack: Label = view._cells[index].get_node("Content/Stack")
	var hotbar: Label = view._hotbar_slots[0].get_node("Content/Stack")
	check(stack.text == "100", "opening displays inventory")
	view.set_panel_open(false)
	await create_timer(0.3).timeout
	check(bp.take_items("iron_ore", 30) == 30 and bp.count_item("iron_ore") == 70, "items removed exactly once")
	check(view._inventory_view_dirty and stack.text == "100", "closed drawer skips card refresh")
	bp.take_items("hp_potion", 1)
	check(hotbar.text == "2", "closed drawer retains live hotbar")
	view.set_panel_open(true)
	check(not view._inventory_view_dirty and stack.text == "70", "reopening refreshes before first visible frame")
	bp.take_items("iron_ore", 10)
	check(stack.text == "60" and hotbar.text == "2", "open drawer updates immediately")
	view.set_panel_open(false)
	bp.take_items("iron_ore", 10)
	check(stack.text == "50", "closing animation retains current values")
	view.set_panel_open(true)
	check(stack.text == "50", "interrupted close remains current")
	print("INVENTORY_REFRESH_VISIBILITY ", "PASS" if failures == 0 else "FAIL")
	quit(0 if failures == 0 else 1)
