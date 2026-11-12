"""M27 right attack: native Attack6 torso drive and a short horizontal hook.

Authoring/export only. No renders, gameplay or acceptance probes.
Clean native Beast06 inputs and the accepted V14 guard are retained separately.
"""
from pathlib import Path
import json
import math
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
ROOT=BASE/'Beast06V2'; OUT=ROOT/'Delivery'; OUT.mkdir(parents=True,exist_ok=True)
SOURCE=json.loads((BASE/'Beast06V1/native_poses.json').read_text())['clips']['Attack6']
bpy.ops.wm.open_mainfile(filepath=str(BASE/'ClawV14/Delivery/MantisM27_ClawV14.blend'))
scene=bpy.context.scene; scene.render.fps=FPS=60; scene.render.fps_base=1.
rig=next(o for o in scene.objects if o.type=='ARMATURE')
for track in rig.animation_data.nla_tracks: track.mute=True
names=[b.name for b in rig.data.bones]
parent={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n].copy() for n in names}
rig.animation_data.action=bpy.data.actions['A_M27_LeftSlash_ClawV14']
if rig.animation_data.action.slots: rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(1)
guard={n:rig.pose.bones[n].matrix.copy() for n in names}
guard_local={n:guard[parent[n]].inverted()@guard[n] if parent[n] else guard[n].copy() for n in names}
reflection=Matrix.Diagonal((1.,-1.,1.))
helper=lambda n:n.startswith(('blade_','hand_','ball_','headfront','head_tip','chain_','membrane_'))

def smooth(x):
    x=min(1.,max(0.,x)); return x*x*(3.-2.*x)

def curve(t,keys):
    """Shape-preserving cubic; no flat key holds or linear whole-clip motion."""
    xs=np.asarray([k[0] for k in keys]); ys=np.asarray([k[1] for k in keys])
    if t<=xs[0]: return float(ys[0])
    if t>=xs[-1]: return float(ys[-1])
    sec=np.diff(ys)/np.diff(xs); slopes=np.zeros(len(xs))
    for i in range(1,len(xs)-1):
        if sec[i-1]*sec[i]>0:
            h0=xs[i]-xs[i-1]; h1=xs[i+1]-xs[i]
            slopes[i]=(3*(h0+h1))/((2*h1+h0)/sec[i-1]+(h1+2*h0)/sec[i])
    i=int(np.searchsorted(xs,t)-1); h=xs[i+1]-xs[i]; x=(t-xs[i])/h
    return float((2*x**3-3*x*x+1)*ys[i]+(x**3-2*x*x+x)*h*slopes[i]
                 +(-2*x**3+3*x*x)*ys[i+1]+(x**3-x*x)*h*slopes[i+1])

def rebuild(m,rotations):
    out={}
    for n in names:
        rel=m[parent[n]].inverted()@m[n] if parent[n] else m[n].copy()
        pose=out[parent[n]]@rel if parent[n] else rel.copy()
        if n in rotations:
            p=pose.translation.copy(); pose=rotations[n].to_matrix().to_4x4(); pose.translation=p
        out[n]=pose
    return out

def build(rotations,hip):
    out={}
    for n in names:
        rel=Matrix.LocRotScale(local[n].translation,rotations.get(n,local[n].to_quaternion()),Vector((1,1,1)))
        out[n]=out[parent[n]]@rel if parent[n] else rel
        if n=='pelvis': out[n].translation=hip
    return out

# Convert the saved native UE result once; do not inherit the rejected V1 bake.
raw=[]
for frame in SOURCE['frames']:
    m={}
    for n in names:
        pose=m[parent[n]]@local[n] if parent[n] else local[n].copy()
        if not helper(n):
            delta=Quaternion(frame[n]['q'])@Quaternion(SOURCE['reference'][n]['q']).inverted()
            q=(reflection@delta.to_matrix()@reflection).to_quaternion()@rest[n].to_quaternion()
            p=pose.translation.copy(); pose=q.to_matrix().to_4x4(); pose.translation=p
        if n=='pelvis':
            pose.translation=rest[n].translation+reflection@(Vector(frame[n]['p'])-Vector(SOURCE['reference'][n]['p']))
        m[n]=pose
    raw.append(m)

def sample(time):
    f=min(len(raw)-1,max(0.,time*FPS)); i=int(f); j=min(i+1,len(raw)-1); alpha=f-i
    rotations={}
    for n in names:
        a=raw[i][parent[n]].inverted()@raw[i][n] if parent[n] else raw[i][n]
        b=raw[j][parent[n]].inverted()@raw[j][n] if parent[n] else raw[j][n]
        rotations[n]=a.to_quaternion().slerp(b.to_quaternion(),alpha)
    return rotations,raw[i]['pelvis'].translation.lerp(raw[j]['pelvis'].translation,alpha)

