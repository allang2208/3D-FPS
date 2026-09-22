"""Rebuild carry/gestures on the Foundation rig from retained source motion.
Reference intent: low asymmetric shuffle; left staff raise; right forward bottle
release; knee sink followed by backward fall. Hit and turns are authored additions.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
FOUND=ROOT.parent/'WitchFoundation20260920';OLD=ROOT.parent/'WitchMeshy20260919'
OUT=ROOT/'Authoring';DEL=ROOT/'Delivery';FPS=30
def update():bpy.context.view_layer.update()
def world(r,n):return r.matrix_world@r.pose.bones[n].matrix
def put(r,n,m):r.pose.bones[n].matrix=r.matrix_world.inverted()@m;update()
def rotate(r,n,q):
    m=world(r,n);p=m.translation.copy();m=q.to_matrix().to_4x4()@m;m.translation=p;put(r,n,m)
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def frame(t):bpy.context.scene.frame_set(math.floor(t),subframe=t%1)
def cache(path):
    bpy.ops.wm.open_mainfile(filepath=str(path));r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    a=r.animation_data.action;start,end=a.frame_range;fps=bpy.context.scene.render.fps
    samples=[];matrices=[];roots=[]
    for i in range(round((end-start)/fps*FPS)+1):
        frame(start+i*fps/FPS)
        samples.append({b.name:b.matrix_basis.copy() for b in r.pose.bones})
        matrices.append({b.name:world(r,b.name).copy() for b in r.pose.bones})
        roots.append(r.matrix_world.copy())
    return samples,matrices,roots
foundation={n:cache(FOUND/f'Authoring/WitchFoundation_{n}.blend') for n in ('Idle','Walk')}
cloud={n:cache(OLD/f'Authoring/CloudGripV02/Witch_{n}_CloudGripV02.blend') for n in ('Idle','CastPoison','ThrowPoisonBottle','DeathBackward')}
base=foundation['Idle'][0][0];baseworld=foundation['Idle'][1][0];oldbase=cloud['Idle'][1][0]
forward=oldbase['headfront'].translation-oldbase['Head'].translation;forward.z=0
axis=Quaternion((0,0,1),math.atan2(-1,0)-math.atan2(forward.y,forward.x))
mapping={'pelvis':'Hips','spine_01':'Spine02','spine_03':'Spine01','spine_05':'Spine','neck_01':'neck','head':'Head'}
for s,side in (('l','Left'),('r','Right')):
    for target,source in [('clavicle','Shoulder'),('upperarm','Arm'),('lowerarm','ForeArm'),('hand','Hand'),('thigh','UpLeg'),('calf','Leg'),('foot','Foot'),('ball','ToeBase')]:mapping[target+'_'+s]=side+source

def solve(r,upper,lower,end,target,pole):
    a,b,c=[world(r,n) for n in (upper,lower,end)];p=a.translation.copy()
    l1=(b.translation-p).length;l2=(c.translation-b.translation).length
    d=target.translation-p;length=max(.01,min(d.length,l1+l2-.008));direction=d.normalized()
    knee=pole-p; knee-=direction*knee.dot(direction)
    if knee.length<.001:knee=Vector((0,-1,0))-direction*direction.y*-1
    knee.normalize();along=(l1*l1-l2*l2+length*length)/(2*length)
    bend=p+direction*along+knee*math.sqrt(max(0,l1*l1-along*along))
    rotate(r,upper,(b.translation-p).rotation_difference(bend-p))
    b=world(r,lower);c=world(r,end)
    rotate(r,lower,(c.translation-b.translation).rotation_difference(target.translation-b.translation))
    put(r,end,target)

manifest={}
source_manifest=json.loads((FOUND/'Authoring/motion_manifest.json').read_text())
for role in ('Idle','Walk','CastPoison','Hit','DeathBackward','TurnLeft','TurnRight'):
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'WitchRebuilt_Master.blend'))
    r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');r.animation_data_clear();r.data.pose_position='POSE'
    # Meshes stay in the source but are excluded from animation export.
    scene=bpy.context.scene;scene.render.fps=FPS
    count=len(foundation[role][0]) if role in foundation else 46 if role in cloud else 31
    scene.frame_start=1;scene.frame_end=count
    feet={s:[] for s in ('l','r')};opening=[]
    for i in range(count):
        t=i/FPS;scene.frame_set(i+1)
        r.matrix_world=foundation[role][2][i] if role in foundation else foundation['Idle'][2][0]
        for b in r.pose.bones:b.rotation_mode='QUATERNION';b.matrix_basis=(foundation[role][0][i] if role in foundation else base)[b.name]
        update();openhand=0
        if role in ('CastPoison','ThrowPoisonBottle','DeathBackward'):
            src=cloud[role][1][round(i*(len(cloud[role][1])-1)/(count-1))]
            strength=1 if role=='DeathBackward' else ramp(t,0,.18)*(1-ramp(t,1.15,1.5))
            for b in r.pose.bones:
                if b.name not in mapping:continue
                n=mapping[b.name]
                q=axis@(src[n].to_quaternion()@oldbase[n].to_quaternion().inverted())@axis.inverted()
                q=Quaternion().slerp(q,strength)
                # A quaternion-only matrix would replace the 0.01 world scale
                # with 1.0 and enlarge this bone chain when a gesture starts.
                m=Matrix.LocRotScale(world(r,b.name).translation,
                    q@baseworld[b.name].to_quaternion(),baseworld[b.name].to_scale())
                if b.name=='pelvis':m.translation=baseworld['pelvis'].translation+(axis@(src['Hips'].translation-oldbase['Hips'].translation))*strength
                put(r,b.name,m)
            if role!='DeathBackward':
                for s,side in (('l','Left'),('r','Right')):
                    # End effector trajectories come from the clean cloud gesture;
                    # target bone lengths and articulated carry hands remain intact.
                    for limb,chain in (('Hand',('upperarm','lowerarm','hand')),('Foot',('thigh','calf','foot'))):
                        upper,lower,end=[x+'_'+s for x in chain]
                        m=world(r,end).copy()
                        m.translation=baseworld[end].translation+axis@(src[side+limb].translation-oldbase[side+limb].translation)*strength
                        pole=baseworld[lower].translation+axis@(src[side+('ForeArm' if limb=='Hand' else 'Leg')].translation-oldbase[side+('ForeArm' if limb=='Hand' else 'Leg')].translation)*strength
                        solve(r,upper,lower,end,m,pole)
                if role=='ThrowPoisonBottle':
                    openhand=ramp(t,.70,.75)*(1-ramp(t,1.17,1.45))
                    for finger in ('index','middle','ring','pinky','thumb'):
                        for segment in ('01','02','03'):
                            b=r.pose.bones[finger+'_'+segment+'_r']
                            loc,q,scale=base[b.name].decompose()
                            b.matrix_basis=Matrix.LocRotScale(loc,q.slerp(Quaternion(),openhand*.95),scale)
        elif role=='Hit':
            recoil=ramp(t,0,.15)*(1-ramp(t,.6,1))
            for n,d in (('spine_02',-7),('spine_04',-9),('neck_01',5)):
                rotate(r,n,Quaternion((1,0,0),math.radians(d)*recoil))
            m=world(r,'pelvis');m.translation+=Vector((0,.025,-.022))*recoil;put(r,'pelvis',m)
            for s in ('l','r'):solve(r,'thigh_'+s,'calf_'+s,'foot_'+s,baseworld['foot_'+s].copy(),baseworld['calf_'+s].translation)
        elif role.startswith('Turn'):
            sign=1 if role=='TurnLeft' else -1
            for s,phase in (('l',0),('r',.5)):
                phase_t=(t-phase)%1
                lift=math.sin(math.pi*phase_t/.5)**2 if phase_t<.5 else 0
                m=baseworld['foot_'+s].copy();m.translation+=Vector((sign*.025,0,.045))*lift
                q=Quaternion((0,0,1),sign*math.radians(12)*lift)
                p=m.translation.copy();m=q.to_matrix().to_4x4()@m;m.translation=p
                solve(r,'thigh_'+s,'calf_'+s,'foot_'+s,m,baseworld['calf_'+s].translation)
        update()
        for s in ('l','r'):
            put(r,'ik_foot_'+s,world(r,'foot_'+s));put(r,'ik_hand_'+s,world(r,'hand_'+s))
            feet[s].append(world(r,'ball_'+s).translation.copy())
        for b in r.pose.bones:
            b.keyframe_insert('location',frame=i+1);b.keyframe_insert('rotation_quaternion',frame=i+1);b.keyframe_insert('scale',frame=i+1)
        r.keyframe_insert('location',frame=i+1);r.keyframe_insert('rotation_euler',frame=i+1);r.keyframe_insert('scale',frame=i+1)
        opening.append(openhand)
    r.animation_data.action.name='A_WitchRebuilt_'+role
    curves={}
    if role in foundation:curves=source_manifest[role]['curves']
    else:
        for s,positions in feet.items():
            curves['FootSpeed_'+s]=[(positions[min(count-1,i+1)]-positions[max(0,i-1)]).length*100*FPS/max(1,min(count-1,i+1)-max(0,i-1)) for i in range(count)]
            # Explicit swing intent uses the same source-speed domain as Foundation.
            # A slow lifted turning foot must still unlock at the 60 cm/s threshold.
            low=min(p.z for p in positions)
            curves['FootSpeed_'+s]=[max(speed,220 if p.z>low+.018 else 0) for speed,p in zip(curves['FootSpeed_'+s],positions)]
    curves['GripOpen_r']=opening
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'WitchRebuilt_{role}.blend'))
    bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
    file=DEL/f'A_WitchRebuilt_{role}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
        use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,
        bake_anim_step=1,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
    manifest[role]={'file':str(file),'fps':FPS,'frames':count,'duration':(count-1)/FPS,'loop':role in ('Idle','Walk','TurnLeft','TurnRight'),
                    'curves':curves,'source':'Foundation carry' if role in foundation else 'CloudGripV02 gesture adapted to complete Foundation anatomy' if role in cloud else 'Authored supplementary reaction/turn, no existing source clip',
                    'release':1.5*5/14 if role=='CastPoison' else .75 if role=='ThrowPoisonBottle' else None}
    (OUT/'motion_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('AUTHORED '+role,flush=True)

# Fit the actual bottle neck before authoring the release from the carry pose.
import sys
sys.path.insert(0,str(Path(__file__).parent))
import refine_bottle_grip
refine_bottle_grip.apply_carry(refine_bottle_grip.solve_grip())
import author_carry04
author_carry04.apply()
# The revised toss has its own anatomically constrained authoring pass. A full
# source rebuild must not restore the historical stretched-hand retarget.
exec(compile((Path(__file__).parent/'author_throw_polish.py').read_text(encoding='utf-8'),'author_throw_polish.py','exec'))
