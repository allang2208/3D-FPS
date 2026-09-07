extends RefCounted
## Grip-local contact directions; joint translations and source skin stay intact.
# Calibrated wrist: the two upper fingers enter the opening; lower fingers cup the heel.
const WRIST = Transform3D(Basis(Vector3(-.352673,.755907,-.551567),Vector3(.920399,.173903,-.350177),Vector3(-.168782,-.631159,-.757067)),Vector3(-.015230,-.127604,.071769))
const CLOSE_WINDOWS = {"index": Vector2(0,.70), "middle": Vector2(.08,.78), "ring": Vector2(.18,.88), "pinky": Vector2(.28,.94), "thumb": Vector2(.40,1.0)}
const CONTACTS = {
 "index": [Vector3(.004,-.027,-.002),Vector3(.036,-.027,.017),Vector3(.025,-.029,.044)],
 "middle": [Vector3(.004,-.039,-.013),Vector3(.038,-.041,.008),Vector3(.025,-.042,.037)],
 "ring": [Vector3(-.007,-.091,-.021),Vector3(.030,-.088,-.002),Vector3(.027,-.062,.022)],
 "pinky": [Vector3(.005,-.113,-.026),Vector3(.023,-.110,-.011),Vector3(.023,-.088,.008)],
 "thumb": [Vector3(-.021,-.033,.063),Vector3(.017,-.027,.065),Vector3(.026,-.043,.047)]
}
const VERTICAL_CONTACTS = {
 "index":[Vector3(-.012,-.030,-.029),Vector3(.024,-.030,-.029),Vector3(.030,-.032,.010)],
 "middle":[Vector3(-.012,-.050,-.029),Vector3(.024,-.050,-.029),Vector3(.030,-.050,.010)],
 "ring":[Vector3(-.012,-.071,-.029),Vector3(.024,-.071,-.029),Vector3(.030,-.071,.010)],
 "pinky":[Vector3(-.012,-.090,-.029),Vector3(.024,-.090,-.029),Vector3(.030,-.090,.010)],
 "thumb":[Vector3(-.028,-.029,.030),Vector3(.005,-.026,.033),Vector3(.019,-.046,.026)]
}
# Side-canted grip: stagger the pads around the body and tuck the thumb above the index.
const CANTED_CONTACTS = {
 "index":[Vector3(-.012,-.030,-.029),Vector3(.024,-.030,-.029),Vector3(.028,-.034,.012)],
 "middle":[Vector3(-.012,-.050,-.029),Vector3(.024,-.050,-.029),Vector3(.028,-.051,.013)],
 "ring":[Vector3(-.012,-.071,-.029),Vector3(.024,-.070,-.029),Vector3(.029,-.068,.012)],
 "pinky":[Vector3(-.012,-.090,-.029),Vector3(.024,-.087,-.029),Vector3(.029,-.082,.010)],
 "thumb":[Vector3(-.028,-.029,.030),Vector3(.005,-.024,.035),Vector3(.018,-.038,.030)]
}
static func finger_curl(finger: String, curl: float) -> float:
	var window: Vector2 = CLOSE_WINDOWS[finger]
	return smoothstep(window.x,window.y,curl)

static func apply(rig: Skeleton3D, frame: Transform3D, weight: float, saved: Dictionary, curl: float = 1.0, profile = null, vertical: bool = false, canted: bool = false) -> void:
	var contacts=CANTED_CONTACTS if canted else VERTICAL_CONTACTS if vertical else CONTACTS
	for finger in contacts:
		var closing := finger_curl(finger,curl)
		for joint in 3:
			var bone=profile.fingers[finger][joint] if profile!=null else rig.find_bone(finger+"_0"+str(joint+1)+"_l")
			saved[bone]=rig.get_bone_pose_rotation(bone)
			var pose=rig.get_bone_global_pose(bone)
			var current=pose.basis.orthonormalized().get_rotation_quaternion()
			var contact: Vector3=contacts[finger][joint]
			if not vertical and profile!=null and rig.find_bone("hand_l")<0 and joint==1:
				if finger=="middle":contact.z-=.010
				elif finger=="index":contact.z-=.008
			if finger in ["index","middle","ring","pinky"] and joint>0:
				var straight: Vector3=contacts[finger][0]+(Vector3(0,0,-.034 if joint==1 else -.064) if vertical else Vector3(.034 if joint==1 else .064,0,0))
				contact=straight.lerp(contact,closing)
			elif finger=="thumb" and joint>0:
				contact+=Vector3(0,0,.006*(1.0-closing))
			var direction=(frame*contact-pose.origin).normalized()
			var local_axis=Vector3.RIGHT
			if profile!=null and rig.find_bone("hand_l")<0:
				local_axis=Vector3.UP if profile.separate_hand else Vector3.FORWARD
			var desired=Quaternion((pose.basis*local_axis).normalized(),direction)*current
			if not vertical and finger in ["index","middle"] and joint==2:
				# Present the broad finger pad to the rod instead of touching with one corner.
				var outward := frame.basis.x.normalized()
				var pad_normal: Vector3 = (outward-direction*outward.dot(direction)).normalized()
				var aligned := Basis(direction,pad_normal,direction.cross(pad_normal)).get_rotation_quaternion()
				aligned=aligned*Quaternion(local_axis,Vector3.RIGHT)
				desired=desired.slerp(aligned,closing*.65)
			var parent=rig.get_bone_global_pose(rig.get_bone_parent(bone)).basis.orthonormalized().get_rotation_quaternion()
			var local=(parent.inverse()*desired).normalized()
			rig.set_bone_pose_rotation(bone,saved[bone].slerp(local,weight))
