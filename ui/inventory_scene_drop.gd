extends Control
## 背包遮罩的空白场景区域接收丢弃；其他面板和快捷栏不作为丢弃目标。
var backpack_view: Control

func _can_drop_data(at: Vector2, data) -> bool:
	if not data is Dictionary or data.get("type", "") not in ["backpack", "equip"]:
		return false
	var hud := get_node_or_null("/root/HUD")
	if hud == null or not is_instance_valid(hud._bound_player) or not is_instance_valid(get_tree().current_scene):
		return false
	var point := global_position + at
	if backpack_view._hotbar_root.is_visible_in_tree() and backpack_view._hotbar_root.get_global_rect().has_point(point):
		return false
	if _over_panel(hud, point):
		return false
	for ref in hud._inventory_panels.values():
		var panel: Node = ref.get_ref()
		if panel != null and panel.is_open() and panel.panel.get_global_rect().has_point(point):
			return false
	return true

func _over_panel(node: Node, point: Vector2) -> bool:
	if node is Control and not node.is_visible_in_tree():
		return false
	if node is Control and node != self and (node is Panel or node is PanelContainer or node is BaseButton):
		if node.get_global_rect().has_point(point):
			return true
	for child in node.get_children():
		if _over_panel(child, point):
			return true
	return false

func _drop_data(at: Vector2, data) -> void:
	if not _can_drop_data(at, data):
		return
	var hud := get_node("/root/HUD")
	var success: bool
	if data.type == "backpack":
		success = hud.drop_inventory_item(backpack_view._drag_backpack_slot(data), data.get("item", {}))
	else:
		success = hud.drop_equipped_item(backpack_view._drag_equip_key(data), data.get("item", {}))
	if not success:
		backpack_view.flash_status("物品已变化，未丢弃")
