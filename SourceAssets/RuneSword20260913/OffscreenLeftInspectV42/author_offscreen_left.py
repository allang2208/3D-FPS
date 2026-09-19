"""Remove the mid-inspect left-hand cameo using the V41 withdrawn pose.

Keep the original right-side action curves and the initial release/final regrip.
Use the complete left clavicle subtree, including twist helpers and fingers.
"""
import bpy,json
from pathlib import Path
from mathutils import Matrix

P=Path(__file__).parent
SOURCE=P.parent/'AnchoredArmFlowV41/AzureRunesword_AnchoredArmFlowV41.blend'
FPS=120;COUNT=349;HOLD_TIME=1.2
ENTER=(.85,1.2);LEAVE=(2.35,2.55)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig']
original=bpy.data.actions['A_RuneSword_Inspect']
r.animation_data.action=original;r.animation_data.action_slot=original.slots[0]
left_root=r.data.bones['clavicle_l']
left={left_root.name}|{b.name for b in left_root.children_recursive}
ordered=[b.name for b in r.data.bones if b.name in left]
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
poses=[];source_quaternions=[]
for frame in range(COUNT):
    s.frame_set(frame)
    poses.append({b.name:b.matrix.copy() for b in r.pose.bones})
    source_quaternions.append({n:r.pose.bones[n].rotation_quaternion.copy() for n in left})
held=poses[round(HOLD_TIME*FPS)]

def smooth(value):
    x=max(0.,min(1.,value));return x*x*x*(x*(x*6.-15.)+10.)

def blend(a,b,w):
    al,aq,asc=a.decompose();bl,bq,bsc=b.decompose()
    if aq.dot(bq)<0:bq.negate()
    return Matrix.LocRotScale(al.lerp(bl,w),aq.slerp(bq,w),asc.lerp(bsc,w))

original.name='RETAINED_V41_A_RuneSword_Inspect';original.use_fake_user=True
action=original.copy();action.name='A_RuneSword_Inspect';action.use_fake_user=True
r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
previous={}
for frame,source in enumerate(poses):
    t=frame/FPS
    weight=smooth((t-ENTER[0])/(ENTER[1]-ENTER[0]))*(1.-smooth((t-LEAVE[0])/(LEAVE[1]-LEAVE[0])))
    target={n:m.copy() for n,m in source.items()}
    for name in ordered:
        parent=parents[name]
        if name==left_root.name:
            target[name]=blend(source[name],held[name],weight) if weight>0 else source[name]
        elif weight>0:
            local=source[parent].inverted()@source[name]
            held_local=held[parent].inverted()@held[name]
            target[name]=target[parent]@blend(local,held_local,weight)
        bone=r.pose.bones[name]
        local=target[parent].inverted()@target[name] if parent else target[name]
        loc,q,scale=(local_rest[name].inverted()@local).decompose()
        if weight<=0:q=source_quaternions[frame][name].copy()
        if name in previous and q.dot(previous[name])<0:q.negate()
        previous[name]=q.copy()
        # Match the quaternion hemisphere across both interval boundaries.
        # A sign-only edit outside the interval retains the same pose and
        # prevents an antipodal interpolation when returning to copied keys.
        if weight<=0:
            if q.dot(source_quaternions[frame][name])<0:
                bone.rotation_quaternion=q
                bone.keyframe_insert('rotation_quaternion',frame=frame,group=name)
            continue
        bone.rotation_mode='QUATERNION';bone.location=loc;bone.rotation_quaternion=q;bone.scale=scale
        for channel in ('location','rotation_quaternion','scale'):
            bone.keyframe_insert(channel,frame=frame,group=name)

for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                if any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in left):
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
s.render.fps=FPS;s.render.fps_base=1.;s.frame_start=0;s.frame_end=COUNT-1;s.frame_set(0)
bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
export=P/'Export';export.mkdir(exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(export/'A_RuneSword_Inspect.fbx'),use_selection=True,object_types={'ARMATURE'},
    axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
r['OffscreenLeftInspectV42']='V41 withdrawn left-arm pose replaces the mid-inspect left-hand cameo'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_OffscreenLeftInspectV42.blend'))
(P/'authoring.json').write_text(json.dumps({'revision':'OffscreenLeftInspectV42','source':str(SOURCE),
    'fps':FPS,'duration':2.9,'left_pose_source_time':HOLD_TIME,'enter_hidden_hold':ENTER,'leave_hidden_hold':LEAVE,
    'changed_bones':ordered,'right_and_weapon_curves':'Copied without editing',
    'initial_release_final_regrip':'V41 copied outside the edit interval',
    'testing':'No new playback, render or automated audit requested or performed'},indent=2),encoding='utf-8')
print('OFFSCREEN_LEFT_V42_AUTHORING_COMPLETE',flush=True)
