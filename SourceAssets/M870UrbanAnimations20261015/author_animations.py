"""Retarget UC's actual M870 keys to the installed V7 bind and weapon clock.

UC reloads with the RIGHT hand while the LEFT supports the pump. Geometry,
weights, skeleton, locomotion and melee remain the installed M870 generation.
"""
import bpy,json,math,sys,bisect,re,ast
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;sys.path.insert(0,str(O))
from read_inputs import smd
P=O.parents[1];BASE=O.parent/'M870Tactical20261015'
X=O/'Exports';X.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'M870_Gameplay_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;I=Matrix.Identity(4)
input_data=json.loads((O/'inputs.json').read_text())
idle={n:Matrix(v) for n,v in input_data['target_idle'].items()}
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
source={name:smd(O/'Original/870/anims'/f'{name}.smd') for name in ('idle','draw','fire','cycle','reloadstart','reloadinsert','reloadend','reloadendCycle')}
si=source['idle']['rows'][0];sp=source['idle']['parents'];gi=si['870_parent'].inverted()
gun0=idle['WPN_root'];guninv=gun0.inverted()

def ease(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)
def mix(a,b,w):
    pa,qa,sa=a.decompose();pb,qb,sb=b.decompose()
    return Matrix.LocRotScale(pa.lerp(pb,w),qa.slerp(qb,w),sa.lerp(sb,w))
def sample(name,f):
    rows=source[name]['rows'];f=max(0,min(float(f),len(rows)-1));i=int(f)
    return {n:mix(m,rows[min(i+1,len(rows)-1)][n],f-i) for n,m in rows[i].items()}
def clock(t,knots):
    if t<=knots[0][0]:return knots[0][1]
    for (a,x),(b,y) in zip(knots,knots[1:]):
        if t<=b:return x+(y-x)*(t-a)/(b-a)
    return knots[-1][1]
def under(n,ancestor):
    while n:
        if n==ancestor:return True
        n=parents.get(n)
    return False
def frame(forward,up):
    y=forward.normalized();z=(up-y*up.dot(y)).normalized();x=y.cross(z).normalized()
    return Matrix((x,y,z)).transposed().to_4x4()
# Map firearm forward/up axes, not either author's arbitrary root-bone axes.
sf=frame(si['870_flash'].translation-si['870_bolt'].translation,si['870_bolt'].translation-si['870_loadingport'].translation)
tf=frame(idle['WPN_FrontSight'].translation-idle['WPN_RearSight'].translation,idle['WPN_RearSight'].translation-idle['WPN_SOCKET_Magazine'].translation)
R=tf@sf.inverted();Rq=R.to_quaternion()
C=Matrix.Translation(idle['WPN_SOCKET_Magazine'].translation)@R@Matrix.Translation(-si['870_loadingport'].translation)
Ci=C.inverted()
hand_corrections={};finger_corrections={};finger_map={}
for side in ('l','r'):
    sn='ValveBiped.Bip01_'+side.upper()+'_Hand'
    hand_corrections[side]=(C@si[sn]).inverted()@idle['hand_'+side]
    for digit,word in enumerate(('thumb','index','middle','ring','pinky')):
        for joint in range(3):
            target=f'{word}_{joint+1:02d}_{side}'
            donor=f'ValveBiped.Bip01_{side.upper()}_Finger{digit}'+('' if joint==0 else str(joint))
            if target in idle and donor in si:
                finger_map[target]=donor
                finger_corrections[target]=(Rq@si[donor].to_quaternion()).inverted()@idle[target].to_quaternion()

def mapped_rotation(name,target,pose):
    return Rq@pose[name].to_quaternion()@si[name].to_quaternion().inverted()@Rq.inverted()@idle[target].to_quaternion()

