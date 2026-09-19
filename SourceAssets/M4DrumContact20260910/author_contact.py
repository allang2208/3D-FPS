import bpy, math, json
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent
SOURCE=O.parent/'M4DrumGrip20260910/Revision7/M4_DrumMatch_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
r=bpy.data.objects['SK_M4_Infima']; s=bpy.context.scene
names=[b.name for b in r.pose.bones]
parents={b.name:b.parent.name if b.parent else None for b in r.pose.bones}
rest={b.name:b.bone.matrix_local.copy() for b in r.pose.bones}
local_rest={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}

def smooth(t):
    t=max(0.,min(1.,t)); return t*t*t*(t*(t*6-15)+10)

def sample(a,f):
    r.animation_data.action=a; r.animation_data.action_slot=a.slots[0]
    s.frame_set(int(f),subframe=f%1); bpy.context.view_layer.update()
    return {b.name:b.matrix.copy() for b in r.pose.bones}

def turn_at(pivot,a,b):
    return Matrix.Translation(pivot)@a.rotation_difference(b).to_matrix().to_4x4()@Matrix.Translation(-pivot)

def correct(p,seat,f,start,aligned,end):
    if f<=start or f>=end:return p,0.,0.
    weight=smooth((f-start)/(aligned-start))
    root=p['WPN_root']; old=p['WPN_SOCKET_Magazine']; rel=root.inverted()@old
    loc,q,scale=rel.decompose(); target=loc.copy()
    # Finish alignment before the feed neck touches the well. Preserve axial
    # insertion depth and the original seat timestamp; remove lateral wobble.
    target.x=seat.translation.x; target.y=seat.translation.y
    mag=root@Matrix.LocRotScale(loc.lerp(target,weight),q.slerp(seat.to_quaternion(),weight),scale)
    delta=mag@old.inverted(); out={n:m.copy() for n,m in p.items()}
    out['WPN_SOCKET_Magazine']=mag
    # Fixed shoulder, original segment lengths, original elbow side. The hand
    # follows the drum rigidly while two-bone IK accommodates the small change.
    shoulder=p['upperarm_l'].translation; elbow=p['lowerarm_l'].translation; wrist=p['hand_l'].translation
    goal=(delta@p['hand_l']).translation
    upper=(elbow-shoulder).length; lower=(wrist-elbow).length
    direction=(goal-shoulder).normalized(); distance=(goal-shoulder).length
    assert abs(upper-lower)+1e-6<distance<upper+lower-1e-6, 'Unreachable wrist'
    along=(upper*upper-lower*lower+distance*distance)/(2*distance)
    pole=elbow-shoulder; pole=(pole-direction*pole.dot(direction)).normalized()
    new_elbow=shoulder+direction*along+pole*math.sqrt(max(0.,upper*upper-along*along))
    up_delta=turn_at(shoulder,elbow-shoulder,new_elbow-shoulder)
    low_rot=(wrist-elbow).rotation_difference(goal-new_elbow).to_matrix().to_4x4()
    low_delta=Matrix.Translation(new_elbow)@low_rot@Matrix.Translation(-elbow)
    for n in names:
        if n.startswith('upperarm') and n.endswith('_l'):out[n]=up_delta@p[n]
        elif n.startswith('lowerarm') and n.endswith('_l'):out[n]=low_delta@p[n]
        elif n.endswith('_l') and n.startswith(('hand','thumb','index','middle','ring','pinky')):out[n]=delta@p[n]
    return out,(goal-wrist).length*100,(new_elbow-elbow).length*100

reports={}
for clip,end,start,aligned,seat_frame in [('reload',126,69,75,95),('reload_empty',148,47,53,80)]:
    original=bpy.data.actions['A_M4_DrumMatch_'+clip]
    seated=sample(original,seat_frame); seat=seated['WPN_root'].inverted()@seated['WPN_SOCKET_Magazine']
    poses=[]; max_wrist=max_elbow=max_grip=max_length=0.
    for k in range(end*4+1):
        f=k/4; p=sample(original,f); out,w,e=correct(p,seat,f,start,aligned,seat_frame)
        max_wrist=max(max_wrist,w);max_elbow=max(max_elbow,e)
        old_grip=p['WPN_SOCKET_Magazine'].inverted()@p['hand_l']
        new_grip=out['WPN_SOCKET_Magazine'].inverted()@out['hand_l']
        max_grip=max(max_grip,(old_grip.translation-new_grip.translation).length*100)
        for a,b in [('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')]:
            max_length=max(max_length,abs((out[b].translation-out[a].translation).length-(p[b].translation-p[a].translation).length)*100)
        poses.append(out)
    a=bpy.data.actions.new('A_M4_DrumContact_'+clip);a.use_fake_user=True;r.animation_data.action=a; previous={}
    for k,p in enumerate(poses):
        for n in names:
            local=local_rest[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n])
            loc,q,scale=local.decompose()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=scale
            for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=k/4)
    for layer in a.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    reports[clip]={'start_frame':start,'aligned_frame':aligned,'seat_frame':seat_frame,'end_frame':end,'source_seconds':end/60,'max_wrist_change_cm':max_wrist,'max_elbow_change_cm':max_elbow,'max_grip_translation_error_cm':max_grip,'max_arm_length_error_cm':max_length}
    assert max_grip<.001 and max_length<.001
    s.render.fps=60;s.frame_start=0;s.frame_end=end
    bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(O/(a.name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.25,bake_anim_simplify_factor=0)

bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_DrumContact_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(reports,indent=2))
print('DRUM_CONTACT_AUTHORED',json.dumps(reports))