initial,initial_hip=sample(0.)
clock=[(0.,0.),(.10,.025),(.175,.06),(.26,.206),(.32,.29),(.425,.41),(.54,.57),(.65,SOURCE['seconds'])]

# Geometry-derived signed cutting frames and conservative whole-blade cages.
weights=np.load(BASE/'BindingV2/binding_weights_v2.npz')
topology=np.load(BASE/'BindingV2/connected_source.npz')
p=topology['points']; points=np.column_stack((p[:,0],-p[:,2],p[:,1]-p[:,1].min()))*100.
indices={n:i for i,n in enumerate(weights['names'])}
blade_axes={}; cages={}; feet={}; anchors={}; floor={}
def axes(a,b):
    a=a.normalized(); b=(b-a*b.dot(a)).normalized()
    return Matrix((a,b,a.cross(b))).transposed().to_quaternion()
for side in ['l','r']:
    n='blade_root_'+side; cloud=points[weights['weights'][:,indices[n]]>.999]
    normal=Vector(np.linalg.svd(cloud-cloud.mean(0),full_matrices=False)[2][-1])
    chord=rest['blade_tip_'+side].translation-rest[n].translation
    chord=(chord-normal*chord.dot(normal)).normalized()
    bend=normal.cross(chord).normalized()
    if bend.dot(rest['blade_mid_'+side].translation-rest[n].translation)<0: bend.negate()
    blade_axes[side]=axes(chord,bend)
    inverse=np.asarray(rest[n].inverted()); cloud=cloud@inverse[:3,:3].T+inverse[:3,3]
    direction=np.linalg.svd(cloud-cloud.mean(0),full_matrices=False)[2][0]; distance=cloud@direction
    bins=np.minimum(13,((distance-distance.min())/np.ptp(distance)*14).astype(int)); cage=[]
    for k in range(14):
        section=cloud[bins==k]
        if not len(section): continue
        lo,hi=section.min(0),section.max(0)
        cage.extend((x,y,z) for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]])
    cages[side]=np.asarray(cage)
    n='foot_'+side; cloud=points[weights['weights'][:,indices[n]]>.999]
    inverse=np.asarray(rest[n].inverted()); feet[side]=cloud@inverse[:3,:3].T+inverse[:3,3]
    matrix=np.asarray(guard[n]); world=feet[side]@matrix[:3,:3].T+matrix[:3,3]
    # The front portion of the actual foot is the pivot, not its ankle joint.
    front=world[:,1]<=np.quantile(world[:,1],.12)
    low=world[:,2]<=np.quantile(world[:,2],.40)
    chosen=front&low
    if not np.any(chosen): chosen=front
    anchor=Vector(world[chosen].mean(0)); floor[side]=float(world[:,2].min())
    anchors[side]=(anchor,guard[n].inverted()@anchor)

def full_body(t):
    source,hip=sample(curve(t,clock)); rot={}
    for n in names:
        # All joints sample one source clock. Staggered settling is authored as
        # pose amplitude, without shifting shoulder/elbow/wrist source times.
        start,end=(.42,.61) if n=='pelvis' else (.46,.64) if n.startswith('spine_') else (.49,.65)
        release=1.-smooth((t-start)/(end-start))
        gain=.44 if n=='pelvis' else .72
        if helper(n): gain=0.
        dq=initial[n].inverted()@source[n]
        rot[n]=guard_local[n].to_quaternion()@Quaternion().slerp(dq,gain*smooth(t/.07)*release)
    delta=hip-initial_hip; delta.x*=.55; delta.y*=.60; delta.z*=.50
    body_envelope=smooth(t/.07)*(1.-smooth((t-.42)/.19))
    shift=curve(t,[(0.,0.),(.13,3.),(.265,-4.5),(.35,-4.),(.60,0.),(.65,0.)])
    target=guard['pelvis'].translation+delta*body_envelope+Vector((shift,0,0))
    return build(rot,target)

