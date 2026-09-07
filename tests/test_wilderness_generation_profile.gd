extends SceneTree

const Profile := preload("res://scripts/wilderness_generation_profile.gd")

var failures: Array[String] = []


func _check(condition: bool, label: String) -> void:
	print("[wilderness-profile-test] ", "PASS " if condition else "FAIL ", label)
	if not condition:
		failures.append(label)


func _initialize() -> void:
	var a := Profile.new(424242)
	var b := Profile.new(424242)
	var c := Profile.new(424243)
	var samples := [Vector2(-4100, 1700), Vector2(0, 0), Vector2(1900, -700)]
	for p in samples:
		_check(is_equal_approx(a.height_at(p), b.height_at(p)), "same seed reproduces height at " + str(p))
	_check(not is_equal_approx(a.height_at(samples[0]), c.height_at(samples[0])), "different seed changes terrain")
	_check(a.detail_band(449.0) == &"entity", "near band permits entities")
	_check(a.detail_band(451.0) == &"impostor", "middle band uses impostors")
	_check(a.detail_band(1501.0) == &"texture", "far band uses texture only")
	_check(is_equal_approx(Profile.WORLD_SIZE_M, Profile.NEAR_WORLD_SIZE_M * 10.0), "world width is exactly ten times near terrain")
	_check(a.biome_at(Vector2(0, a.river_center_z(0))) == &"river", "river formula and biome mask share coordinates")
	quit(0 if failures.is_empty() else 1)
