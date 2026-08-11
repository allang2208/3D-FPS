extends SceneTree
## 探针：确认 Godot 4.7.1 的 SkeletonModifier3D / IKModifier3D API（类、属性、枚举）

var _frames := 0

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		for cls in ["SkeletonModifier3D", "IKModifier3D", "IterateIK3D", "TwoBoneIK3D", "ChainIK3D", "SplineIK3D"]:
			print("class ", cls, " exists=", ClassDB.class_exists(cls))
		print("enum ROTATION_AXIS_ALL=", SkeletonModifier3D.ROTATION_AXIS_ALL)
		print("enum BONE_DIRECTION_PLUS_Y=", SkeletonModifier3D.BONE_DIRECTION_PLUS_Y)
		print("--- IKModifier3D props (all, with hints) ---")
		for pr in ClassDB.class_get_property_list("IKModifier3D", false):
			print("prop ", pr.name, " type=", pr.type, " hint=", pr.hint, " hint_string=", pr.hint_string)
		print("--- Skeleton3D methods ---")
		var sk := Skeleton3D.new()
		for m in ["add_bone", "set_bone_parent", "set_bone_rest", "set_bone_pose", "get_bone_global_rest", "get_bone_global_pose"]:
			print("Skeleton3D.", m, "=", sk.has_method(m))
		sk.free()
		quit(0)
	return false
