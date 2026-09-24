"""Retarget the actual archived Godot Gallop directly to Meshy canine V2.

Absolute anatomical directions and explicit canine joint planes replace
rest-rotation deltas / unconstrained hind-leg FABRIK. Mesh and weights stay put.
"""
import json,math,statistics,hashlib
from pathlib import Path
import bpy
from mathutils import Matrix,Vector,Quaternion

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/InfectedDogMeshy20260924'
OUT=BASE/'GodotRunFitV2';OUT.mkdir(exist_ok=True)
SOURCE=OUT/'Source/godot_gallop_samples.json'
SRC=json.loads(SOURCE.read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(BASE/'CompletionV2/InfectedDog_MeshyV2.blend'))
scene=bpy.context.scene;scene.render.fps=60;scene.render.fps_base=1.
scene.frame_start=1;scene.frame_end=35
rig=next(o for o in scene.objects if o.type=='ARMATURE');rig.name='Armature'
rig.animation_data_clear();rig.animation_data_create()
rig.animation_data.action=bpy.data.actions.new('A_InfectedDogMeshy_GodotRunFitV2')
rig.animation_data.action.use_fake_user=True
NAMES=[b.name for b in rig.data.bones]
PARENTS={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
REST={b.name:b.matrix_local.copy() for b in rig.data.bones}
LOCAL={n:REST[PARENTS[n]].inverted()@REST[n] if PARENTS[n] else REST[n].copy() for n in NAMES}
def p(row,name):return Vector(row[name]['head'])
def direction(row,a,b=None):return (p(row,b) if b else Vector(row[a]['tail']))-p(row,a)
def hip_center(row):return (p(row,'BackLeg.L')+p(row,'BackLeg.R'))*.5
source_hips=hip_center(SRC['rest'])
scale=REST['pelvis'].translation.z/source_hips.z
def fk(local):
    w={}
    for n in NAMES:w[n]=w[PARENTS[n]]@local[n] if PARENTS[n] else local[n].copy()
    return w
def setq(local,n,q):
    w=fk(local);parent=PARENTS[n]
    local[n]=Matrix.LocRotScale(local[n].translation,w[parent].to_quaternion().inverted()@q if parent else q,Vector((1,1,1)))
def orient(local,n,desired,child=None):
    # Keep the fitted bone roll; use anatomical vectors, not exporter bone axes.
    ref=(REST[child].translation-REST[n].translation) if child else (rig.data.bones[n].tail_local-rig.data.bones[n].head_local)
    q=ref.normalized().rotation_difference(desired.normalized())@REST[n].to_quaternion()
    setq(local,n,q)
def two_bone(local,chain,goal,bend_sign):
    w=fk(local);a,b,c=[w[n].translation.copy() for n in chain]
    l1,l2=(b-a).length,(c-b).length
    d=goal-a;r=max(abs(l1-l2)+1e-5,min(d.length,(l1+l2)*.998))
    axis=d.normalized();end=a+axis*r
    pole=Vector((0,bend_sign,0));pole-=axis*pole.dot(axis);pole.normalize()
    along=(l1*l1-l2*l2+r*r)/(2*r)
    middle=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    orient(local,chain[0],middle-a,chain[1])
    orient(local,chain[1],end-middle,chain[2])
    return (end-goal).length

def fit_hock(local,side,ankle_goal,preferred):
    """Keep the paw goal while fitting a shorter target shin; no free FABRIK."""
    w=fk(local)
    hip=w['thigh'+side].translation
    knee=w['calf'+side].translation
    hock=w['hock'+side].translation
    ankle=w['hindfoot'+side].translation
    a,b,c=(knee-hip).length,(hock-knee).length,(ankle-hock).length
    axis=ankle_goal-hip;distance=axis.length;axis.normalize()
    # Keep a small knee bend even at maximum extension.
    proximal=math.sqrt(a*a+b*b+2*a*b*math.cos(math.radians(12)))
    fitted=ankle_goal.copy()
    if distance>proximal+c-.0001:
        distance=proximal+c-.0001;fitted=hip+axis*distance
    desired=fitted-preferred*c
    reach=(desired-hip).length
    if reach>proximal:
        along=(proximal*proximal-c*c+distance*distance)/(2*distance)
        radius=math.sqrt(max(0,proximal*proximal-along*along))
        center=hip+axis*along
        offset=desired-center;offset-=axis*offset.dot(axis)
        if offset.length<1e-6:
            offset=Vector((0,1,0));offset-=axis*offset.dot(axis)
        desired=center+offset.normalized()*radius
    return desired,(fitted-desired).normalized(),(fitted-ankle_goal).length

BODY=[('pelvis','spine_01','Back','Torso'),('spine_01','spine_02','Torso','Torso2'),
      ('spine_02','chest','Torso2','Torso3'),('chest','neck_01','Torso3','Neck1'),
      ('neck_01','neck_02','Neck1','Neck2'),('neck_02','neck_03','Neck2','Neck3'),
      ('neck_03','head','Neck3','Head'),('head',None,'Head',None)]
rows=[];goals=[];foot_tracks={n+'.'+s:[] for s in ('L','R') for n in ('front_toes','rear_toes')}
for index,source in enumerate(SRC['samples']):
    local={n:m.copy() for n,m in LOCAL.items()}
    # The fitted bind stands near full leg extension; a 7.5 cm running crouch
    # gives the borrowed gait its required knee/elbow flexion reserve.
    local['pelvis'].translation+=REST['root'].inverted().to_3x3()@((hip_center(source)-source_hips)*scale+Vector((0,0,-.075)))
    for n,child,a,b in BODY:orient(local,n,direction(source,a,b),child)
    for side in ('L','R'):
        suffix='.'+side
        # Shoulder is a short floating support in this fitted mesh. Transfer
        # source shoulder motion without imposing its horizontal bind shape.
        n='scapula'+suffix;sn='FrontShoulder'+suffix
        delta=Matrix(source[sn]['matrix']).to_quaternion()@Matrix(SRC['rest'][sn]['matrix']).to_quaternion().inverted()
        setq(local,n,delta@REST[n].to_quaternion())
        for front in (True,False):
            if front:
                toe='front_toes'+suffix;ankle='carpus'+suffix
                sa='IKFrontLeg'+suffix;st='FF'+suffix
            else:
                toe='rear_toes'+suffix;ankle='hindfoot'+suffix
                sa='IKBackLeg'+suffix;st='FFB'+suffix
            # Ground-relative source trajectory, with the target's neutral
            # footprint retained and lateral travel fitted to its narrower body.
            movement=(p(source,st)-p(SRC['rest'],st))*scale
            movement.x*=.35
            movement.y*=.9
            toe_goal=REST[toe].translation+movement
            paw_dir=direction(source,sa,st).normalized()
            paw_len=(REST[toe].translation-REST[ankle].translation).length
            ankle_goal=toe_goal-paw_dir*paw_len
            if front:
                chain=[n+suffix for n in ('upperarm','forearm','carpus')]
                residual=two_bone(local,chain,ankle_goal,1.)
            else:
                # Prescribe the source hock direction, then solve the proximal
                # two links. This prevents the third link flipping at gathering.
                shank=direction(source,'BackLowerLeg'+suffix,sa).normalized()
                shank.x*=.35;shank.normalize()
                hock_goal,shank,unreachable=fit_hock(local,suffix,ankle_goal,shank)
                residual=unreachable+two_bone(local,[n+suffix for n in ('thigh','calf','hock')],hock_goal,-1.)
                orient(local,'hock'+suffix,shank,ankle)
            orient(local,ankle,paw_dir,toe)
            orient(local,toe,direction(source,st))
            goals.append({'frame':index+1,'foot':toe,'unreachable_m':residual})
            foot_tracks[toe].append(list(fk(local)[toe].translation))
        for t,sn in [('ear_base','Ear1'),('ear_tip','Ear3')]:
            n=t+suffix;sn=sn+suffix
            delta=Matrix(source[sn]['matrix']).to_quaternion()@Matrix(SRC['rest'][sn]['matrix']).to_quaternion().inverted()
            setq(local,n,delta@REST[n].to_quaternion())
    for j in range(6):
        n=f'tail_{j+1:02}';sn='Tail'+str([1,2,3,5,6,8][j])
        delta=Matrix(source[sn]['matrix']).to_quaternion()@Matrix(SRC['rest'][sn]['matrix']).to_quaternion().inverted()
        setq(local,n,delta@REST[n].to_quaternion())
    rows.append(local)
rows[-1]={n:m.copy() for n,m in rows[0].items()}
for frame,local in enumerate(rows,1):
    for name in NAMES:
        b=rig.pose.bones[name];pos,rot,_=(LOCAL[name].inverted()@local[name]).decompose()
        if frame>1 and b.rotation_quaternion.dot(rot)<0:rot.negate()
        b.rotation_mode='QUATERNION';b.location=pos;b.rotation_quaternion=rot;b.scale=(1,1,1)
        for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=frame,group=name)
