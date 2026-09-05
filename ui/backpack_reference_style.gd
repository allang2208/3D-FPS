extends RefCounted
## Visual values from the supplied 1912x948 screenshot and game-style.css.
static var _cache := {}
static func surface(top: String, bottom: String, border: String, radius := 8, width := 2, padding := 0) -> StyleBoxTexture:
	var key := str([top, bottom, border, radius, width])
	if not _cache.has(key):
		var img := Image.create(128, 128, false, Image.FORMAT_RGBA8)
		for y in 128:
			for x in 128:
				var point := Vector2(x + 0.5, y + 0.5)
				var center := point.clamp(Vector2.ONE * radius, Vector2.ONE * (128 - radius))
				var distance := point.distance_to(center)
				var color := Color(top).lerp(Color(bottom), y / 127.0)
				if x < width or y < width or x >= 128-width or y >= 128-width or distance > radius-width:
					color = Color(border)
				color.a *= 1.0 if radius == 0 else clampf(radius + 0.5 - distance, 0, 1)
				img.set_pixel(x, y, color)
		_cache[key] = ImageTexture.create_from_image(img)
	var box := StyleBoxTexture.new()
	box.texture = _cache[key]
	for edge in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		box.set_texture_margin(edge, radius)
		box.set_content_margin(edge, padding)
	return box

static func clear_cache() -> void:
	_cache.clear()
