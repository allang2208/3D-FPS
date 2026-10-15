"""Retarget the accepted Hundred-Eyed Slag donor; fit the full M66 arm outside its torso."""
import ast,bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66')
ROOT=BASE/'ClawSweepV06'
for folder in ('Authoring','Export','Records'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
prefix=(BASE/'LocomotionV02/author_locomotion.py').read_text(encoding='utf-8').split('contracts=[]')[0]
prefix=prefix.replace("ROOT.parent/'MeshyRigV01/Authoring/M66_back_completed_v01.blend'",
                      "ROOT.parent/'SurfaceLifeV05/Authoring/M66_surface_life_v05.blend'")
exec(compile(prefix,'M66_existing_locomotion_setup','exec'))
ROOT=BASE/'ClawSweepV06'
pose_frame('Idle',0.);bpy.context.view_layer.update()
neutral={n:rig.pose.bones[n].matrix.copy() for n in ordered}
nlocal={n:neutral[parents[n]].inverted()@neutral[n] if parents[n] else neutral[n].copy() for n in ordered}
base_feet={side:neutral[foot].translation.copy() for side,_,_,foot in chains}
for node in ast.parse((BASE/'ReactionsV03/author_reactions.py').read_text(encoding='utf-8')).body:
    if isinstance(node,ast.FunctionDef) and node.name in {'apply_worlds','solve_planted_legs'}:
        exec(compile(ast.Module(body=[node],type_ignores=[]),'M66_existing_support','exec'))

DURATION=2.6;FPS=60;COUNT=157
upper,lower,wrist='Bone_027','Bone_026','Bone_037'
bridge=('Bone_025','Bone_024')
finger_roots=['Bone_%03d'%n for n in (57,61,65,69,73)]
def below(name,ancestor):
    while parents[name]:
        name=parents[name]
        if name==ancestor:return True
    return False
hand_children=[n for n in ordered if below(n,wrist)]
arm_names={upper,lower,wrist,*bridge,*hand_children}
a=(neutral[lower].translation-neutral[upper].translation).length
b=(neutral[wrist].translation-neutral[lower].translation).length
u0=(neutral[lower].translation-neutral[upper].translation).normalized()
l0=(neutral[wrist].translation-neutral[lower].translation).normalized()
n0=u0.cross(l0).normalized()
def basis(direction,normal):
    direction=direction.normalized();normal=(normal-direction*normal.dot(direction)).normalized()
    return Matrix((direction,normal.cross(direction),normal)).transposed().to_quaternion()
tu0,tl0=basis(u0,n0),basis(l0,n0)

DONOR=Path('D:/FPS3D/FPSGAME/SourceAssets/HundredEyedSlagMeshy20260930/RampageReferenceIntake/source_motion/Attack_Biped_Melee_A.json')
raw=json.loads(DONOR.read_text())
# The donor's UE coordinates face +Y; the M66 authoring rig faces -Y.
C=Matrix.Diagonal((1.,-1.,1.));source=[]
for row in raw['frames']:
    frame={}
    for name,value in row['component'].items():
        x,y,z,w=value['rotation_xyzw'];q=Quaternion((w,x,y,z))
        frame[name]=(C@Vector(value['translation_cm'])*.01,(C@q.to_matrix()@C).to_quaternion())
    source.append(frame)
ref=source[0]
def sample(t):
    x=max(0.,min(1.,t))*60;i=min(60,int(x));j=min(60,i+1);f=x-i
    return {n:(p.lerp(source[j][n][0],f),q.slerp(source[j][n][1],f)) for n,(p,q) in source[i].items()}

# Keep the combat clock while retaining the donor's complete load/strike/recovery.
time_pairs=np.array([(0,0),(.84,.19),(.98,.23),(1.35,.39),(1.66,.53),(2.25,.91),(2.6,1.)])
def source_time(t):
    # Monotone cubic time mapping: changing speed does not introduce a velocity step.
    x,y=time_pairs[:,0],time_pairs[:,1];d=np.diff(y)/np.diff(x)
    slopes=np.r_[d[0],2*d[:-1]*d[1:]/(d[:-1]+d[1:]),d[-1]]
    i=min(len(x)-2,max(0,int(np.searchsorted(x,t,side='right')-1)))
    h=x[i+1]-x[i];s=(t-x[i])/h
    return (2*s**3-3*s*s+1)*y[i]+(s**3-2*s*s+s)*h*slopes[i]+(-2*s**3+3*s*s)*y[i+1]+(s**3-s*s)*h*slopes[i+1]

def arm_frame(src):
    u=(src['lowerarm_r'][0]-src['upperarm_r'][0]).normalized()
    l=(src['hand_r'][0]-src['lowerarm_r'][0]).normalized()
    normal=u.cross(l)
    if normal.length<1e-5:normal=src['upperarm_r'][1]@ref['upperarm_r'][1].inverted()@sn0
    return u,l,normal.normalized()
su0,sl0,sn0=arm_frame(ref)
sfu0,sfl0=basis(su0,sn0),basis(sl0,sn0)
align0=tu0@sfu0.inverted()
if align0.w<0:align0.negate()

def body_pose(src,t,active):
    mapping={'Bone_000':('pelvis',.48),'Bone_007':('spine_01',.50),
             'Bone_006':('spine_02',.60),'Bone_005':('spine_03',.68)}
    movement=(src['pelvis'][0]-ref['pelvis'][0])*1.25
    movement=Vector((max(-.14,min(.14,movement.x)),max(-.16,min(.16,movement.y)),max(-.06,min(.09,movement.z))))
    worlds={}
    for name in ordered:
        m=worlds[parents[name]]@nlocal[name] if parents[name] else nlocal[name].copy()
        if name=='Bone_000':m.translation+=movement
        if name in mapping:
            donor,factor=mapping[name];delta=src[donor][1]@ref[donor][1].inverted()
            if delta.w<0:delta.negate()
            m=Matrix.LocRotScale(m.translation,Quaternion().slerp(delta,factor)@neutral[name].to_quaternion(),neutral[name].to_scale())
        if name=='Bone_028':
            # Transfer clavicle motion too; preserve the target clavicle length.
            delta=src['clavicle_r'][1]@ref['clavicle_r'][1].inverted()
            if delta.w<0:delta.negate()
            m=Matrix.LocRotScale(m.translation,Quaternion().slerp(delta,.78)@neutral[name].to_quaternion(),Vector((1,1,1)))
        if name.startswith('M66_Sac') or name.startswith('M66_Vent'):
            lag=math.sin(max(0,t-1.12)*15)*math.exp(-3.8*max(0,t-1.12))*smooth((t-.95)/.25)*(1-smooth((t-2.0)/.6))
            m=rotate(m,(0,0,1),(.025 if name.startswith('M66_Sac') else .04)*lag)
        worlds[name]=m
    return worlds

poses=[];geometry=[]
positions=np.array([v.co[:] for v in mesh.data.vertices],dtype=np.float64)
groups=[g.name for g in mesh.vertex_groups]
mass=np.array([sum(g.weight for g in v.groups if groups[g.group] in arm_names) for v in mesh.data.vertices])
hand_mass=np.array([sum(g.weight for g in v.groups if groups[g.group] in {wrist,*hand_children}) for v in mesh.data.vertices])
# The torso envelope closes the mouth cavity, so a path through it is never accepted.
body=positions[(mass<.03)&(positions[:,2]>1.0)&(positions[:,2]<3.62)]
profile=[]
for z in np.arange(1.1,3.61,.18):
    p=body[np.abs(body[:,2]-z)<.18]
    if len(p):
        lo,hi=np.percentile(p[:,:2],[.3,99.7],axis=0)
        profile.append([z,*((lo+hi)*.5),*((hi-lo)*.5+.055)])
profile=np.array(profile)
hand=positions[hand_mass>.65]
# Spatially distributed actual hand/finger surface samples, not just the wrist.
_,selected=np.unique(np.floor(hand/.14).astype(int),axis=0,return_index=True)
hand=hand[selected]
hand_local=np.array([tuple(neutral[wrist].inverted()@Vector(v)) for v in hand])
fractions=np.array([.45,.72,1.]);forearm=np.array([.2,.45,.7,1.])
radii=np.r_[np.full(len(fractions),.18),np.full(len(forearm),.22),np.full(len(hand),.045)]
for frame in range(COUNT):
    t=frame/FPS;src=sample(source_time(t));active=smooth(t/.48)*(1-smooth((t-2.20)/.4))
    worlds=body_pose(src,t,active)
    us,ls,ns=arm_frame(src);sfu,sfl=basis(us,ns),basis(ls,ns)
    alignment=align0.slerp(Quaternion(),active)
    ud=alignment@us;normal=alignment@ns
    bend=us.angle(ls)+(u0.angle(l0)-su0.angle(sl0))*(1-active)
    bend=max(math.radians(8),min(math.radians(112),bend))
    ld=Quaternion(normal,bend)@ud
    uf,lf=basis(ud,normal),basis(ld,normal)
    uq=uf@tu0.inverted()@neutral[upper].to_quaternion()
    lq=lf@tl0.inverted()@neutral[lower].to_quaternion()
    hq=lf@(sfl.inverted()@src['hand_r'][1])@(sfl0.inverted()@ref['hand_r'][1]).inverted()@tl0.inverted()@neutral[wrist].to_quaternion()
    shoulder=worlds[upper].translation.copy();elbow=shoulder+ud*a;hand_origin=elbow+ld*b
    points=np.vstack([np.array(shoulder)+fractions[:,None]*np.array(ud*a),
                      np.array(elbow)+forearm[:,None]*np.array(ld*b),
                      hand_local@np.array(hq.to_matrix()).T+np.array(hand_origin)])
    body_delta=worlds['Bone_005']@neutral['Bone_005'].inverted()
    poses.append((worlds,shoulder,elbow,hand_origin,uq,lq,hq,body_delta))
    geometry.append(points-np.array(shoulder))
geometry=np.array(geometry);shoulders=np.array([list(p[1]) for p in poses])
body_inverse=np.array([list(map(list,p[7].inverted())) for p in poses])

# Offline shoulder-only fitting preserves the donor elbow/wrist relationship.
# Smooth correction curves move the whole arm around the torso and never shorten it.
knots=np.array([0,.24,.70,1.,1.2,1.4,1.7,2.05,2.35,2.6]);times=np.arange(COUNT)/FPS
weights=np.zeros((COUNT,len(knots)))
for i,t in enumerate(times):
    j=min(len(knots)-2,max(0,int(np.searchsorted(knots,t,side='right')-1)))
    f=smooth((t-knots[j])/(knots[j+1]-knots[j]));weights[i,j]=1-f;weights[i,j+1]=f
def corrected_points(params):
    angles=weights@params;ya,pi=angles[:,0],angles[:,1]
    cy,sy,cp,sp=np.cos(ya),np.sin(ya),np.cos(pi),np.sin(pi)
    rot=np.zeros((COUNT,3,3))
    rot[:,0,0]=cy;rot[:,0,1]=-sy*cp;rot[:,0,2]=sy*sp
    rot[:,1,0]=sy;rot[:,1,1]=cy*cp;rot[:,1,2]=-cy*sp
    rot[:,2,1]=sp;rot[:,2,2]=cp
    points=np.einsum('fij,fpj->fpi',rot,geometry)+shoulders[:,None,:]
    return points,angles
def objective(params,details=False):
    points,angles=corrected_points(params)
    local_points=np.einsum('fij,fpj->fpi',body_inverse[:,:3,:3],points)+body_inverse[:,:3,3][:,None,:]
    z=local_points[:,:,2];fields=[np.interp(z,profile[:,0],profile[:,i]) for i in range(1,5)]
    cx,cy,rx,ry=fields;rx=rx+radii;ry=ry+radii
    q=((local_points[:,:,0]-cx)/rx)**2+((local_points[:,:,1]-cy)/ry)**2
    penetration=np.maximum(0,1-np.sqrt(q))*np.minimum(rx,ry)
    penetration[(z<1.)|(z>3.65)]=0
    floor=np.maximum(0,.045-points[:,:,2])
    # Attachment overlap in the original pose is not an animation error.
    baseline=penetration[0].copy()
    penetration=np.maximum(0,penetration-baseline[None,:])
    score=16000*np.sum(penetration**2)+10000*np.sum(np.max(penetration,axis=1)**2)+10000*np.sum(floor**2)
    score+=.08*np.sum(angles**2)+30*np.sum(np.diff(angles,axis=0)**2)
    if details:return {'score':float(score),'torso_envelope_penetration_m':float(penetration.max()),
        'floor_penetration_m':float(floor.max()),'sampled_hand_points':len(hand),
        'yaw_pitch_knots_degrees':np.rad2deg(params).tolist()}
    return score
params=np.deg2rad(np.array([[0,0],[0,0],[-10,0],[-20,-5],[-30,-5],[-35,-5],[-35,0],[-20,0],[0,0],[0,0]],float))
for step_degrees in (18,9,4.5,2.25,1.):
    step=math.radians(step_degrees)
    for iteration in range(5):
        changed=False
        for index in range(1,len(knots)-1):
            for axis in range(2):
                best=objective(params);choice=params[index,axis]
                for direction in (-1,1):
                    candidate=params.copy();candidate[index,axis]+=direction*step
                    if abs(candidate[index,axis])>math.radians(95 if axis==0 else 65):continue
                    score=objective(candidate)
                    if score<best-1e-6:best=score;choice=candidate[index,axis];changed=True
                params[index,axis]=choice
        if not changed:break
print('M66_ARM_FIT '+json.dumps(objective(params,True)),flush=True)

action=bpy.data.actions.new('A_M66_ClawSweep_V06');action.use_fake_user=True
rig.animation_data.action=action;scene.frame_start=0;scene.frame_end=COUNT-1
previous={};_,angles=corrected_points(params);path=[]
for frame,(worlds,shoulder,elbow,hand_origin,uq,lq,hq,_) in enumerate(poses):
    scene.frame_set(frame);yaw,pitch=angles[frame]
    adjust=Quaternion((0,0,1),yaw)@Quaternion((1,0,0),pitch)
    elbow=shoulder+adjust@(elbow-shoulder);hand_origin=shoulder+adjust@(hand_origin-shoulder)
    uq,lq,hq=adjust@uq,adjust@lq,adjust@hq
    worlds[upper]=Matrix.LocRotScale(shoulder,uq,Vector((1,1,1)))
    worlds[lower]=Matrix.LocRotScale(elbow,lq,Vector((1,1,1)))
    lower_delta=worlds[lower]@neutral[lower].inverted()
    for name in bridge:worlds[name]=lower_delta@neutral[name]
    worlds[wrist]=Matrix.LocRotScale(hand_origin,hq,Vector((1,1,1)))
    for name in hand_children:worlds[name]=worlds[parents[name]]@nlocal[name]
    solve_planted_legs(worlds);apply_worlds(worlds)
    for pb in rig.pose.bones:
        q=pb.rotation_quaternion.copy()
        if pb.name in previous and q.dot(previous[pb.name])<0:q.negate()
        pb.rotation_quaternion=q;previous[pb.name]=q.copy()
        for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame,group=pb.name)
    path.append({'time':frame/FPS,'shoulder':list(shoulder),'elbow':list(elbow),'wrist':list(hand_origin)})
