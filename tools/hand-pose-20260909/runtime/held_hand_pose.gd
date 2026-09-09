extends RefCounted
## A reversible finger-only layer over the authored animation and grip contacts.
var saved := {}
var enabled := true
var ads := 0.0

func restore(rig: Skeleton3D) -> void:
	if rig != null:
		for bone in saved: rig.set_bone_pose_rotation(bone, saved[bone])
	saved.clear()

func chain(rig: Skeleton3D, side: String, finger: String) -> Array:
	var result := []
	for j in 3:
		var name_ := finger + "_0" + str(j + 1) + "_" + side
		if rig.find_bone("mixamorig2_LeftHand") >= 0:
			name_ = "mixamorig2_" + ("Left" if side == "l" else "Right") + "Hand" + finger.capitalize() + str(j + 1)
		elif rig.find_bone("L_wrist") >= 0:
			name_ = ("L_" if side == "l" else "R_") + ("point" if finger == "index" else "pink" if finger == "pinky" else finger) + str(j + 1)
		result.append(rig.find_bone(name_))
	return result

func apply(rig: Skeleton3D, state, has_grip: bool, amount: float) -> void:
	ads = clampf(amount, 0.0, 1.0)
	if not enabled or rig == null: return
	var hold := 1.0
	if state.action not in ["", "idle", "aim", "fire", "aim_fire"] and state.elapsed < state.action_length:
		# Leave the middle of release/charging/inspection clips completely authored.
		hold = maxf(1.0 - smoothstep(0.0, .05, state.elapsed), smoothstep(state.action_length - .10, state.action_length, state.elapsed))
	if hold <= .00001: return
	for side in ["l", "r"]:
		# Installed foregrips already solve each joint against a physical contact.
		# Preserve those contacts instead of curling fingers through the grip.
		if side == "l" and has_grip: continue
		var fingers := {}
		for finger in ["index", "middle", "ring", "pinky"]:
			fingers[finger] = chain(rig, side, finger)
			if -1 in fingers[finger]: return
		var lateral: Vector3 = (rig.get_bone_global_pose(fingers.index[0]).origin - rig.get_bone_global_pose(fingers.pinky[0]).origin).normalized()
		var directions := {}
		var average := Vector3.ZERO
		var center := Vector3.ZERO
		for finger in fingers:
			var bones: Array = fingers[finger]
			var direction: Vector3 = (rig.get_bone_global_pose(bones[1]).origin - rig.get_bone_global_pose(bones[0]).origin).normalized()
			directions[finger] = direction
			average += direction * .25
			center += rig.get_bone_global_pose(bones[0]).origin * .25
		for finger in fingers:
			var bones: Array = fingers[finger]
			var trigger: bool = side == "r" and finger == "index"
			if trigger: continue # Keep the authored trigger contact and firing motion exact.
			var direction: Vector3 = directions[finger]
			var next_direction: Vector3 = (rig.get_bone_global_pose(bones[2]).origin - rig.get_bone_global_pose(bones[1]).origin).normalized()
			var bend_axis := direction.cross(next_direction)
			var close_strength := lerpf(.45, .80, ads) * hold
			var base := rig.get_bone_global_pose(bones[0]).origin
			var segment_length := base.distance_to(rig.get_bone_global_pose(bones[1]).origin)
			var convergence := (base - center).dot(lateral) / maxf(segment_length, .00001) * lerpf(.12, .28, ads) * hold
			var target := (direction - lateral * ((direction - average).dot(lateral) * close_strength + convergence)).normalized()
			var turn := Quaternion(direction, target)
			var angle := direction.angle_to(target)
			var limit := deg_to_rad(lerpf(7.0, 12.0, ads)) * hold
			if angle > limit: turn = Quaternion.IDENTITY.slerp(turn, limit / angle)
			rotate_global(rig, bones[0], turn)
			# Follow the source finger's existing flexion plane, preserving rig-specific axes.
			if bend_axis.length_squared() > .015 and not trigger:
				bend_axis = turn * bend_axis.normalized()
				var curl := deg_to_rad(lerpf(2.0, 5.0, ads) if side == "l" else lerpf(3.0, 7.0, ads)) * hold
				for joint in 3:
					rotate_global(rig, bones[joint], Quaternion(bend_axis, curl * [.55, 1.0, .60][joint]))

func rotate_global(rig: Skeleton3D, bone: int, rotation_: Quaternion) -> void:
	if not saved.has(bone): saved[bone] = rig.get_bone_pose_rotation(bone)
	var parent := rig.get_bone_parent(bone)
	var parent_rotation := rig.get_bone_global_pose(parent).basis.orthonormalized().get_rotation_quaternion()
	var current := rig.get_bone_global_pose(bone).basis.orthonormalized().get_rotation_quaternion()
	rig.set_bone_pose_rotation(bone, (parent_rotation.inverse() * rotation_ * current).normalized())
