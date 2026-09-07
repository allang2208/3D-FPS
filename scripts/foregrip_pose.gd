extends RefCounted
## Post-animation two-bone left-arm adaptation. Source poses are restored before evaluation.
var saved := {}
var saved_positions := {}
var action := ""
var elapsed := 0.0
var action_length := 0.0
var action_speed := 1.0
var weight := 0.0
var support_angle := 0.0
var forearm_roll := 0.0

func restore(rig: Skeleton3D) -> void:
	for bone in saved:
		rig.set_bone_pose_rotation(bone,saved[bone])
	saved.clear()
	for bone in saved_positions:rig.set_bone_pose_position(bone,saved_positions[bone])
	saved_positions.clear()

func begin(clip: StringName, length: float, speed: float) -> void:
	action=str(clip);elapsed=0.0;action_length=length;action_speed=speed

func advance(delta: float) -> void:
	elapsed+=delta*action_speed

func apply(rig: Skeleton3D, part: Node3D, profile = null) -> void:
	weight=1.0
	var withdrawal := 0.0
	var curl := 1.0
	var approaching := false
	if action not in ["","fire","aim_fire","equip_quick"] and elapsed<action_length:
		# First unhook, then withdraw through the opening, then resume the source action.
		var return_start=action_length-.22
		if action=="reload":return_start=profile.return_times.x if profile!=null else 1.85
		elif action=="reload_empty":return_start=profile.return_times.y if profile!=null else 2.15
		var end := action_length-.02
		# Finish at the installed grip before the source clip returns to factory support.
		if action=="equip_charge" and profile!=null:
			return_start=minf(profile.equip_return.x,action_length-.12)
			end=minf(profile.equip_return.y,action_length-.02)
		var approach := minf(return_start+.14,lerpf(return_start,end,.5))
		var insert := lerpf(return_start,end,.82)
		weight=smoothstep(return_start,approach,elapsed)
		approaching=elapsed>=return_start and elapsed<approach
		withdrawal=.070*(1.0-smoothstep(approach,insert,elapsed))
		curl=smoothstep(insert,end,elapsed)
		if action in ["reload","reload_empty","inspect","holster"] and elapsed<.40:
			weight=1.0-smoothstep(.25,.40,elapsed)
			withdrawal=.070*smoothstep(.05,.15,elapsed)
			curl=1.0-smoothstep(0.0,.05,elapsed)
	if weight<=0.0001:return
	var upper=profile.upper if profile!=null else rig.find_bone("upperarm_l")
	var lower=profile.lower if profile!=null else rig.find_bone("lowerarm_l")
	var hand=profile.hand if profile!=null else rig.find_bone("hand_l")
	for bone in [upper,lower,hand]:saved[bone]=rig.get_bone_pose_rotation(bone)
	var holder: BoneAttachment3D=part.get_parent()
	var weapon_rig:Skeleton3D=holder.get_parent()
	var contact_frame=rig.global_transform.affine_inverse()*weapon_rig.global_transform*weapon_rig.get_bone_global_pose(holder.bone_idx)*part.transform
	if profile!=null and rig.find_bone("hand_l")<0:withdrawal*=1.6
	contact_frame.origin+=contact_frame.basis*Vector3(-withdrawal,0,withdrawal*(1.0-weight))
	var target=contact_frame*part.get_node("HandTarget").transform
	var a=rig.get_bone_global_pose(upper).origin
	var b=rig.get_bone_global_pose(lower).origin
	var c=rig.get_bone_global_pose(hand).origin
	var destination=c.lerp(target.origin,weight)
	if part.get_meta("classic_grip",false) or part.has_node("GripPoseFrame"):
		if elapsed<.40 and weight<1.0 and not approaching:
			destination-=contact_frame.basis.x*(.12 if part.has_node("GripPoseFrame") else .06)*sin(PI*sqrt(1.0-weight))
		elif approaching and not part.get_meta("vertical_grip",false):
			destination-=contact_frame.basis.x*.04*sin(PI*sqrt(weight))
	if part.get_meta("vertical_grip",false) and approaching:
		destination+=(contact_frame.basis.y*float(part.get_meta("vertical_return_lift",0.0))-contact_frame.basis.x*(.12 if part.has_node("GripPoseFrame") else .04))*sin(PI*sqrt(weight))
	if profile!=null and profile.separate_hand and approaching and action=="reload_empty":
		destination+=contact_frame.basis.y*.065*sin(PI*sqrt(weight))
	var l1=a.distance_to(b);var l2=b.distance_to(c)
	var direction=(destination-a).normalized()
	var d=clampf(a.distance_to(destination),absf(l1-l2)+.001,l1+l2-.001)
	var along=(l1*l1-l2*l2+d*d)/(2*d)
	var bend=(b-a)-direction*(b-a).dot(direction)
	if bend.length_squared()<.000001:bend=direction.cross(Vector3.UP)
	# A small elbow response absorbs the shot while the wrist and fingers stay anchored.
	support_angle=sin(PI*clampf(elapsed/.18,0.0,1.0))*.035 if action in ["fire","aim_fire"] and elapsed<.18 else 0.0
	bend=bend.rotated(direction,support_angle)
	var elbow=a+direction*along+bend.normalized()*sqrt(maxf(0,l1*l1-along*along))
	_rotate_toward(rig,upper,b-a,elbow-a)
	b=rig.get_bone_global_pose(lower).origin;c=rig.get_bone_global_pose(hand).origin
	_rotate_toward(rig,lower,c-b,destination-b)
	if profile!=null and profile.separate_hand:
		saved_positions[hand]=rig.get_bone_pose_position(hand)
		rig.set_bone_pose_position(hand,rig.get_bone_global_pose(rig.get_bone_parent(hand)).affine_inverse()*destination)
	var desired=rig.get_bone_global_pose(hand).basis.orthonormalized().get_rotation_quaternion().slerp(target.basis.orthonormalized().get_rotation_quaternion(),weight)
	# Share axial rotation with the forearm; rotation about elbow->wrist preserves reach.
	var before=rig.get_bone_global_pose(hand).basis.orthonormalized().get_rotation_quaternion()
	var correction=desired*before.inverse()
	var axis=(rig.get_bone_global_pose(hand).origin-rig.get_bone_global_pose(lower).origin).normalized()
	var projected=axis*Vector3(correction.x,correction.y,correction.z).dot(axis)
	var twist=Quaternion(projected.x,projected.y,projected.z,correction.w).normalized()
	var distributed=Quaternion.IDENTITY.slerp(twist,.42*weight)
	forearm_roll=distributed.get_angle()
	_set_global_rotation(rig,lower,distributed*rig.get_bone_global_pose(lower).basis.orthonormalized().get_rotation_quaternion())
	_set_global_rotation(rig,hand,desired)
	var finger_frame=contact_frame*part.get_node("GripPoseFrame").transform if part.has_node("GripPoseFrame") else contact_frame
	preload("res://scripts/foregrip_finger_pose.gd").apply(rig,finger_frame,sqrt(weight),saved,curl,profile,part.get_meta("vertical_grip",false),part.has_node("GripPoseFrame"))

func _rotate_toward(rig: Skeleton3D, bone: int, from: Vector3, to: Vector3) -> void:
	var current=rig.get_bone_global_pose(bone).basis.orthonormalized().get_rotation_quaternion()
	_set_global_rotation(rig,bone,Quaternion(from.normalized(),to.normalized())*current)

func _set_global_rotation(rig: Skeleton3D, bone: int, rotation: Quaternion) -> void:
	var parent=rig.get_bone_parent(bone)
	var parent_rotation=rig.get_bone_global_pose(parent).basis.orthonormalized().get_rotation_quaternion()
	rig.set_bone_pose_rotation(bone,(parent_rotation.inverse()*rotation).normalized())
