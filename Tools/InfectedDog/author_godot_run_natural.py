"""Polish the current Godot-based canine run without changing its rig/weights.

Absolute anatomical directions and explicit canine joint planes replace
rest-rotation deltas / unconstrained hind-leg FABRIK. Mesh and weights stay put.
"""
import json,math,statistics,hashlib
from pathlib import Path
import bpy
from mathutils import Matrix,Vector,Quaternion

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/InfectedDogMeshy20260924'
OUT=BASE/'GodotRunNaturalV3';OUT.mkdir(exist_ok=True)
SOURCE=BASE/'GodotRunFitV2/Source/godot_gallop_samples.json'
SRC=json.loads(SOURCE.read_text(encoding='utf-8'))
FPS=120
PERIOD=34/60
COUNT=68

def smoothstep(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)))
    return t*t*t*(t*(t*6-15)+10)

# Smooth the source controls around the cycle, before contact constraints and
# IK. Never average final bone rotations after planting the feet.
RAW=SRC['samples'][:-1]
KERNEL=[(-2,.035),(-1,.18),(0,.57),(1,.18),(2,.035)]
SMOOTH=[]
for i in range(len(RAW)):
    row={}
    for n in RAW[i]:
        item={}
        for key in ('head','tail'):
            item[key]=sum((Vector(RAW[(i+d)%len(RAW)][n][key])*w for d,w in KERNEL),Vector())
        q=Matrix(RAW[i][n]['matrix']).to_quaternion()
        neighbors=Matrix(RAW[(i-1)%len(RAW)][n]['matrix']).to_quaternion().slerp(Matrix(RAW[(i+1)%len(RAW)][n]['matrix']).to_quaternion(),.5)
        item['q']=q.slerp(neighbors,.32)
        row[n]=item
    SMOOTH.append(row)

def source_at(frame):
    at=(frame%COUNT)*len(RAW)/COUNT
    i=int(math.floor(at));t=at-i
    row={}
    for n in SMOOTH[i]:
        item={}
        for key in ('head','tail'):
            a,b,c,d=[SMOOTH[(i+k)%len(RAW)][n][key] for k in (-1,0,1,2)]
            item[key]=.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)
        q=SMOOTH[i][n]['q'].slerp(SMOOTH[(i+1)%len(RAW)][n]['q'],t)
        item['matrix']=Matrix.LocRotScale(item['head'],q,Vector((1,1,1)))
        row[n]=item
    return row

SAMPLES=[source_at(i) for i in range(COUNT)]
bpy.ops.wm.open_mainfile(filepath=str(BASE/'CompletionV2/InfectedDog_MeshyV2.blend'))
scene=bpy.context.scene;scene.render.fps=FPS;scene.render.fps_base=1.
scene.frame_start=1;scene.frame_end=COUNT+1
rig=next(o for o in scene.objects if o.type=='ARMATURE');rig.name='Armature'
rig.animation_data_clear();rig.animation_data_create()
rig.animation_data.action=bpy.data.actions.new('A_InfectedDogMeshy_GodotRunNaturalV3')
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
    # Ease into the reach limit over 3.5 cm instead of suddenly locking the
    # knee at the old clipping threshold.
    width=.035
    h=max(0.,width-abs(reach-proximal))/width
    softened=min(reach,proximal)-h*h*width*.25
    softened=max(abs(distance-c)+1e-6,softened)
    if reach>softened+1e-6:
        along=(softened*softened-c*c+distance*distance)/(2*distance)
        radius=math.sqrt(max(0,softened*softened-along*along))
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

MEAN_HIP=sum((hip_center(row) for row in SAMPLES),Vector())/COUNT
MEAN_DIR={n:sum((direction(row,a,b).normalized() for row in SAMPLES),Vector()).normalized() for n,_,a,b in BODY}
FOOT={};support_slopes=[]