if action.slots:rig.animation_data.action_slot=action.slots[0]
for layer in action.layers:
    for strip in layer.strips:
        bag=strip.channelbag(action.slots[0])
        for curve in bag.fcurves:
            for key in curve.keyframe_points:key.interpolation='LINEAR'
action['M66_source']='Epic Rampage Attack_Biped_Melee_A, retained Hundred-Eyed Slag sweep reference; M66 anatomical arm adaptation'
action['contact_start']=1.;action['contact_end']=1.35;action['loop']=False
scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
destination=ROOT/'Export/A_M66_ClawSweep_V06.fbx'
bpy.ops.export_scene.fbx(filepath=str(destination),use_selection=True,object_types={'ARMATURE','MESH'},
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
    bake_anim_step=1.,bake_anim_simplify_factor=0.,use_mesh_modifiers=False,axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/M66_claw_sweep_v06.blend'))
manifest={'source':str(SOURCE),'donor':str(DONOR),'authoring':str(ROOT/'Authoring/M66_claw_sweep_v06.blend'),
 'clips':[{'role':'ClawSweep','action':action.name,'fbx':str(destination),'seconds':DURATION,'fps':FPS,'frames':COUNT,'loop':False}],
 'contact_start_seconds':1.,'contact_end_seconds':1.35,'bones':len(rest),'arm_chain':[upper,lower,wrist],
 'intermediate_forearm_bones':list(bridge),'upper_length_m':a,'forearm_length_m':b,
 'mesh_modified':False,'runtime_tested':False,'rendered':False,'root_motion':False,
 'source_time_mapping':time_pairs.tolist(),'shoulder_fit':objective(params,True)}
(ROOT/'Records/animation_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(ROOT/'Records/authored_joint_path.json').write_text(json.dumps(path,indent=2),encoding='utf-8')
print('M66_CLAW_SWEEP_V06_AUTHORED',flush=True)