def solve_arm(row,side,hand,pose=None):
    """Keep the native bone lengths; carry source elbow swing and forearm roll."""
    un='upperarm_'+side;ln='lowerarm_'+side;hn='hand_'+side;cl='clavicle_'+side
    old=idle;shoulder=old[un].translation.copy();elbow=old[ln].translation;wrist=old[hn].translation
    l1=(elbow-shoulder).length;l2=(wrist-elbow).length
    upperq=old[un].to_quaternion();foreq=old[ln].to_quaternion()
    pole=elbow-shoulder
    if pose:
        prefix='ValveBiped.Bip01_'+side.upper()+'_'
        shoulder+=R.to_3x3()@(pose[prefix+'UpperArm'].translation-si[prefix+'UpperArm'].translation)*.78
        delta=(R.to_3x3()@(si[prefix+'Forearm'].translation-si[prefix+'UpperArm'].translation)).rotation_difference(R.to_3x3()@(pose[prefix+'Forearm'].translation-pose[prefix+'UpperArm'].translation))
        pole=delta@pole
        upperq=mapped_rotation(prefix+'UpperArm',un,pose)
        foreq=mapped_rotation(prefix+'Forearm',ln,pose)
    goal=hand.translation;axis=goal-shoulder;distance=axis.length
    # A native arm is shorter than the Source rig. Translate the hidden arm
    # root continuously when needed instead of stretching skin/bone segments.
    reach=.94*(l1+l2)
    if distance>reach:
        shoulder+=axis.normalized()*(distance-reach);axis=goal-shoulder;distance=axis.length
    row[cl]=idle[cl].copy();row[cl].translation+=shoulder-old[un].translation
    axis.normalize();pole-=axis*pole.dot(axis)
    if pole.length<1e-7:pole=Vector((-.6 if side=='l' else .6,-.2,-1)).cross(axis)
    pole.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*max(distance,1e-7))
    e=shoulder+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    ua=old[un].to_quaternion().inverted()@(elbow-old[un].translation)
    fa=old[ln].to_quaternion().inverted()@(wrist-elbow)
    upperq=(upperq@ua).rotation_difference(e-shoulder)@upperq
    foreq=(foreq@fa).rotation_difference(goal-e)@foreq
    um=Matrix.LocRotScale(shoulder,upperq,Vector((1,1,1)));fm=Matrix.LocRotScale(e,foreq,Vector((1,1,1)))
    ud=um@old[un].inverted();fd=fm@old[ln].inverted();hd=hand@old[hn].inverted()
    for n in row:
        if under(n,hn):row[n]=hd@old[n]
        elif under(n,ln):row[n]=fd@old[n]
        elif under(n,un):row[n]=ud@old[n]

def fingers(row,side,pose):
    for target,donor in finger_map.items():
        if not target.endswith('_'+side):continue
        tp=parents[target];dp=sp[donor]
        # Manny has metacarpals where Source goes directly from palm to digit.
        bp=(Rq@si[dp].to_quaternion()).inverted()@idle[tp].to_quaternion()
        local_source=pose[dp].to_quaternion().inverted()@pose[donor].to_quaternion()
        q=bp.inverted()@local_source@finger_corrections[target]
        loc=idle[tp].inverted()@idle[target]
        row[target]=row[tp]@Matrix.LocRotScale(loc.translation,q,Vector((1,1,1)))