speeds=[]
for track in foot_tracks.values():
    floor=min(p[2] for p in track)
    for a,b in zip(track,track[1:]):
        v=(b[1]-a[1])*60
        if max(a[2],b[2])<floor+.025 and v>.1:speeds.append(v*100)
speed=statistics.median(speeds)
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=OUT/'A_InfectedDogMeshy_GodotRunFitV2.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
    use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'InfectedDog_GodotRunFitV2.blend'))
report={'source':'Quaternius Godot archive Gallop','license':'CC0-1.0','source_url':'https://quaternius.com/packs/ultimateanimatedanimals.html',
        'source_commit':'49cec1dd11d65295f43c737bac327de829cfd7b1','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'seconds':34/60,'fps':60,'reference_run_speed_cm_s':speed,'scale':scale,'fbx':str(fbx),
        'slots':['Run','RunTurnLeft','RunTurnRight'],'turn_policy':'Same cycle; actor steering',
        'mesh_or_weights_changed':False,'run_crouch_m':.075,'sagittal_travel_factor':.9,
        'maximum_unreachable_m':max(x['unreachable_m'] for x in goals)}
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(OUT/'foot_goals.json').write_text(json.dumps(goals,indent=2),encoding='utf-8')
print('GODOT_RUN_AUTHORED '+json.dumps(report),flush=True)