def cyclic_regions(mask):
    # Return each stance once, including a stance that crosses the loop seam.
    regions=[]
    for start in range(COUNT):
        if mask[start] and not mask[(start-1)%COUNT]:
            region=[];at=start
            while mask[at%COUNT] and len(region)<COUNT:
                region.append(at);at+=1
            regions.append(region)
    return regions

for side in ('L','R'):
    for front in (True,False):
        toe=('front_toes' if front else 'rear_toes')+'.'+side
        st=('FF' if front else 'FFB')+'.'+side
        positions=[]
        for row in SAMPLES:
            move=(p(row,st)-p(SRC['rest'],st))*scale
            move.x*=.35;move.y*=.9
            positions.append(REST[toe].translation+move)
        floor=min(point.z for point in positions)
        contact=[1-smoothstep(.002,.022,point.z-floor) for point in positions]
        regions=cyclic_regions([w>.02 for w in contact])
        for region in regions:
            active=[j for j in region if contact[j%COUNT]>.85]
            if len(active)<3:continue
            ct=sum(active)/len(active);cy=sum(positions[j%COUNT].y for j in active)/len(active)
            slope=sum((j-ct)*(positions[j%COUNT].y-cy) for j in active)/sum((j-ct)**2 for j in active)*FPS
            if slope>.1:support_slopes.append(slope)
        FOOT[toe]={'positions':positions,'contact':contact,'regions':regions}
SUPPORT_SPEED=statistics.median(support_slopes)
for toe,data in FOOT.items():
    positions=data['positions'];weights=data['contact']
    for region in data['regions']:
        total=sum(weights[j%COUNT] for j in region)
        center_t=sum(j*weights[j%COUNT] for j in region)/total
        center=sum((positions[j%COUNT]*weights[j%COUNT] for j in region),Vector())/total
        for j in region:
            index=j%COUNT;weight=weights[index]
            planted=Vector((center.x,center.y+SUPPORT_SPEED*(j-center_t)/FPS,REST[toe].translation.z))
            positions[index]=positions[index].lerp(planted,weight)

def source_delta(row,n):
    return Matrix(row[n]['matrix']).to_quaternion()@Matrix(SRC['rest'][n]['matrix']).to_quaternion().inverted()

