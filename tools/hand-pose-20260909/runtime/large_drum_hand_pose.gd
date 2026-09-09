extends "res://scripts/foregrip_pose.gd"
## Keep the source wrist orientation and elbow plane; resolve only the extra
## drum-shell volume during the existing left-hand magazine handling action.
var correction_meters:=0.0
func clear_shell(part:Node3D,profile,influence:float=1.0) -> void:
	correction_meters=0.0
	if profile.rig==null or influence<=0.0: return
	var rig:Skeleton3D=profile.rig
	var drum:Node3D=part.get_node("LargeDrum")
	var holder:BoneAttachment3D=part.get_parent()
	var weapon_rig:Skeleton3D=holder.get_parent()
	var world:=weapon_rig.global_transform*weapon_rig.get_bone_global_pose(holder.bone_idx)*part.transform*drum.transform
	var hand:int=profile.hand
	var wrist:=rig.get_bone_global_pose(hand)
	var finger:int=profile.fingers.middle[0]
	var palm:=wrist.origin.lerp(rig.get_bone_global_pose(finger).origin,.65)
	var local_delta:=Vector3.ZERO
	for sample:Vector3 in [palm,wrist.origin]:
		var local:=world.affine_inverse()*(rig.global_transform*sample)
		var radial:=Vector2(local.x,local.y+.085)
		if absf(local.z)>.065 or radial.length()>.080 or local.y>-.035: continue
		var direction:=radial.normalized() if radial.length()>.001 else Vector2.LEFT
		var target:=local
		target.x=direction.x*.080
		target.y=direction.y*.080-.085
		var blend_weight:=smoothstep(.065,.040,absf(local.z))*smoothstep(-.035,-.055,local.y)
		var push:=(target-local)*blend_weight
		if push.length_squared()>local_delta.length_squared():local_delta=push
	if local_delta.is_zero_approx():return
	# Magazine handling yields to the installed grip's contact constraint.
	local_delta*=clampf(influence,0.0,1.0)
	var delta:=rig.global_transform.affine_inverse().basis*(world.basis*local_delta)
	correction_meters=(world.basis*local_delta).length()
	var destination:=wrist.origin+delta
	var upper:int=profile.upper
	var lower:int=profile.lower
	for bone in [upper,lower,hand]:saved[bone]=rig.get_bone_pose_rotation(bone)
	var a:=rig.get_bone_global_pose(upper).origin
	var b:=rig.get_bone_global_pose(lower).origin
	var c:=wrist.origin
	var tip_local:=rig.get_bone_global_pose(lower).affine_inverse()*c
	var l1:=a.distance_to(b)
	var l2:=b.distance_to(c)
	var d:=clampf(a.distance_to(destination),absf(l1-l2)+.001,l1+l2-.001)
	var axis:=(destination-a).normalized()
	if profile.separate_hand:destination=a+axis*d
	var along:=(l1*l1-l2*l2+d*d)/(2*d)
	var bend:=(b-a)-axis*(b-a).dot(axis)
	if bend.length_squared()<.000001:bend=axis.cross(Vector3.UP)
	var elbow:=a+axis*along+bend.normalized()*sqrt(maxf(0,l1*l1-along*along))
	_rotate_toward(rig,upper,b-a,elbow-a)
	b=rig.get_bone_global_pose(lower).origin
	c=rig.get_bone_global_pose(hand).origin
	if profile.separate_hand:c=rig.get_bone_global_pose(lower)*tip_local
	_rotate_toward(rig,lower,c-b,destination-b)
	if profile.separate_hand:
		saved_positions[hand]=rig.get_bone_pose_position(hand)
		rig.set_bone_pose_position(hand,rig.get_bone_global_pose(rig.get_bone_parent(hand)).affine_inverse()*destination)
	_set_global_rotation(rig,hand,wrist.basis.orthonormalized().get_rotation_quaternion())
