import unreal
U = unreal
body = U.load_asset("/Game/Characters/Mannequins/PlayerBodySkin/SKM_Manny_PlayerSkin.SKM_Manny_PlayerSkin")
pose = body.get_editor_property("skeleton").get_reference_pose()
bone = pose.get_bone_pose("spine_03", U.AnimPoseSpaces.WORLD)

# 期望组件空间放置：包体无旋转（+Z 上、+Y 背带面贴身体正面方向）、背面居中
for loc in ((0.0,-13.0,125.0),(0.0,-13.0,122.0)):
    des = U.Transform()
    des.translation = U.Vector(*loc)
    des.rotation = U.Rotator(0.0,0.0,0.0).quaternion()
    des.scale3d = U.Vector(1.0,1.0,1.0)
    rel = des.make_relative(bone)
    r = rel.rotation.rotator(); l = rel.translation
    # 验证：bone ∘ rel 应还原 des（此 API 的 * 是 b*a 顺序，用 rel*bone 验证）
    back = rel * bone
    ok = abs(back.translation.x-loc[0])<0.1 and abs(back.translation.y-loc[1])<0.1 and abs(back.translation.z-loc[2])<0.1
    print(f"des{loc} rel loc=[{l.x:.2f},{l.y:.2f},{l.z:.2f}] rot(p,y,r)=[{r.pitch:.2f},{r.yaw:.2f},{r.roll:.2f}] verify={ok}")
