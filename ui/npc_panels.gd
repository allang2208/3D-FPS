extends RefCounted
## NPC 子面板宿主（UI 迁移线）：任一场景一键挂载 7 个选项面板并接到 npc_bar。
## 用法：
##   var panels = NpcPanels.build(self, db, backpack, equipment, economy, npc_bar)
##   选项分发：NpcPanels.open(panels, npc_bar, "enhance")
##   面板关闭后自动回到对话框（reopen）；quest/expedition 信号从 panels 里取：
##   panels["quest"].teleport_requested / panels["expedition"].depart_requested

const PANEL_SCRIPTS := {
	"shop": "res://ui/shop_panel.gd",
	"enhance": "res://ui/enhance_panel.gd",
	"craft": "res://ui/craft_panel.gd",
	"enchant": "res://ui/enchant_panel.gd",
	"quest": "res://ui/quest_panel.gd",
	"fusion": "res://ui/fusion_panel.gd",
	"expedition": "res://ui/expedition_panel.gd",
	"warehouse": "res://ui/warehouse_panel.gd",
}

static func title_of(key: String) -> String:
	match key:
		"shop":
			return "🏪 商店"
		"enhance":
			return "⚒️ 强化"
		"craft":
			return "🔧 改造"
		"enchant":
			return "✨ 附魔"
		"quest":
			return "📜 任务日志"
		"fusion":
			return "🔮 祭品合成"
		"expedition":
			return "⚔️ 献祭出征"
		"warehouse":
			return "📦 仓库"
	return ""

static func build(host: Node, db, backpack, equipment, economy, npc_bar,
		warehouse = null, player_status = null) -> Dictionary:
	var out := {}
	for key in PANEL_SCRIPTS:
		var panel = load(PANEL_SCRIPTS[key]).new()
		panel.name = key.capitalize() + "Panel"
		host.add_child(panel)
		panel.setup(db, backpack, equipment, economy)
		if panel.has_method("set_warehouse"):
			panel.set_warehouse(warehouse)
		if panel.has_method("set_player_status"):
			panel.set_player_status(player_status)
		panel.set_title(title_of(key))
		panel.closed.connect(func() -> void:
			if npc_bar != null:
				npc_bar.reopen())
		out[key] = panel
	return out

static func open(panels: Dictionary, npc_bar, id: String) -> bool:
	if not panels.has(id):
		return false
	if npc_bar != null:
		npc_bar.close()
	panels[id].open_panel()
	return true

## 旷野等轻量场景的测试物资（主场景在 _build_backpack_hud 里另有种子）
static func seed_materials(backpack) -> void:
	backpack.add_item("rusty_sword", 1)
	backpack.add_item("g18_pistol", 1)
	backpack.add_item("enhancement_stone", 3)
	backpack.add_item("reforge_ticket", 2)
	backpack.add_item("magic_dust", 150)
	backpack.add_item("enchant_scroll_heavy", 1)
	backpack.add_item("enchant_scroll_sharp", 1)
	backpack.add_item("enchant_scroll_tarantula", 1)
	backpack.add_item("enchant_scroll_skeleton", 1)
	backpack.add_item("tribute_common", 4)
	backpack.add_item("tribute_uncommon", 2)