def foot_support(m,t):
    rotations={}
    for side in ['l','r']:
        a,b,c=[part+'_'+side for part in ['thigh','calf','foot']]
        if side=='l':
            heel=curve(t,[(0.,0.),(.11,0.),(.235,13.),(.30,15.),(.40,10.),(.57,0.),(.65,0.)])
            yaw=curve(t,[(0.,0.),(.13,0.),(.275,-12.),(.38,-9.),(.59,0.),(.65,0.)])
        else:
            heel=curve(t,[(0.,0.),(.11,3.),(.21,0.),(.65,0.)])
            yaw=curve(t,[(0.,0.),(.15,0.),(.28,5.),(.42,3.),(.61,0.),(.65,0.)])
        q=Quaternion((0,0,1),math.radians(yaw))@Quaternion((1,0,0),math.radians(heel))@guard[c].to_quaternion()
        anchor,offset=anchors[side]; target=anchor-q@offset
        rotated=feet[side]@np.asarray(q.to_matrix()).T
        target.z=floor[side]-float(rotated[:,2].min())
        hip=m[a].translation; direction=target-hip; axis=direction.normalized()
        l1=(rest[b].translation-rest[a].translation).length; l2=(rest[c].translation-rest[b].translation).length
        distance=max(abs(l1-l2)+.01,min(direction.length,l1+l2-.01))
        pole=m[b].translation-hip; pole-=axis*pole.dot(axis)
        if pole.length<.01:
            pole=guard[b].translation-guard[a].translation; pole-=axis*pole.dot(axis)
        pole.normalize(); along=(l1*l1-l2*l2+distance*distance)/(2*distance)
        knee=hip+axis*along+pole*math.sqrt(max(0.,l1*l1-along*along))
        rotations[a]=(m[b].translation-hip).rotation_difference(knee-hip)@m[a].to_quaternion()
        rotations[b]=(m[c].translation-m[b].translation).rotation_difference(target-knee)@m[b].to_quaternion()
        rotations[c]=q
    return rebuild(m,rotations)

def blade_target(m,side,t):
    if side=='r':
        # Attack6 provides the distinct body/arm source. The right scythe's
        # near-horizontal cutting plane makes a short hook, not a left mirror.
        elevation=curve(t,[(0.,-40.),(.10,-20.),(.175,35.),(.205,44.),(.26,-10.),(.30,-36.),(.345,-44.),(.40,-32.),(.49,-52.),(.58,-45.),(.65,-40.)])
        yaw=curve(t,[(0.,28.),(.10,40.),(.175,45.),(.205,34.),(.26,0.),(.30,-18.),(.38,-20.),(.48,0.),(.57,20.),(.65,28.)])
        bank=curve(t,[(0.,math.degrees(math.atan(.12))),(.17,66.),(.245,72.),(.30,74.),(.38,70.),(.49,40.),(.58,15.),(.65,math.degrees(math.atan(.12)))])
    else:
        elevation=curve(t,[(0.,-40.),(.18,-55.),(.265,-66.),(.34,-61.),(.44,-55.),(.54,-47.),(.65,-40.)])
        yaw=curve(t,[(0.,28.),(.18,65.),(.265,75.),(.34,65.),(.44,55.),(.54,38.),(.65,28.)])
        bank=curve(t,[(0.,math.degrees(math.atan(.12))),(.22,10.),(.40,9.),(.65,math.degrees(math.atan(.12)))])
    sign=1. if side=='l' else -1.; yaw=math.radians(yaw); theta=math.radians(elevation); bank=math.radians(bank)
    forward=Vector((sign*math.sin(yaw),-math.cos(yaw),0))
    outward=Vector((sign*math.cos(yaw),math.sin(yaw),0))
    diagonal=Vector((0,0,1))*math.cos(bank)+outward*math.sin(bank)
    chord=forward*math.cos(theta)+diagonal*math.sin(theta)
    bend=-forward*math.sin(theta)+diagonal*math.cos(theta)
    # Follow chest motion in a calibrated frame; never pull the blade back to
    # a sampled world-space V14 orientation on every frame.
    chest=guard['spine_05'].to_quaternion().slerp(m['spine_05'].to_quaternion(),.75)@guard['spine_05'].to_quaternion().inverted()
    desired=chest@axes(chord,bend)
    current=m['blade_root_'+side].to_quaternion()@rest['blade_root_'+side].to_quaternion().inverted()@blade_axes[side]
    return desired@current.inverted()

