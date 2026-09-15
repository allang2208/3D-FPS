"""Repair the left elbow's differential roll in the photo-directed V20 guard.

The shoulder/upper-arm frame and its two skin helpers change. The forearm, fist,
sword, right arm, upper-arm/elbow/wrist centers and contact tracks stay V20.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector

P=Path(__file__).parent
SOURCE=P.parent/'FistBraceGuardV20/AzureRunesword_Manny_Editable.blend'
OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=480
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig']
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local={n:rest[parent[n]].inverted()@m if parent[n] else m for n,m in rest.items()}
RU=(rest['lowerarm_l'].translation-rest['upperarm_l'].translation).normalized()
RF=(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
ONE=Vector((1,1,1))

def ease(t):
    t=max(0.,min(1.,t));return t*t*t*(t*(t*6.-15.)+10.)

def repair(pose,weight):
    if weight<=0:return pose
    upper=pose['upperarm_l'];fore=pose['lowerarm_l']
    current=(fore.translation-upper.translation).normalized()
    fore_deform=fore.to_quaternion()@rest['lowerarm_l'].to_quaternion().inverted()
    # Transport the forearm's deformation to the upper segment by a shortest
    # swing. The V20 plane-based upper frame injected >110 degrees of axial
    # differential into the elbow while each segment individually looked valid.
    aligned=fore_deform@RU
    upper_deform=aligned.rotation_difference(current)@fore_deform
    goal=upper_deform@rest['upperarm_l'].to_quaternion()
    corrected=upper.to_quaternion().slerp(goal,weight)
    pose['upperarm_l']=Matrix.LocRotScale(upper.translation,corrected,ONE)
    delta=pose['upperarm_l']@upper.inverted()
    # The sleeve cap also carries clavicle weights. Carry its support through
    # the same shoulder rotation instead of moving the elbow twist upstream
    # into a collapsed shoulder cap. The upper-arm pivot itself stays fixed.
    pose['clavicle_l']=delta@pose['clavicle_l']
    for name in ('upperarm_twist_01_l','upperarm_twist_02_l'):
        pose[name]=delta@pose[name]
    return pose

records=[]
s.render.fps=FPS;s.render.fps_base=1.
for clip in ('Guard','GuardHit','GuardBreak'):
    name='A_RuneSword_'+clip
    source=bpy.data.actions[name]
    r.animation_data.action=source;r.animation_data.action_slot=source.slots[0]
    start,end=map(int,source.frame_range)
    frames=[]
    for f in range(start,end+1):
        s.frame_set(f);bpy.context.view_layer.update()
        pose={b.name:b.matrix.copy() for b in r.pose.bones}
        t=f/FPS
        if clip=='Guard':weight=ease(t/.065)
        elif clip=='GuardHit':weight=1.
        else:weight=1.-ease((t-.18)/.22)
        frames.append(repair(pose,weight))
    source.name='REF_V20_'+name;source.use_fake_user=True
    action=bpy.data.actions.new(name);action.use_fake_user=True
    r.animation_data.action=action;s.frame_start=start;s.frame_end=end
    previous={}
    for f,pose in enumerate(frames,start):
        s.frame_set(f)
        for b in r.pose.bones:
            m=pose[parent[b.name]].inverted()@pose[b.name] if parent[b.name] else pose[b.name]
            loc,q,scale=(local[b.name].inverted()@m).decompose()
            if b.name in previous and q.dot(previous[b.name])<0:q.negate()
            previous[b.name]=q.copy()
            b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=scale
            for channel in ('location','rotation_quaternion','scale'):
                b.keyframe_insert(channel,frame=f,group=b.name)
    r.animation_data.action_slot=action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True)
    bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,
        object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    records.append({'clip':name,'frames':[start,end],'seconds':(end-start)/FPS})
    print('V21_LEFT_ELBOW_EXPORTED '+name,flush=True)
r.animation_data.action=bpy.data.actions['A_RuneSword_Guard']
r.animation_data.action_slot=r.animation_data.action.slots[0]
s.frame_start=0;s.frame_end=96;s.frame_set(96)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({'revision':'FistBraceGuardV21','source':str(SOURCE),
    'fps':FPS,'clips':records,'changed':'Left clavicle/upper-arm frame and its two complete-segment helpers',
    'preserved':'V20 upper-arm/elbow/wrist centers, forearm, fist, sword, right arm, timing and contacts',
    'method':'Shortest-swing upper-arm frame transported from the forearm deformation; smooth entry/regrip',
    'acceptance':'Source and imported animation inspection follows; gameplay not covered'},indent=2),encoding='utf-8')
print('RUNESWORD_V21_AUTHORED',flush=True)
