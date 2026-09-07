extends SceneTree

## Converts retained GPT image albedo sources into Terrain3D channel-packed
## candidate maps. Height/normal/roughness are artistic approximations, not
## photogrammetry; sources stay untouched for later Material Maker replacement.
## The default batch contains accepted sources only. Rejected experiments can
## still be rebuilt explicitly with --source and --output when needed.

const DIR := "res://assets/textures/wilderness_generated/"
const WORK_SIZE := 1024
const ARRAY_SIZE := 4096
const EDGE_BLEND := 32
const SOURCES := [
	{
		"source": "colluvium_albedo_gptimage2_v1.png",
		"output": "colluvium_gptimage2_v1",
		"normal_strength": 3.8,
		"roughness": 0.91,
		"height_gain": 2.0,
	},
]


func _initialize() -> void:
	var custom := _custom_spec(OS.get_cmdline_user_args())
	if not custom.is_empty():
		_build_candidate(custom)
		quit()
		return
	for spec in SOURCES:
		_build_candidate(spec)
	quit()


func _custom_spec(args: PackedStringArray) -> Dictionary:
	var spec := {
		"source": "",
		"output": "",
		"normal_strength": 3.0,
		"roughness": 0.88,
		"height_gain": 1.7,
	}
	for arg in args:
		if arg.begins_with("--source="): spec.source=arg.trim_prefix("--source=")
		elif arg.begins_with("--output="): spec.output=arg.trim_prefix("--output=")
		elif arg.begins_with("--normal-strength="): spec.normal_strength=float(arg.trim_prefix("--normal-strength="))
		elif arg.begins_with("--roughness="): spec.roughness=float(arg.trim_prefix("--roughness="))
		elif arg.begins_with("--height-gain="): spec.height_gain=float(arg.trim_prefix("--height-gain="))
	if String(spec.source).is_empty(): return {}
	assert(not String(spec.output).is_empty(), "--output is required with --source")
	return spec


func _build_candidate(spec: Dictionary) -> void:
	var source_path := String(spec.source)
	if not source_path.begins_with("res://") and not source_path.is_absolute_path():
		source_path=DIR+source_path
	var source := Image.load_from_file(ProjectSettings.globalize_path(source_path) if source_path.begins_with("res://") else source_path)
	assert(source != null and not source.is_empty())
	source.resize(WORK_SIZE, WORK_SIZE, Image.INTERPOLATE_LANCZOS)
	source.convert(Image.FORMAT_RGBA8)
	_make_periodic(source)
	var color := source.get_data()
	var luminance := PackedFloat32Array()
	luminance.resize(WORK_SIZE * WORK_SIZE)
	for index in luminance.size():
		luminance[index] = (color[index * 4] * 0.2126 + color[index * 4 + 1] * 0.7152 + color[index * 4 + 2] * 0.0722) / 255.0
	var heights := PackedFloat32Array()
	heights.resize(luminance.size())
	for y in WORK_SIZE:
		for x in WORK_SIZE:
			var index := y * WORK_SIZE + x
			var broad := 0.0
			for offset in [4, 12, 28]:
				broad += luminance[y * WORK_SIZE + posmod(x - offset, WORK_SIZE)]
				broad += luminance[y * WORK_SIZE + posmod(x + offset, WORK_SIZE)]
				broad += luminance[posmod(y - offset, WORK_SIZE) * WORK_SIZE + x]
				broad += luminance[posmod(y + offset, WORK_SIZE) * WORK_SIZE + x]
			broad /= 12.0
			heights[index] = clampf(0.5 + (luminance[index] - broad) * float(spec.height_gain), 0.12, 0.88)
	var normals := PackedByteArray()
	normals.resize(color.size())
	for y in WORK_SIZE:
		for x in WORK_SIZE:
			var index := y * WORK_SIZE + x
			var dx := heights[y * WORK_SIZE + posmod(x + 1, WORK_SIZE)] - heights[y * WORK_SIZE + posmod(x - 1, WORK_SIZE)]
			var dy := heights[posmod(y + 1, WORK_SIZE) * WORK_SIZE + x] - heights[posmod(y - 1, WORK_SIZE) * WORK_SIZE + x]
			var normal := Vector3(-dx * float(spec.normal_strength), -dy * float(spec.normal_strength), 1.0).normalized()
			for axis in 3:
				normals[index * 4 + axis] = roundi((normal[axis] * 0.5 + 0.5) * 255.0)
			var roughness := clampf(float(spec.roughness) + (0.5 - heights[index]) * 0.12, 0.68, 0.98)
			normals[index * 4 + 3] = roundi(roughness * 255.0)
			color[index * 4 + 3] = roundi(heights[index] * 255.0)
	var albedo_height := Image.create_from_data(WORK_SIZE, WORK_SIZE, false, Image.FORMAT_RGBA8, color)
	var normal_roughness := Image.create_from_data(WORK_SIZE, WORK_SIZE, false, Image.FORMAT_RGBA8, normals)
	_save_pair(albedo_height, normal_roughness, String(spec.output))
	print("WILDERNESS_PBR_CANDIDATE ", spec.output)


func _make_periodic(image: Image) -> void:
	for axis in 2:
		for along in WORK_SIZE:
			for distance in EDGE_BLEND:
				var a := Vector2i(distance, along) if axis == 0 else Vector2i(along, distance)
				var b := Vector2i(WORK_SIZE - 1 - distance, along) if axis == 0 else Vector2i(along, WORK_SIZE - 1 - distance)
				var average := image.get_pixelv(a).lerp(image.get_pixelv(b), 0.5)
				var weight := 1.0 - smoothstep(0.0, float(EDGE_BLEND), float(distance))
				image.set_pixelv(a, image.get_pixelv(a).lerp(average, weight))
				image.set_pixelv(b, image.get_pixelv(b).lerp(average, weight))


func _save_pair(albedo_height: Image, normal_roughness: Image, output: String) -> void:
	for entry in [[albedo_height, "alb_ht"], [normal_roughness, "nrm_rgh"]]:
		var map: Image = entry[0]
		assert(map.save_png(DIR + output + "_1k_" + entry[1] + ".png") == OK)
		map.resize(ARRAY_SIZE, ARRAY_SIZE, Image.INTERPOLATE_LANCZOS)
		assert(map.save_png(DIR + output + "_" + entry[1] + ".png") == OK)