def constrain(m,side,t,turn):
    shoulder=m['upperarm_'+side].translation; matrix=np.asarray(m['blade_root_'+side])
    vectors=[Vector(p)-shoulder for p in cages[side]@matrix[:3,:3].T+matrix[:3,3]]
    lane=smooth((t-.10)/.115)*(1.-smooth((t-.36)/.24))
    split=Vector((-math.cos(lane*math.pi*.5),-math.sin(lane*math.pi*.5),0))
    normal=split*(1 if side=='r' else -1); center=Vector((0,-45*lane,0))
    planes=[(normal,normal.dot(center)+14.),(Vector((0,0,1)),12.)]
    for _ in range(48):
        settled=True
        for normal,plane in planes:
            low=min((turn@v for v in vectors),key=lambda v:v.dot(normal)); bound=plane-shoulder.dot(normal)
            if low.dot(normal)>=bound-.01: continue
            settled=False; length=low.length
            old=math.acos(max(-1,min(1,low.dot(normal)/length)))
            new=math.acos(max(-1,min(1,(bound+.08)/length)))
            axis=low.cross(normal)
            if axis.length<1.e-5: axis=Vector((1,0,0))
            turn=Quaternion(axis.normalized(),max(0.,old-new))@turn
        if settled: break
    return turn.normalized()

frames=[]
for i in range(40):
    t=i/FPS; m=foot_support(full_body(t),t)
    turns={s:constrain(m,s,t,blade_target(m,s,t)) for s in ['l','r']}
    frames.append({'time':t,'pose':m,'turns':turns})
# Filter the adaptation correction in one quaternion hemisphere. The source
# arm chain stays intact; only the complete arm rotates about its shoulder.
for side in ['l','r']:
    source=[f['turns'][side].copy() for f in frames]
    for i,frame in enumerate(frames):
        center=source[i]; value=np.zeros(4)
        for step,weight in [(-2,1),(-1,4),(0,6),(1,4),(2,1)]:
            q=source[min(39,max(0,i+step))].copy()
            if q.dot(center)<0: q.negate()
            value+=np.asarray(q)*weight
        smoothed=Quaternion(value).normalized()
        # Keep exact guard endpoints; fade the correction filter in/out.
        mix=smooth(i/3)*smooth((39-i)/3)
        frame['turns'][side]=constrain(frame['pose'],side,frame['time'],center.slerp(smoothed,mix))

name='A_M27_RightSlash_Beast06V2'; action=bpy.data.actions.new(name); action.use_fake_user=True
rig.animation_data.action=action; scene.frame_start=1; scene.frame_end=40; previous={}
for i,frame in enumerate(frames):
    m=frame['pose']; changed={}
    for side in ['l','r']:
        n='upperarm_'+side; changed[n]=frame['turns'][side]@m[n].to_quaternion()
    m=rebuild(m,changed)
    for n in names:
        basis=local[n].inverted()@(m[parent[n]].inverted()@m[n] if parent[n] else m[n])
        pb=rig.pose.bones[n]; q=basis.to_quaternion()
        if n in previous and previous[n].dot(q)<0: q.negate()
        previous[n]=q.copy(); pb.location=basis.translation; pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=q; pb.scale=(1,1,1)
        for channel in ['location','rotation_quaternion','scale']: pb.keyframe_insert(channel,frame=i+1,group=n)
scene.frame_set(1); bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',global_scale=1.,axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
    use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0.)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MantisM27_Beast06V2_Right.blend'))
manifest={'revision':'Beast06V2','scope':'RightSlash only','fps':FPS,'mesh_revision':'BindingV2',
    'source':SOURCE['source'],'raw_asset':SOURCE['raw_asset'],'guard_baseline':'ClawV14 frame 1',
    'previous_candidate_used_as_motion_source':False,'runtime_tested':False,'rendered':False,'offline_validated':False,
    'clips':{'RightSlash':{'file':name+'.fbx','frames':40,'seconds':.65,'contact_window_seconds':[.25,.30]}},
    'source_clock':clock,'adaptation':{'pelvis_motion_gain':.44,'other_source_motion_gain':.72,
        'chest_carry_gain':.75,'rear_heel_peak_degrees':15.,'rear_pivot_peak_degrees':12.,
        'main_blade_plane_peak_degrees':74.,'attack_design':'Short right horizontal hook from native Attack6; not a mirrored left clip',
        'blade_authoring_clearance_cm':12.,'blade_lane_half_gap_cm':14.,
        'arm_policy':'One source time for the complete arm; geometry-derived signed blade frame; whole-arm shoulder adaptation',
        'recovery_policy':'Continuous blade follow-through/recurve, pelvis settles before torso, arm settles last'},
    'source_license':'Retain installed Fab Beast06 and existing ClawV14 provenance; not CC0'}
(OUT/'motion_manifest_right.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('M27_BEAST06_V2_RIGHT_AUTHORED',flush=True)
