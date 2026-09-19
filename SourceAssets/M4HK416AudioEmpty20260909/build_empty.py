"""M4 empty reload: retain mag contacts, add HK416-style support-hand bolt release.
Original rig/skin and all non-empty clips remain separate read-only inputs.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4ReloadFinger20260909/M4_Reload_FingerCurl.blend')
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];source=bpy.data.actions['M4_reload_FingerCurl']
def set_action(a):
    r.animation_data_create();r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def frame(t):
    s.frame_set(int(t),subframe=t-int(t));bpy.context.view_layer.update()
def smooth(v):
    v=max(0,min(1,v));return v*v*(3-2*v)
def blend(a,b,t):
    p,q,z=a.decompose();u,v,w=b.decompose();return Matrix.LocRotScale(p.lerp(u,t),q.slerp(v,t),z.lerp(w,t))

# Existing disconnected bolt carrier/bolt shells inside the receiver. No invented proxy.
body=bpy.data.objects['M4_M4 Body_Export'];parts=json.loads((OUT/'body_parts.json').read_text())
bolt_ids=parts[20]['vertices']+parts[21]['vertices']
assert len(bolt_ids)==612
body.vertex_groups['WPN_root'].remove(bolt_ids)
group=body.vertex_groups.get('WPN_bolt') or body.vertex_groups.new(name='WPN_bolt');group.add(bolt_ids,1,'REPLACE')

set_action(source);frame(114)
hand=r.pose.bones['hand_l'].matrix.copy();receiver=r.pose.bones['WPN_root'].matrix.copy()
# Anatomical palm frame, from this actual hand's metacarpal roots.
pinky=r.pose.bones['pinky_01_l'].head.copy();index=r.pose.bones['index_01_l'].head.copy();middle=r.pose.bones['middle_01_l'].head.copy()
y=(middle-hand.translation).normalized();x=(index-pinky).normalized();z=x.cross(y).normalized();x=y.cross(z).normalized()
anatomical=Matrix((x,y,z)).transposed()
desired_local=Matrix((Vector((0,1,0)),Vector((0,0,1)),Vector((1,0,0)))).transposed()
target_q=(receiver.to_3x3()@desired_local@anatomical.inverted()@hand.to_3x3()).to_quaternion()
# Contact with existing bolt catch on the receiver's left side.
button=Vector((.017,-.093,.052))
palm_center=(hand.translation+middle)*.5
palm_in_hand=hand.inverted()@palm_center
target_local_q=receiver.to_quaternion().inverted()@target_q
seat_local=receiver.inverted()@hand
samples=[];max_length_error=0;contacts=[]
for t in range(229):
    source_t=t if t<=114 else 114+(t-114)*6/66 if t<=180 else 120+(t-180)*68/48
    set_action(source);frame(source_t)
    base={b.name:b.matrix.copy() for b in r.pose.bones}
    root=base['WPN_root'];upper=base['upperarm_l'];fore=base['lowerarm_l'];wrist=base['hand_l']
    if 114<t<224:
        # Lift clear of the magazine, approach from outside, press, then withdraw.
        press=smooth((t-156)/18)*(1-smooth((t-180)/10))
        clearance=.042-.030*press
        contact=button+Vector((clearance,0,0))
        target=Matrix.LocRotScale(root@contact-(root.to_quaternion()@target_local_q)@palm_in_hand,
            root.to_quaternion()@target_local_q,Vector((1,1,1)))
        weight=smooth((t-120)/34)*(1-smooth((t-190)/34))
        goal=blend(wrist,target,weight)
        if t<154:
            goal.translation+=root.to_3x3()@Vector((.03*math.sin(math.pi*max(0,t-114)/40),0,-.018*math.sin(math.pi*max(0,t-114)/40)))
        shoulder=upper.translation;elbow=fore.translation;old_wrist=wrist.translation
        l1=(elbow-shoulder).length;l2=(old_wrist-elbow).length
        v=goal.translation-shoulder;d=min(v.length,l1+l2-1e-6);axis=v.normalized()
        goal.translation=shoulder+axis*d
        pole=elbow-shoulder;pole=(pole-axis*pole.dot(axis)).normalized()
        along=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(0,l1*l1-along*along))
        new_elbow=shoulder+axis*along+pole*height
        upper_q=(elbow-shoulder).rotation_difference(new_elbow-shoulder)@upper.to_quaternion()
        fore_q=(old_wrist-elbow).rotation_difference(goal.translation-new_elbow)@fore.to_quaternion()
        r.pose.bones['upperarm_l'].matrix=Matrix.LocRotScale(shoulder,upper_q,upper.to_scale());bpy.context.view_layer.update()
        r.pose.bones['lowerarm_l'].matrix=Matrix.LocRotScale(new_elbow,fore_q,fore.to_scale());bpy.context.view_layer.update()
        r.pose.bones['hand_l'].matrix=goal;bpy.context.view_layer.update()
        max_length_error=max(max_length_error,abs((new_elbow-shoulder).length-l1),abs((goal.translation-new_elbow).length-l2))
        if 174<=t<=180:contacts.append((goal@palm_in_hand-root@button).length*100)
    # The bolt is held open until the support hand depresses the release, then closes.
    open_amount=1-smooth((t-180)/4)
    bolt=r.pose.bones['WPN_bolt'];m=base['WPN_bolt'].copy();m.translation+=root.to_3x3()@Vector((0,.035*open_amount,0));bolt.matrix=m
    bpy.context.view_layer.update()
    samples.append({b.name:b.matrix_basis.copy() for b in r.pose.bones})

action=bpy.data.actions.new('M4_reload_empty_BoltRelease');action.use_fake_user=True
r.animation_data.action=action
previous={}
for t,poses in enumerate(samples):
    for name,m in poses.items():
        b=r.pose.bones[name];p,q,z=m.decompose()
        if name in previous and previous[name].dot(q)<0:q.negate()
        previous[name]=q.copy();b.rotation_mode='QUATERNION';b.location=p;b.rotation_quaternion=q;b.scale=z
        for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=t)
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for k in curve.keyframe_points:k.interpolation='LINEAR'
s.render.fps=60;s.frame_start=0;s.frame_end=228
bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(OUT/'A_M4_ReloadEmpty_BoltRelease.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
    add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
r.animation_data_clear()
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
for o in r.children:
    if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_M4_Infima_BoltReceiver.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,path_mode='COPY',embed_textures=True,mesh_smooth_type='FACE')
set_action(action);frame(180)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M4_EmptyReload_BoltRelease.blend'))
assert max_length_error<.0001,max_length_error
report={'frames':229,'fps':60,'source_duration':3.8,'runtime_duration':3.466667,'cue_frames':[30,90,114,180],
    'bolt_closed_frame':184,'bolt_travel_cm':3.5,'bolt_vertices':len(bolt_ids),'bone_count':len(r.data.bones),
    'maximum_arm_length_error_cm':max_length_error*100,'palm_button_distance_cm_at_press':contacts,
    'reference':'Godot HK416 reload_empty: seated magazine, lift support hand, press bolt catch, return to foreend',
    'original_hand_pack':'No separate empty reload or charge action; plain Reload was duplicated before this change.'}
(OUT/'empty_build.json').write_text(json.dumps(report,indent=2));print('M4_EMPTY_BUILD_PASS',report)
