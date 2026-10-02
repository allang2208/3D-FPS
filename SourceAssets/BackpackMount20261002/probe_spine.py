import unreal
U = unreal
body = U.load_asset("/Game/Characters/Mannequins/PlayerBodySkin/SKM_Manny_PlayerSkin.SKM_Manny_PlayerSkin")
pose = body.get_editor_property("skeleton").get_reference_pose()
bone = pose.get_bone_pose("spine_03", U.AnimPoseSpaces.WORLD)
des = U.Transform()
des.translation = U.Vector(0.0, -19.0, 122.0)
des.rotation = U.Rotator(0.0, 90.0, 0.0).quaternion()
des.scale3d = U.Vector(1.0, 1.0, 1.0)
rel = bone.inverse() * des
r = rel.rotation.rotator()
l = rel.translation
print("attach_location [%.3f, %.3f, %.3f]" % (l.x, l.y, l.z))
print("attach_rotation(pitch,yaw,roll) [%.3f, %.3f, %.3f]" % (r.pitch, r.yaw, r.roll))
