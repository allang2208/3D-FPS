extends Node3D
## 场景通用 HUD 验证：无自建 HUD 的场景应自动获得 autoload(HUD) 的完整 HUD

var _frames := 0


func _ready() -> void:
	var player := CharacterBody3D.new()
	player.name = "Player"
	player.set_script(load("res://scripts/player.gd"))
	add_child(player)


func _process(_delta: float) -> void:
	_frames += 1
	if _frames < 20:
		return
	var hud := get_tree().root.get_node_or_null("HUD")
	var bph: Control = hud.get("_backpack_hud") if hud != null else null
	var sbar: CanvasLayer = hud.get("_status_bar") if hud != null else null
	print("HUD autoload: ", hud != null,
		"  backpack_hud: ", bph != null,
		"  status_bar: ", sbar != null,
		"  data: ", hud != null and hud.backpack != null)
	# 唯一性：全树不应有第二个 BackpackHud
	var count := 0
	for node in get_tree().get_nodes_in_group("__none__"):
		pass
	var all := get_tree().root.find_children("BackpackHud", "", true, false)
	count = all.size()
	print("BackpackHud count in tree: ", count)
	get_tree().quit(0 if hud != null and bph != null and sbar != null and hud.backpack != null and count == 1 else 1)