rows=[];goals=[];foot_tracks={n+'.'+s:[] for s in ('L','R') for n in ('front_toes','rear_toes')}
for index,source in enumerate(SAMPLES):
    local={n:m.copy() for n,m in LOCAL.items()}
    # The fitted bind stands near full leg extension; a 7.5 cm running crouch
    # gives the borrowed gait its required knee/elbow flexion reserve.
    hip=hip_center(source)
    hip.z=MEAN_HIP.z+(hip.z-MEAN_HIP.z)*.90
    local['pelvis'].translation+=REST['root'].inverted().to_3x3()@((hip-source_hips)*scale+Vector((0,0,-.075)))
    for n,child,a,b in BODY:
        d=direction(source,a,b).normalized()
        if n.startswith('neck'):d=MEAN_DIR[n].lerp(d,.88).normalized()
        elif n=='head':d=MEAN_DIR[n].lerp(d,.68).normalized()
        orient(local,n,d,child)
    for side in ('L','R'):
        suffix='.'+side
        # Shoulder is a short floating support in this fitted mesh. Transfer
        # source shoulder motion without imposing its horizontal bind shape.
        n='scapula'+suffix;sn='FrontShoulder'+suffix
        delta=source_delta(source,sn)
        old=delta@REST[n].to_quaternion()
        source_parent=SRC['rest'][sn]['parent']
        relative=source_delta(source,source_parent).inverted()@delta
        parent=fk(local)['chest'].to_quaternion()@REST['chest'].to_quaternion().inverted()
        coupled=parent@relative@REST[n].to_quaternion()
        setq(local,n,old.slerp(coupled,.35))
        for front in (True,False):
            if front:
                toe='front_toes'+suffix;ankle='carpus'+suffix
                sa='IKFrontLeg'+suffix;st='FF'+suffix
            else:
                toe='rear_toes'+suffix;ankle='hindfoot'+suffix
                sa='IKBackLeg'+suffix;st='FFB'+suffix
            # Ground-relative source trajectory, with the target's neutral
            # footprint retained and lateral travel fitted to its narrower body.
            toe_goal=FOOT[toe]['positions'][index]
            contact=FOOT[toe]['contact'][index]
            paw_dir=direction(source,sa,st).normalized()
            neutral=(REST[toe].translation-REST[ankle].translation).normalized()
            paw_dir=paw_dir.lerp(neutral,contact*.48).normalized()
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
            toe_direction=direction(source,st).normalized()
            neutral=(rig.data.bones[toe].tail_local-rig.data.bones[toe].head_local).normalized()
            orient(local,toe,toe_direction.lerp(neutral,contact*.82).normalized())
            goals.append({'frame':index+1,'foot':toe,'unreachable_m':residual})
            foot_tracks[toe].append(list(fk(local)[toe].translation))
        for t,sn in [('ear_base','Ear1'),('ear_tip','Ear3')]:
            n=t+suffix;sn=sn+suffix
            delta=source_delta(source,sn)
            relative=source_delta(source,'Head').inverted()@delta
            parent=fk(local)['head'].to_quaternion()@REST['head'].to_quaternion().inverted()
            setq(local,n,(delta@REST[n].to_quaternion()).slerp(parent@relative@REST[n].to_quaternion(),.65))
    for j in range(6):
        n=f'tail_{j+1:02}';sn='Tail'+str([1,2,3,5,6,8][j])
        # Delayed source motion along the tail, with no synthetic sine wave.
        delayed=source_at(index-(.012+j*.007)*FPS)
        delta=source_delta(delayed,sn)
        setq(local,n,delta@REST[n].to_quaternion())
    rows.append(local)
rows.append({n:m.copy() for n,m in rows[0].items()})
for frame,local in enumerate(rows,1):
    for name in NAMES:
        b=rig.pose.bones[name];pos,rot,_=(LOCAL[name].inverted()@local[name]).decompose()
        if frame>1 and b.rotation_quaternion.dot(rot)<0:rot.negate()
        b.rotation_mode='QUATERNION';b.location=pos;b.rotation_quaternion=rot;b.scale=(1,1,1)
        for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=frame,group=name)
speed=SUPPORT_SPEED*100
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=OUT/'A_InfectedDogMeshy_GodotRunNaturalV3.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
    use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'InfectedDog_GodotRunNaturalV3.blend'))
report={'source':'Quaternius Godot archive Gallop','license':'CC0-1.0','source_url':'https://quaternius.com/packs/ultimateanimatedanimals.html',
        'source_commit':'49cec1dd11d65295f43c737bac327de829cfd7b1','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'seconds':PERIOD,'fps':FPS,'reference_run_speed_cm_s':speed,'scale':scale,'fbx':str(fbx),
        'slots':['Run','RunTurnLeft','RunTurnRight'],'turn_policy':'Same cycle; actor steering',
        'mesh_or_weights_changed':False,'run_crouch_m':.075,'sagittal_travel_factor':.9,
        'polish':{'source_control_filter':KERNEL,'stance_backward_speed_m_s':SUPPORT_SPEED,
                  'stance_toe_flatten':.82,'stance_carpus_neutral':.48,'body_vertical_amplitude':.90,
                  'neck_angle_amplitude':.88,'head_angle_amplitude':.68,'scapula_body_coupling':.35,
                  'tail_lag_seconds':[.012+j*.007 for j in range(6)],'hock_easing_width_m':.035},
        'runtime_tested':False,'preview_rendered':False,
        'maximum_unreachable_m':max(x['unreachable_m'] for x in goals)}
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(OUT/'foot_goals.json').write_text(json.dumps(goals,indent=2),encoding='utf-8')
print('GODOT_RUN_NATURAL_AUTHORED '+json.dumps(report),flush=True)