def retarget(pose,loading=0.):
    row={n:m.copy() for n,m in idle.items()}
    motion=C@pose['870_parent']@gi@Ci
    row['WPN_root']=motion@gun0
    for n in row:
        if n.startswith('WPN_'):row[n]=motion@idle[n]
    for side in ('l','r'):
        sn='ValveBiped.Bip01_'+side.upper()+'_Hand';base=C@pose[sn]
        hand=base@hand_corrections[side]
        # Offsets stay on the gun while the hand is carrying it. During
        # right-hand loading the loading-port registration owns the position.
        offset=idle['hand_'+side].translation-(C@si[sn]).translation
        hand.translation=(C@pose[sn]).translation+motion.to_3x3()@offset*(1-loading if side=='r' else 1)
        solve_arm(row,side,hand,pose);fingers(row,side,pose)
    # Convert the original pump stroke to this model's measured 105 mm travel.
    local=pose['870_parent'].inverted()@pose['870_slide']
    base=gi@si['870_slide'];travel=(base.translation-local.translation).length
    source_travel=max((gi@si['870_slide']).translation.z-(p['870_parent'].inverted()@p['870_slide']).translation.z for p in source['cycle']['rows'])
    amount=max(0,min(1,travel/source_travel))
    shift=motion.to_3x3()@tf.to_3x3()@Vector((0,-.105*amount,0))
    row['WPN_bolt'].translation+=shift
    # The left hand remains clamped on the installed pump with its source
    # finger articulation; no accumulated stroke mismatch between gun models.
    if amount>0:
        expected=motion@idle['hand_l'];expected.translation+=shift
        solve_arm(row,'l',expected,pose);fingers(row,'l',pose)
    # Source loading gate and trigger retain their keyed local rotations.
    for donor,target in [('870_loadingport','WPN_Load'),('870_trigger','WPN_Trigger')]:
        relative=pose['870_parent'].inverted()@pose[donor]
        original=gi@si[donor]
        local_delta=relative@original.inverted()
        d=C@si['870_parent']@local_delta@gi@Ci
        row[target]=motion@d@idle[target]
    return row

# Source cartridge geometry supplies its bone-to-shell centre and long axis.
meshpath=O/'Original/870/shotgun.smd';mesh_source=smd(meshpath)
lines=meshpath.read_text().splitlines();ids={};section='';points=[]
for line in lines:
    if line in ('nodes','skeleton','triangles'):section=line;continue
    if line=='end':section='';continue
    if section=='nodes':
        m=re.match(r'(\d+) "([^"]+)" (-?\d+)',line.strip())
        if m:ids[int(m[1])]=m[2]
    elif section=='triangles':
        v=line.split()
        if len(v)>=10 and v[0].lstrip('-').isdigit():
            weights=[(int(v[i]),float(v[i+1])) for i in range(10,len(v)-1,2)] if len(v)>10 else [(int(v[0]),1.)]
            if any(ids.get(n)=='870_shell2' and w>.5 for n,w in weights):points.append(Vector(list(map(float,v[1:4])))*.0254)
if not points:raise RuntimeError('Original cartridge surface is missing')
shell_rest=mesh_source['rows'][0]['870_shell2'];local_points=np.array([list(shell_rest.inverted()@v) for v in points]);centre=local_points.mean(axis=0)
eigenvalues,eigenvectors=np.linalg.eigh(np.cov(local_points.T));shell_axis=Vector(eigenvectors[:,-1])
contact=source['reloadinsert']['rows'][12]
forward=(si['870_flash'].translation-si['870_bolt'].translation).normalized()
if (contact['870_shell2'].to_3x3()@shell_axis).dot(forward)<0:shell_axis=-shell_axis
target_centre=Vector(json.loads((O/'contacts.json').read_text())['shell_center_local'])
B=Vector((0,1,0)).rotation_difference(shell_axis).to_matrix().to_4x4();B.translation=Vector(centre)-B.to_3x3()@target_centre
def shell(row,pose,phase):
    row['WPN_Shell']=C@pose['870_shell2']@B
    if phase>=14.:
        p,q,sc=row['WPN_Shell'].decompose();row['WPN_Shell']=Matrix.LocRotScale(p,q,Vector((.001,.001,.001)))

# Reuse only the exporter implementation, not the old model-generation job.
tree=ast.parse((BASE/'author_m870.py').read_text())
selected=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in ('select','bake')]
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
authored={};(X/'Animations').mkdir(exist_ok=True)
exec(compile(ast.Module(body=selected,type_ignores=[]),str(BASE/'author_m870.py'),'exec'))

equip=[retarget(sample('draw',23*f/36)) for f in range(37)]
def cycle_pose(t,start=.12,end=64/60):
    # Source minimum fore-end position is the rearward turning point.
    rows=source['cycle']['rows'];peak=min(range(len(rows)),key=lambda i:(rows[i]['870_parent'].inverted()@rows[i]['870_slide']).translation.z)
    f=clock(t,[(0,0),(start,0),(.35,peak),(.40,peak),(.62,10),(end,20)])
    return retarget(sample('cycle',f))
