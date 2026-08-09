extends RefCounted
## 图标工具：Lucide SVG → Godot 纹理（assets/ui/icons/*.svg，黑色 stroke）
## 用法：TextureRect 用 Style.Icons.get_icon("heart")，着色用 modulate（黑色乘任意色）
## 生成图标：tools/gen-icons.ps1（从本地 shadcn-ui 仓库的 lucide-react 提取）

const ICON_DIR := "res://assets/ui/icons/"

static var _cache: Dictionary = {}

static func has(name: String) -> bool:
	return ResourceLoader.exists(ICON_DIR + name + ".svg")

static func get_icon(name: String) -> Texture2D:
	if _cache.has(name):
		return _cache[name]
	if not has(name):
		return null
	var tex: Texture2D = load(ICON_DIR + name + ".svg")
	_cache[name] = tex
	return tex

## 便捷：给 TextureRect 设置图标 + 颜色（modulate 黑色 stroke → 任意色）
static func apply_icon(rect: TextureRect, name: String, color: Color) -> void:
	var tex := get_icon(name)
	if tex == null:
		rect.texture = null
		rect.visible = false
		return
	rect.texture = tex
	rect.visible = true
	rect.modulate = color

## 便捷：生成带图标的 Label 纹理（用于无 TextureRect 的场景）？暂无需要。
