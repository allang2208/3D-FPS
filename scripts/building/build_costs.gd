extends RefCounted
const Catalog:=preload("res://scripts/building/build_piece_catalog.gd")
const NAMES={"wood":"木材","stone":"石块"}

static func item_for(kind: String) -> String:
	var definition:=Catalog.definition(kind)
	return definition.cost_item if definition!=null else ""

static func amount_for(kind: String) -> int:
	var definition:=Catalog.definition(kind)
	return definition.cost_amount if definition!=null else 0

static func stock(owner: Node) -> RefCounted:
	var hud:=owner.get_node_or_null("/root/HUD")
	return hud.backpack if hud!=null else null

static func error(owner: Node, kind: String) -> String:
	var id:=item_for(kind)
	if id.is_empty(): return "未知构件"
	var bp:=stock(owner)
	var amount:=amount_for(kind)
	if bp==null or bp.count_item(id)<amount: return "%s不足，需要 %d 份" % [NAMES[id],amount]
	return ""

static func grant(owner: Node, id: String) -> bool:
	var bp:=stock(owner)
	return bp!=null and bp.add_item(id,1)
