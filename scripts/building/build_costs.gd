extends RefCounted
const COSTS={"floor":"wood","wall":"wood","ceiling":"wood","stone_floor":"stone","stone_wall":"stone","stone_ceiling":"stone","marble":"stone"}
const NAMES={"wood":"木材","stone":"石块"}

static func item_for(kind: String) -> String:
	return COSTS.get(kind,"")

static func stock(owner: Node) -> RefCounted:
	var hud:=owner.get_node_or_null("/root/HUD")
	return hud.backpack if hud!=null else null

static func error(owner: Node, kind: String) -> String:
	var id:=item_for(kind)
	if id.is_empty(): return "未知构件"
	var bp:=stock(owner)
	if bp==null or bp.count_item(id)<1: return "%s不足，需要 1 份" % NAMES[id]
	return ""

static func grant(owner: Node, id: String) -> bool:
	var bp:=stock(owner)
	return bp!=null and bp.add_item(id,1)
