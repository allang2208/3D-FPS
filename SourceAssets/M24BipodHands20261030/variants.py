from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('metrics=[];')[0],'setup','exec'))
t=.24;original=sample_pose(t)
def rotate_arm(row,degrees):
    old=clone(row);U=old['lowerarm_l'].translation-old['upperarm_l'].translation;L=old['hand_l'].translation-old['lowerarm_l'].translation
    for bone,axis in (('upperarm_l',U),('lowerarm_l',L)):
        new=Matrix.LocRotScale(old[bone].translation,Quaternion(axis.normalized(),math.radians(degrees))@old[bone].to_quaternion(),Vector((1,1,1)))
        for n in names:
            if under(n,'hand_l'):continue
            if under(n,bone) and (bone=='lowerarm_l' or not under(n,'lowerarm_l')):row[n]=new@old[bone].inverted()@old[n]
    ax=rest['lowerarm_l'].to_quaternion().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
    rel=row['lowerarm_l'].to_quaternion().inverted()@row['hand_l'].to_quaternion()@(rest['lowerarm_l'].to_quaternion().inverted()@rest['hand_l'].to_quaternion()).inverted()
    if rel.w<0:rel=-rel
    roll=2*math.atan2(Vector((rel.x,rel.y,rel.z)).dot(ax),rel.w)
    for j,w in ((1,1),(2,.5)):
        n=f'lowerarm_twist_{j:02d}_l';lr=rest['lowerarm_l'].inverted()@rest[n]
        row[n]=row['lowerarm_l']@Matrix.LocRotScale(lr.translation,Quaternion(ax,roll*w)@lr.to_quaternion(),lr.to_scale())
    return row
for roll in (-40,-20,0,20,40):
    row=rotate_arm(clone(original),roll);set_pose(row,t)
    target=row['lowerarm_l'].translation;cam.location=target+Vector((-.25,-.12,.15));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.27
    s.render.filepath=str(folder/(f'elbow_roll_{roll}.png'));bpy.ops.render.render(write_still=True)
for zs in ((45,0,10),(65,0,10),(45,25,25),(65,25,25)):
    row=clone(original)
    for j,z in enumerate(zs,1):
        n=f'thumb_{j:02d}_l';local=original[parents[n]].inverted()@original[n];basis=local_rest[n].inverted()@local;e=basis.to_euler();e.z=math.radians(z)
        row[n]=row[parents[n]]@local_rest[n]@Matrix.LocRotScale(basis.translation,e.to_quaternion(),basis.to_scale())
    set_pose(row,t);root=row['WPN_root']@rest['WPN_root'].inverted()
    target=row['hand_l'].translation+root.to_3x3()@Vector((.015,.025,.01));cam.location=target+root.to_3x3()@Vector((-.26,.06,.18));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.25
    s.render.filepath=str(folder/('thumb_'+'_'.join(str(x) for x in zs)+'.png'));bpy.ops.render.render(write_still=True)
