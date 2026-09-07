extends RefCounted
class Ghost:
	extends Control
	var overlay: CanvasLayer
	func _process(_delta: float) -> void:
		overlay.transform = Transform2D(0, global_position)

## Shared drag ghost. No mutation of inventory while dragging.
## Spatial items carry their complete footprint and keep the grabbed cell under
## the cursor, so an 8x2 rifle never collapses to a generic 1x1 icon.
static func make(
	item: Dictionary,
	footprint := Vector2i.ONE,
	cell_side := 56.0,
	grab_cell := Vector2i.ZERO,
	icon_override: Texture2D = null,
	cell_style: StyleBox = null
) -> Control:
	var root := Ghost.new()
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.modulate.a = 0.82
	root.overlay = CanvasLayer.new()
	root.overlay.name = "Overlay"
	root.overlay.layer = 128
	root.add_child(root.overlay)
	var visual := Control.new()
	visual.name = "SpatialVisual"
	visual.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var safe_footprint := Vector2i(maxi(1, footprint.x), maxi(1, footprint.y))
	var safe_side := maxf(1.0, cell_side)
	var total_size := Vector2(safe_footprint) * safe_side
	var safe_grab := Vector2i(clampi(grab_cell.x, 0, safe_footprint.x - 1), clampi(grab_cell.y, 0, safe_footprint.y - 1))
	visual.position = -(Vector2(safe_grab) * safe_side + Vector2.ONE * safe_side * 0.5)
	visual.size = total_size
	root.overlay.add_child(visual)
	var cells := Control.new()
	cells.name = "FootprintCells"
	cells.mouse_filter = Control.MOUSE_FILTER_IGNORE
	cells.size = total_size
	visual.add_child(cells)
	for y in safe_footprint.y:
		for x in safe_footprint.x:
			var tile := Panel.new()
			tile.mouse_filter = Control.MOUSE_FILTER_IGNORE
			tile.position = Vector2(x, y) * safe_side
			tile.size = Vector2.ONE * safe_side
			if cell_style != null:
				tile.add_theme_stylebox_override("panel", cell_style)
			else:
				var fallback_style := StyleBoxFlat.new()
				fallback_style.bg_color = Color("#3c3c3ccc")
				fallback_style.border_color = Color("#787878")
				fallback_style.set_border_width_all(1)
				tile.add_theme_stylebox_override("panel", fallback_style)
			cells.add_child(tile)
	var icon := TextureRect.new()
	icon.name = "Icon"
	icon.position = Vector2.ZERO
	icon.size = total_size
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	icon.modulate.a = 0.88
	icon.texture = icon_override
	if icon.texture == null:
		for field in ["slotImage", "iconImage", "icon"]:
			var path := str(item.get(field, ""))
			if not path.is_empty() and ResourceLoader.exists(path):
				var texture = load(path)
				if texture is Texture2D:
					icon.texture = texture
					break
	visual.add_child(icon)
	if icon.texture == null:
		var fallback := Label.new()
		fallback.name = "Fallback"
		fallback.text = str(item.get("icon_fallback", "◇"))
		fallback.position = Vector2.ZERO
		fallback.size = total_size
		fallback.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		fallback.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		fallback.add_theme_font_size_override("font_size", 32)
		fallback.mouse_filter = Control.MOUSE_FILTER_IGNORE
		visual.add_child(fallback)
	return root
