extends SceneTree
const DB := preload("res://ui/item_db.gd")
const Backpack := preload("res://ui/backpack.gd")
const Equipment := preload("res://ui/equipment.gd")
const Warehouse := preload("res://ui/warehouse.gd")
const Save := preload("res://ui/inventory_save.gd")
var failures := 0
var checks := 0

func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures += 1
		push_error(message)

func count_items(bp) -> int:
	var result := 0
	for item in bp.slots:
		if item != null:
			result += int(item.stack)
	return result

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var db := DB.new()
	var bp := Backpack.new(db)
	check(bp.max_slots == 10, "default capacity")
	check(db.get_all_ids().size() >= 194, "all original definitions")
	check(bp.add_item("hp_potion", 250), "multi-stack insert")
	check(count_items(bp) == 250 and bp.item_count() == 3, "no truncated items")
	check(bp.split_stack(0, 20), "split succeeds")
	check(count_items(bp) == 250 and bp.slots[0].instance_id != bp.slots[3].instance_id, "split preserves quantity and separates identity")
	bp.bind_hotbar(0, bp.slots[3].instance_id)
	bp.sort_items()
	check(not bp.resolve_hotbar(0).is_empty(), "hotbar survives sort")
	var before := bp.serialize()
	check(not bp.add_item("hp_potion", 10000), "full insert refused")
	check(bp.serialize() == before, "failed insert is atomic")
	var eq := Equipment.new(bp)
	check(not eq.can_equip_to("offhand", db.create_instance("rusty_sword")), "sword cannot equip to offhand")
	check(eq.can_equip_to("offhand", db.create_instance("small_shield")), "shield fits offhand")
	var weapon := db.create_instance("rusty_sword")
	weapon.enhanceLevel = 7
	weapon._craftData = {"barrel": "precise"}
	weapon._enchantData = {"prefix": {"id": "heavy"}}
	check(bp.add_instance(weapon), "add modified instance")
	var slot := bp.find_slot(weapon.instance_id)
	check(eq.equip_to_slot("weapon", slot), "equip modified item")
	check(eq.unequip("weapon", 8), "unequip to chosen free slot")
	check(bp.slots[8].instance_id == weapon.instance_id and bp.slots[8]._craftData == weapon._craftData, "equipment identity survives")
	var wh := Warehouse.new()
	check(wh.store_from_backpack(bp, 8), "deposit instance")
	check(wh.retrieve_to_backpack(bp, 0, 8), "retrieve instance")
	check(bp.slots[8].enhanceLevel == 7 and bp.slots[8]._enchantData == weapon._enchantData, "warehouse keeps upgrades")
	# Full bag + two occupied weapon slots requires two return spaces, so reject atomically.
	bp = Backpack.new(db)
	eq = Equipment.new(bp)
	for i in 10:
		bp.add_item("rusty_sword")
	eq.slots.weapon = db.create_instance("rusty_sword")
	eq.slots.offhand = db.create_instance("small_shield")
	bp.slots[0].isTwoHanded = true
	before = bp.serialize()
	var eq_before := eq.serialize()
	check(not eq.equip_to_slot("weapon", 0), "full dual displacement refused")
	check(bp.serialize() == before and eq.serialize() == eq_before, "failed equipment operation is atomic")
	bp.slots[9] = null
	check(eq.equip_to_slot("weapon", 0) and eq.slots.offhand == null, "two hand displacement succeeds with space")
	check(not eq.swap_equip("weapon", "helmet"), "slot swaps validate both targets")
	var snapshot := {"version": 1, "backpack": bp.serialize(), "equipment": eq.serialize(), "warehouse": wh.serialize(), "pending": {"craft": {"item": weapon}}}
	check(Save.write_snapshot(snapshot, "user://inventory-regression.save") == OK, "save succeeds")
	check(Save.read_snapshot("user://inventory-regression.save") == snapshot, "save retains nested instance state")
	var restored := Backpack.new(db)
	restored.restore(snapshot.backpack)
	check(restored.serialize() == bp.serialize(), "backpack restoration")
	# Cross-container swaps and overwriting an existing save retain complete instances.
	var left := Backpack.new(db)
	left.add_item("rusty_sword")
	var left_id: String = left.slots[0].instance_id
	var store := Warehouse.new()
	store.add_item(db.create_instance("small_shield"))
	check(store.store_from_backpack(left, 0, 0), "cross container swap")
	check(left.slots[0].id == "small_shield" and store.get_item_at(0).instance_id == left_id, "swap preserves both instances")
	check(Save.write_snapshot(snapshot, "user://inventory-regression.save") == OK, "atomic overwrite existing save")
	check(db.get_def("enchant_scroll_heavy").get("scroll_id", "") == "heavy", "source scroll adapter")
	var hud := root.get_node("HUD")
	hud._ensure_built()
	var host := Node.new()
	root.add_child(host)
	var panels := preload("res://ui/npc_panels.gd").build(host, db, left, Equipment.new(left), hud.economy, null, store, hud.player_status)
	for panel in panels.values():
		panel.open_panel()
		await process_frame
		panel.close()
	check(panels.size() == 8, "all NPC panels build and open")
	var enhance = panels.enhance
	var target_id: String = left.slots[0].instance_id
	enhance._equip_from_backpack(0)
	for i in 10:
		left.add_item("rusty_sword")
	enhance._return_item()
	check(not enhance._equipped.is_empty() and enhance._equipped.item.instance_id == target_id, "full bag retains upgrade escrow")
	check(hud.save_inventory() == OK, "save all panel escrow")
	var saved := Save.read_snapshot()
	check(saved.pending.enhance._equipped.item.instance_id == target_id, "persist escrow identity")
	left.slots[0] = null
	enhance._return_item()
	check(enhance._equipped.is_empty() and left.find_slot(target_id) >= 0, "return escrow after freeing space")
	var expedition = panels.expedition
	left.slots[0] = null
	var tribute := db.create_instance("tribute_common")
	tribute.enhanceLevel = 3
	left.add_instance(tribute, 0)
	expedition._place_from_backpack(0)
	left.add_item("rusty_sword")
	expedition._return_all()
	check(expedition._carried[0] != null, "full bag retains expedition offering")
	left.slots[0] = null
	expedition._return_all()
	check(left.slots[0].instance_id == tribute.instance_id and left.slots[0].enhanceLevel == 3, "expedition return preserves metadata")
	host.queue_free()
	await process_frame
	await process_frame
	print("INVENTORY: %d checks, %d failures" % [checks, failures])
	quit(1 if failures else 0)
