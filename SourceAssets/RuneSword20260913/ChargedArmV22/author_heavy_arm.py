"""Apply the user-accepted V21 elbow/shoulder transport to charged attacks.

HeavyCharge and HeavyRelease share one corrected held pose. Slash1 uses the
same left-arm treatment because releasing an incomplete charge resumes its
windup directly. Hand grips, elbow/wrist centers, sword and clocks are retained.
"""
import bpy, json, sys, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

P=Path(__file__).parent
SOURCE=P.parent/'FistBraceGuardV21/AzureRunesword_Manny_Editable.blend'
OUT=P/'Export';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(P.parent/'CompactRecoveryV8'))
import rhythm_clock
FPS=480;ONE=Vector((1,1,1))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig']
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local={n:rest[parent[n]].inverted()@m if parent[n] else m for n,m in rest.items()}
RU=(rest['lowerarm_l'].translation-rest['upperarm_l'].translation).normalized()
changed={'clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l'}
edit_bones=changed|{n for n in parent if parent[n] in changed}

def ease(t):
    t=max(0.,min(1.,t));return t*t*t*(t*(t*6.-15.)+10.)

def weight_at(clip,t):
    if clip=='HeavyCharge':return ease(t/.12)
    # The rapid swing crosses a near-antiparallel transport axis at ~45 ms.
    # Return to its authored frame before that crossing, retaining the shared
    # charged pose at release zero instead of adding an axial spin mid-strike.
    if clip=='HeavyRelease':return 1.-ease(t/.025)
    # Incomplete-charge dispatch maps .65 charge seconds to .17 source seconds.
    # Match that activation curve on the existing Slash1 windup clock.
    charge_time=rhythm_clock.source_time(t)*.65/.17
    return ease(charge_time/.12)*(1.-ease((t-.65)/.20))

def transported(pose):
    upper=pose['upperarm_l'];fore=pose['lowerarm_l']
    axis=(fore.translation-upper.translation).normalized()
    fore_deform=fore.to_quaternion()@rest['lowerarm_l'].to_quaternion().inverted()
    aligned=fore_deform@RU
    return axis,(aligned.rotation_difference(axis)@fore_deform)@rest['upperarm_l'].to_quaternion()

def repair(pose,weight,initial_roll=None):
    if weight<=0:return pose
    upper=pose['upperarm_l'];fore=pose['lowerarm_l']
    current,goal=transported(pose)
    # Decay the idle's fixed residual roll on the moving segment axis. Blending
    # against the old per-frame upper orientation would retain its 40 ms flip.
    corrected=(Quaternion(current,initial_roll*(1.-weight))@goal if initial_roll is not None
               else upper.to_quaternion().slerp(goal,weight))
    pose['upperarm_l']=Matrix.LocRotScale(upper.translation,corrected,ONE)
    delta=pose['upperarm_l']@upper.inverted()
    # Carry all upper-segment skin weights, including the shoulder's support,
    # instead of pushing the differential roll into the sleeve cap.
    for name in ('clavicle_l','upperarm_twist_01_l','upperarm_twist_02_l'):
        pose[name]=delta@pose[name]
    return pose

records=[];s.render.fps=FPS;s.render.fps_base=1.
for clip in ('HeavyCharge','HeavyRelease','Slash1'):
    name='A_RuneSword_'+clip;source=bpy.data.actions[name]
    r.animation_data.action=source;r.animation_data.action_slot=source.slots[0]
    start,end=map(int,source.frame_range);frames=[];initial_roll=None
    for f in range(start,end+1):
        s.frame_set(f);bpy.context.view_layer.update()
        pose={b.name:b.matrix.copy() for b in r.pose.bones};t=f/FPS
        if f==start:
            axis,goal=transported(pose)
            offset=pose['upperarm_l'].to_quaternion()@goal.inverted()
            initial_roll=2*math.atan2(Vector((offset.x,offset.y,offset.z)).dot(axis),offset.w)
            initial_roll=(initial_roll+math.pi)%(2*math.pi)-math.pi
        entry=(clip=='HeavyCharge' or (clip=='Slash1' and t<=.65))
        frames.append(repair(pose,weight_at(clip,t),initial_roll if entry else None))
    source.name='REF_V21_'+name;source.use_fake_user=True
    action=source.copy();action.name=name;action.use_fake_user=True
    def edited(curve):
        return any(curve.data_path.startswith('pose.bones["'+n+'"].') for n in edit_bones)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in list(bag.fcurves):
                    if edited(curve):bag.fcurves.remove(curve)
    r.animation_data.action=action;s.frame_start=start;s.frame_end=end;previous={}
    r.animation_data.action_slot=action.slots[0]
    for f,pose in enumerate(frames,start):
        s.frame_set(f)
        for b in r.pose.bones:
            if b.name not in edit_bones:continue
            m=pose[parent[b.name]].inverted()@pose[b.name] if parent[b.name] else pose[b.name]
            loc,q,scale=(local[b.name].inverted()@m).decompose()
            if b.name in previous and q.dot(previous[b.name])<0:q.negate()
            previous[b.name]=q.copy()
            b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=scale
            for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=f,group=b.name)
    r.animation_data.action_slot=action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if edited(curve):
                        for key in curve.keyframe_points:key.interpolation='LINEAR'
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True)
    bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,
        object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    records.append({'clip':name,'frames':[start,end],'seconds':(end-start)/FPS})
    print('V22_LEFT_ARM_EXPORTED '+name,flush=True)
r.animation_data.action=bpy.data.actions['A_RuneSword_HeavyCharge']
r.animation_data.action_slot=r.animation_data.action.slots[0]
s.frame_start=0;s.frame_end=960;s.frame_set(960)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({'revision':'ChargedArmV22','source':str(SOURCE),'fps':FPS,
    'clips':records,'changed':'Left clavicle, upper-arm frame and two upper-arm skin helpers',
    'preserved':'V21 guard; source hand grips, sword and right arm; upper-arm/elbow/wrist centers; timing',
    'method':'V21 shortest-swing upper-arm orientation transported from the forearm deformation',
    'transitions':'120 ms decay of initial idle roll; 25 ms release handoff; Slash1 correction fades during .65-.85 s load hold',
    'track_scope':sorted(edit_bones),
    'transport_scope':'Full correction in charge; no transported frame through the near-antiparallel fast-swing axis'},indent=2),encoding='utf-8')
print('RUNESWORD_V22_AUTHORED',flush=True)
