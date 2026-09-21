"""Re-author spell support from clean cloud motion; retain V06 body and PBR.

Only the two spell clips change. The original sources and candidate body remain.
No renders or gameplay tests are run by this authoring script.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchMeshy20260919')
sys.path.insert(0,str(ROOT))
import layered_v04 as common
OUT=ROOT/'Authoring/SpellSupportV07';OUT.mkdir(parents=True,exist_ok=True)
DEL=ROOT/'Delivery/SpellSupportV07';DEL.mkdir(parents=True,exist_ok=True)
FPS=60

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def world(r,n):return r.matrix_world@r.pose.bones[n].matrix
def put(r,n,m):
    r.pose.bones[n].matrix=r.matrix_world.inverted()@m;common.update()
def mix(a,b,t):
    al,aq,asc=a.decompose();bl,bq,bsc=b.decompose()
    return Matrix.LocRotScale(al.lerp(bl,t),aq.slerp(bq,t),asc.lerp(bsc,t))
def solve(r,side,target):
    upper,lower,end=[side+n for n in ('UpLeg','Leg','Foot')]
    a,b,c=[world(r,n) for n in (upper,lower,end)]
    hip,knee,ankle=[m.translation.copy() for m in (a,b,c)]
    l1=(knee-hip).length;l2=(ankle-knee).length
    target=target.copy()
    d=target.translation-hip;distance=min(d.length,l1+l2-.008);axis=d.normalized()
    target.translation=hip+axis*distance
    # Preserve the authored knee plane, never swap to the back-facing IK solution.
    pole=knee-hip;pole-=axis*pole.dot(axis)
    if pole.length<.001:pole=Vector((0,-1,0))-axis*axis.dot(Vector((0,-1,0)))
    pole.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    new_knee=hip+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    q=(knee-hip).rotation_difference(new_knee-hip)
    m=q.to_matrix().to_4x4()@a;m.translation=hip;put(r,upper,m)
    b=world(r,lower);c=world(r,end)
    q=(c.translation-b.translation).rotation_difference(target.translation-b.translation)
    m=q.to_matrix().to_4x4()@b;m.translation=b.translation;put(r,lower,m)
    put(r,end,target)

clouds={n:common.cache_cloud(n) for n in ('Idle','CastPoison','ThrowPoisonBottle')}
report={'source':'CloudGripV02 clean Meshy motion, V06 original body retained',
        'runtime_tested':False,'clips':{},'body_mesh_changed':False}
for role in ('CastPoison','ThrowPoisonBottle'):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/CleanRobeV06/Witch_CleanRobeV06.blend'))
    r=common.rig();common.neutral(r);rest=common.rest(r)
    scene=bpy.context.scene;scene.render.fps=FPS;scene.frame_start=0;scene.frame_end=90
    idle=clouds['Idle'][0][0]
    for b in r.pose.bones:b.rotation_mode='QUATERNION';b.matrix_basis=idle[b.name]
    common.update()
    base_hip=world(r,'Hips')
    targets={};toe_offsets={}
    feet=bpy.data.objects['Witch_OriginalFeet']
    # Keep the clean idle's foot/toe orientation and solve separate soles, independent of the hem.
    for side,sign in (('Left',1),('Right',-1)):
        foot=side+'Foot';toe=side+'ToeBase'
        m=world(r,foot).copy()
        m.translation=Vector((sign*.16,-.175 if side=='Left' else -.095,.095))
        targets[side]=m
        toe_offsets[side]=world(r,foot).inverted()@world(r,toe).translation
    for side in targets:solve(r,side,targets[side])
    deps=bpy.context.evaluated_depsgraph_get();ev=feet.evaluated_get(deps);me=ev.to_mesh()
    lows={side:min((ev.matrix_world@v.co).z for v in me.vertices
                  if (ev.matrix_world@v.co).x*sign>0) for side,sign in (('Left',1),('Right',-1))}
    ev.to_mesh_clear()
    for side in targets:targets[side].translation.z-=lows[side]
    # Retain normal knee flexion without moving the root to whichever foot is lowest.
    base_hip.translation.z-=max(lows.values())
    source=clouds[role][0];poses=[]
    curves={'SupportLeft':[],'SupportRight':[],'SupportHeelRight':[]}
    release=.535714285714 if role=='CastPoison' else .75
    for i in range(91):
        t=i/FPS;scene.frame_set(i)
        # Endpoints return to the carry pose; release remains on the original clock.
        strength=ramp(t,0,.25)*(1-ramp(t,1.14,1.5))
        for b in r.pose.bones:b.matrix_basis=mix(idle[b.name],source[i][b.name],strength)
        common.update()
        hip=world(r,'Hips')
        lean=ramp(t,.10,.37)*(1-ramp(t,.86,1.3))
        transfer=ramp(t,.36,.75)*(1-ramp(t,1.05,1.44)) if role=='ThrowPoisonBottle' else 0
        # Loading the right/rear leg precedes transferring weight to the left/front leg.
        offset=Vector((-.012*lean+.038*transfer,-.012*lean-.026*transfer,-.012*lean))
        hip.translation=base_hip.translation+offset
        put(r,'Hips',hip)
        # Lower the pelvis if either planted leg would otherwise need to stretch.
        drop=0.0
        for side in ('Left','Right'):
            up,knee,foot=[world(r,side+n).translation for n in ('UpLeg','Leg','Foot')]
            reach=(knee-up).length+(foot-knee).length-.012
            delta=up-targets[side].translation
            max_height=math.sqrt(max(.001,reach*reach-delta.x*delta.x-delta.y*delta.y))
            drop=max(drop,delta.z-max_height)
        if drop>0:
            hip.translation.z-=drop;put(r,'Hips',hip)
        for side in ('Left','Right'):
            target=targets[side].copy()
            # Throw follow-through pivots over the right toe; it never translates the support toe.
            heel=math.radians(4.0)*ramp(t,.54,.79)*(1-ramp(t,.97,1.24)) if role=='ThrowPoisonBottle' and side=='Right' else 0
            if heel:
                pivot=target@toe_offsets[side]
                q=Quaternion(Vector((1,0,0)),heel)
                target=q.to_matrix().to_4x4()@target
                target.translation=pivot-q@(pivot-targets[side].translation)
            solve(r,side,target)
        curves['SupportLeft'].append(1.0)
        curves['SupportRight'].append(1.0)
        curves['SupportHeelRight'].append(math.degrees(heel) if role=='ThrowPoisonBottle' else 0)
        poses.append({b.name:b.matrix_basis.copy() for b in r.pose.bones})
    r.animation_data_clear();r.animation_data_create()
    action=bpy.data.actions.new('A_Witch_'+role+'_SpellSupportV07');r.animation_data.action=action
    last={}
    for i,pose in enumerate(poses):
        for b in r.pose.bones:
            b.matrix_basis=pose[b.name]
            if b.name in last and b.rotation_quaternion.dot(last[b.name])<0:b.rotation_quaternion.negate()
            last[b.name]=b.rotation_quaternion.copy()
            for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=i,group=b.name)
    for name,time in [('settled',.25),('release',release),('recover',1.14)]:scene.timeline_markers.new(name,frame=round(time*FPS))
    scene['support_revision']='V07 independent sole anchors, bent knees, right-to-left throw transfer'
    scene.frame_set(0);common.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'Witch_{role}_SpellSupportV07.blend'))
    common.export(DEL/f'A_Witch_{role}_SpellSupportV07.fbx',[r],True)
    report['clips'][role]={'duration':1.5,'fps':FPS,'keys':91,'release':release,'loop':False,
        'curves':curves,'ankle_height_cm':{s:targets[s].translation.z*100 for s in targets},
        'toe_bone_local_units':{s:list(toe_offsets[s]) for s in targets},
        'file':str(DEL/f'A_Witch_{role}_SpellSupportV07.fbx')}
    print('AUTHORED SpellSupportV07 '+role,flush=True)
(OUT/'motion_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
