extends SceneTree
## 无头验证：图标层（Lucide SVG → Godot 纹理）
## 运行： $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_icons.gd

const Icons := preload("res://ui/icons.gd")

var _fail := 0

func _check(name: String, ok: bool, detail := "") -> void:
	print("TEST ", name, "=", ok, "" if detail.is_empty() else "  " + detail)
	if not ok:
		_fail += 1

func _initialize() -> void:
	var required := ["heart", "shield", "sword", "crosshair", "zap", "waves", "coins", "gem",
		"backpack", "settings", "volume-2", "pause", "search", "x", "check", "chevron-down",
		"plus", "trash-2", "map", "flag", "trophy", "skull", "key", "lock", "eye", "info",
		"menu", "refresh-cw", "sparkles", "flame", "target", "save", "pencil-line", "activity",
		"timer", "star", "user", "footprints", "hard-hat", "radio", "circle-dollar-sign", "triangle-alert"]
	for name in required:
		var tex := Icons.get_icon(name)
		_check("icon_" + name, tex != null)
	_check("icon_missing_returns_null", Icons.get_icon("does-not-exist") == null)
	quit(0 if _fail == 0 else 1)