cycle=[cycle_pose(f/60) for f in range(65)]
fire=[]
for f in range(55):
    t=f/60
    if t<=.16:row=retarget(sample('fire',13*t/.16))
    else:row=cycle_pose(t,.16,.90)
    fire.append(row)
bake('equip',equip);bake('cycle',cycle);bake('fire',fire)
for role,empty,last in [('reload_continuous',False,399),('reload_full',True,424)]:
    rows=[]
    tail_name='reloadendCycle' if empty else 'reloadend'
    tail_count=len(source[tail_name]['rows'])-1
    tail_peak=min(range(tail_count+1),key=lambda i:(source[tail_name]['rows'][i]['870_parent'].inverted()@source[tail_name]['rows'][i]['870_slide']).translation.z) if empty else 0
    for f in range(last+1):
        t=f/60
        if t<.30:
            pose=sample('reloadstart',20*t/.30);row=retarget(pose,ease(t/.30))
        elif t<6.:
            index=0 if t<1. else min(6,1+int((t-1.)/(50/60)+1.e-6))
            start=.30 if index==0 else 1.+(index-1)*50/60
            contact_time=44/60+index*50/60;finish=1.+index*50/60
            phase=clock(t,[(start,0),(contact_time,12),(finish,26)])
            pose=sample('reloadinsert',phase);row=retarget(pose,1.);shell(row,pose,phase)
        else:
            phase=clock(t,[(6.,0),(6.30,15),(6.43,tail_peak),(6.48,tail_peak),(6.62,26),(last/60,tail_count)]) if empty else (t-6.)/(last/60-6.)*tail_count
            pose=sample(tail_name,phase);row=retarget(pose,1-ease(phase/9))
        rows.append(row)
    # Exact hand-off to the installed idle; donor transitions already reach it.
    rows[-1]={n:m.copy() for n,m in idle.items()}
    bake(role,rows)

# Original inspection: two deliberate side presentations, supported at the
# actual M870 grip points. Arms solve independently instead of rotating skin
# and shoulders as one rigid object. This is not a claimed UC inspect clip.
inspect=[];pivot=idle['hand_r'].translation
knots=[(0,0.,0.,0.),(.55,-.56,-.10,.035),(.92,-.56,-.10,.035),(1.45,.30,.12,.045),(1.78,.30,.12,.045),(2.50,0.,0.,0.)]
for f in range(151):
    t=f/60
    a,b=next(((a,b) for a,b in zip(knots,knots[1:]) if a[0]<=t<=b[0]),(knots[-2],knots[-1]))
    w=ease((t-a[0])/(b[0]-a[0]));roll=a[1]+(b[1]-a[1])*w;yaw=a[2]+(b[2]-a[2])*w;lift=a[3]+(b[3]-a[3])*w
    d=Matrix.Translation((0,-.015*math.sin(math.pi*t/2.5),lift))@Matrix.Translation(pivot)@tf@Matrix.Rotation(roll,4,'Y')@Matrix.Rotation(yaw,4,'Z')@tf.inverted()@Matrix.Translation(-pivot)
    row={n:m.copy() for n,m in idle.items()}
    for n in row:
        if n.startswith('WPN_'):row[n]=d@idle[n]
    for side in ('l','r'):solve_arm(row,side,d@idle['hand_'+side])
    inspect.append(row)
bake('inspect',inspect)
r.animation_data.action=bpy.data.actions['A_M870_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0)
s.frame_start=0;s.frame_end=150;bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_Urban_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(dict(clips=authored,source_commit=json.loads((O/'acquisition.json').read_text())['commit'],source_fps=30,export_fps=60,source_reload_hand='right',source_support_hand='left',inspect_source='newly authored on the installed M870 grip',shell_source='retained project 12g mesh; UC shell2 motion only',contact_source_frame=12,insert_time=44/60,loop_step=50/60,tail_time=6.,pump_travel=.105,source_to_target=[list(v) for v in C],runtime_tested=False),indent=2))
print('M870_UC_AUTHORED',len(authored),'clips',flush=True)
