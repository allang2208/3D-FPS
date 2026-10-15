"""Full-chain Rampage ground-smash adaptation on the accepted V10 M66 skin."""
import ast,bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'GroundSlamV13'
for folder in ('Authoring','Export','Records'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
prefix=(BASE/'LocomotionV02/author_locomotion.py').read_text(encoding='utf-8').split('contracts=[]')[0]
prefix=prefix.replace("ROOT.parent/'MeshyRigV01/Authoring/M66_back_completed_v01.blend'","ROOT.parent/'ThumbDrapeV10/Authoring/M66_thumb_drape_v10.blend'")
exec(compile(prefix,'M66_existing_rig_setup','exec'));ROOT=BASE/'GroundSlamV13'
pose_frame('Idle',0.);bpy.context.view_layer.update()
neutral={n:rig.pose.bones[n].matrix.copy() for n in ordered}
nlocal={n:neutral[parents[n]].inverted()@neutral[n] if parents[n] else neutral[n].copy() for n in ordered}
base_feet={side:neutral[foot].translation.copy() for side,_,_,foot in chains}
for node in ast.parse((BASE/'ReactionsV03/author_reactions.py').read_text(encoding='utf-8')).body:
    if isinstance(node,ast.FunctionDef) and node.name in {'apply_worlds','solve_planted_legs'}:
        exec(compile(ast.Module(body=[node],type_ignores=[]),'M66_existing_support','exec'))

DURATION=3.5;FPS=60;COUNT=211
DONOR=Path('D:/FPS3D/FPSGAME/SourceAssets/HundredEyedSlagMeshy20260930/RampageReferenceIntake/source_motion')
C=Matrix.Diagonal((1.,-1.,1.));sources={}
for name in ('Idle','Ability_GroundSmash_Start','Ability_GroundSmash_End'):
    raw=json.loads((DONOR/(name+'.json')).read_text());frames=[]
    for row in raw['frames']:
        frame={}
        for n,value in row['component'].items():
            x,y,z,w=value['rotation_xyzw'];q=Quaternion((w,x,y,z))
            frame[n]=(C@Vector(value['translation_cm'])*.01,(C@q.to_matrix()@C).to_quaternion())
        frames.append(frame)
    sources[name]={'frames':frames,'seconds':raw['seconds']}
reference=sources['Idle']['frames'][0]

def mix(a,b,t):return {n:(p.lerp(b[n][0],t),q.slerp(b[n][1],t)) for n,(p,q) in a.items()}
def sample(name,t):
    src=sources[name];x=max(0.,min(src['seconds'],t))*60;i=min(len(src['frames'])-1,int(x));j=min(len(src['frames'])-1,i+1)
    return mix(src['frames'][i],src['frames'][j],x-i)
def source_pose(t):
    if t<.35:return mix(reference,sources['Ability_GroundSmash_Start']['frames'][0],smooth(t/.35))
    if t<1.25:return sample('Ability_GroundSmash_Start',smooth((t-.35)/.9)*sources['Ability_GroundSmash_Start']['seconds'])
    if t<1.35:return mix(sources['Ability_GroundSmash_Start']['frames'][-1],sources['Ability_GroundSmash_End']['frames'][0],smooth((t-1.25)/.1))
    if t<1.65:return sample('Ability_GroundSmash_End',.25*(t-1.35)/.3)
    if t<2.85:return sample('Ability_GroundSmash_End',.25+.45*smooth((t-1.65)/1.2))
    return mix(sources['Ability_GroundSmash_End']['frames'][-1],reference,smooth((t-2.85)/.65))
def below(name,ancestor):
    while parents[name]:
        name=parents[name]
        if name==ancestor:return True
    return False
upper,lower,wrist='Bone_027','Bone_026','Bone_037'
arm_names={n for n in ordered if n==upper or below(n,upper)}
hand_names={n for n in ordered if n==wrist or below(n,wrist)}
a=(neutral[lower].translation-neutral[upper].translation).length;b=(neutral[wrist].translation-neutral[lower].translation).length
u0=(neutral[lower].translation-neutral[upper].translation).normalized();l0=(neutral[wrist].translation-neutral[lower].translation).normalized();n0=u0.cross(l0).normalized()
def basis(direction,normal):
    direction=direction.normalized();normal=(normal-direction*normal.dot(direction)).normalized()
    return Matrix((direction,normal.cross(direction),normal)).transposed().to_quaternion()
def arm_frame(src):
    u=(src['lowerarm_r'][0]-src['upperarm_r'][0]).normalized();l=(src['hand_r'][0]-src['lowerarm_r'][0]).normalized()
    normal=u.cross(l)
    if normal.length<1e-5:normal=src['upperarm_r'][1]@reference['upperarm_r'][1].inverted()@sn0
    return u,l,normal.normalized()
tu0,tl0=basis(u0,n0),basis(l0,n0);su0,sl0,sn0=arm_frame(reference)
sfu0,sfl0=basis(su0,sn0),basis(sl0,sn0);align0=tu0@sfu0.inverted()
if align0.w<0:align0.negate()

def body_pose(src,t):
    mapping={'Bone_000':('pelvis',.45),'Bone_007':('spine_01',.58),'Bone_006':('spine_02',.72),'Bone_005':('spine_03',.78)}
    movement=(src['pelvis'][0]-reference['pelvis'][0])*.85
    compress=max(0.,reference['upperarm_r'][0].z-src['upperarm_r'][0].z)*.25
    movement=Vector((max(-.10,min(.10,movement.x)),max(-.16,min(.20,movement.y)),max(-.32,min(.10,movement.z-compress))))
    worlds={}
    for name in ordered:
        m=worlds[parents[name]]@nlocal[name] if parents[name] else nlocal[name].copy()
        if name=='Bone_000':m.translation+=movement
        if name in mapping:
            donor,factor=mapping[name];delta=src[donor][1]@reference[donor][1].inverted()
            if delta.w<0:delta.negate()
            m=Matrix.LocRotScale(m.translation,Quaternion().slerp(delta,factor)@neutral[name].to_quaternion(),neutral[name].to_scale())
        if name=='Bone_028':
            delta=src['clavicle_r'][1]@reference['clavicle_r'][1].inverted()
            if delta.w<0:delta.negate()
            m=Matrix.LocRotScale(m.translation,Quaternion().slerp(delta,.72)@neutral[name].to_quaternion(),Vector((1,1,1)))
        worlds[name]=m
    return worlds

positions=np.array([v.co[:] for v in mesh.data.vertices]);groups=[g.name for g in mesh.vertex_groups]
arm_mass=np.array([sum(g.weight for g in v.groups if groups[g.group] in arm_names) for v in mesh.data.vertices])
hand_mass=np.array([sum(g.weight for g in v.groups if groups[g.group] in hand_names) for v in mesh.data.vertices])
body=positions[(arm_mass<.03)&(positions[:,2]>1.)&(positions[:,2]<3.65)]
profile=[]
for z in np.arange(1.1,3.61,.18):
    p=body[np.abs(body[:,2]-z)<.18]
    if len(p):
        lo,hi=np.percentile(p[:,:2],[.3,99.7],axis=0);profile.append([z,*((lo+hi)*.5),*((hi-lo)*.5+.045)])
profile=np.array(profile)
hand=positions[hand_mass>.65];_,selected=np.unique(np.floor(hand/.13).astype(int),axis=0,return_index=True)
hand=hand[selected];hand_local=np.array([tuple(neutral[wrist].inverted()@Vector(p)) for p in hand])
fractions=np.array([.45,.72,1.]);forearm=np.array([.2,.45,.7,1.])
radii=np.r_[np.full(3,.17),np.full(4,.21),np.full(len(hand),.035)]
poses=[];geometry=[]
for frame in range(COUNT):
    t=frame/FPS;src=source_pose(t);active=smooth(t/.5)*(1-smooth((t-2.55)/.95));worlds=body_pose(src,t)
    us,ls,ns=arm_frame(src);sfl=basis(ls,ns);alignment=align0.slerp(Quaternion(),active)
    ud=alignment@us;normal=alignment@ns;bend=us.angle(ls)+(u0.angle(l0)-su0.angle(sl0))*(1-active)
    bend=max(math.radians(8),min(math.radians(112),bend));ld=Quaternion(normal,bend)@ud
    uf,lf=basis(ud,normal),basis(ld,normal)
    uq=uf@tu0.inverted()@neutral[upper].to_quaternion();lq=lf@tl0.inverted()@neutral[lower].to_quaternion()
    hq=lf@(sfl.inverted()@src['hand_r'][1])@(sfl0.inverted()@reference['hand_r'][1]).inverted()@tl0.inverted()@neutral[wrist].to_quaternion()
    shoulder=worlds[upper].translation.copy();elbow=shoulder+ud*a;w=elbow+ld*b
    points=np.vstack([np.array(shoulder)+fractions[:,None]*np.array(ud*a),np.array(elbow)+forearm[:,None]*np.array(ld*b),hand_local@np.array(hq.to_matrix()).T+np.array(w)])
    poses.append((worlds,shoulder,elbow,w,uq,lq,hq,worlds['Bone_005']@neutral['Bone_005'].inverted()));geometry.append(points-np.array(shoulder))
geometry=np.array(geometry);shoulders=np.array([list(p[1]) for p in poses]);body_inverse=np.array([list(map(list,p[7].inverted())) for p in poses])
times=np.arange(COUNT)/FPS;knots=np.array([0,.30,.65,1.05,1.35,1.52,1.63,1.85,2.30,2.80,3.15,3.5])
weights=np.zeros((COUNT,len(knots)))
for i,t in enumerate(times):
    j=min(len(knots)-2,max(0,int(np.searchsorted(knots,t,side='right')-1)));f=smooth((t-knots[j])/(knots[j+1]-knots[j]));weights[i,j]=1-f;weights[i,j+1]=f
def corrected(params):
    values=weights@params;ya,pi,drop=values.T;cy,sy,cp,sp=np.cos(ya),np.sin(ya),np.cos(pi),np.sin(pi)
    rot=np.zeros((COUNT,3,3));rot[:,0,0]=cy;rot[:,0,1]=-sy*cp;rot[:,0,2]=sy*sp;rot[:,1,0]=sy;rot[:,1,1]=cy*cp;rot[:,1,2]=-cy*sp;rot[:,2,1]=sp;rot[:,2,2]=cp
    p=np.einsum('fij,fpj->fpi',rot,geometry)+shoulders[:,None,:];p[:,:,2]-=drop[:,None]
    return p,values
def objective(params):
    p,values=corrected(params);recenter=p.copy();recenter[:,:,2]+=values[:,2,None]
    q=np.einsum('fij,fpj->fpi',body_inverse[:,:3,:3],recenter)+body_inverse[:,:3,3][:,None,:];z=q[:,:,2]
    cx,cy,rx,ry=[np.interp(z,profile[:,0],profile[:,i]) for i in range(1,5)];rx+=radii;ry+=radii
    penetration=np.maximum(0,1-np.sqrt(((q[:,:,0]-cx)/rx)**2+((q[:,:,1]-cy)/ry)**2))*np.minimum(rx,ry)
    penetration[(z<1.)|(z>3.65)]=0;penetration=np.maximum(0,penetration-penetration[0])
    floor=np.maximum(0,.025-p[:,:,2]);impact=(times>=1.57)&(times<=1.68)
    hand_floor=p[impact,7:,2].min(1)
    # Production fit: keep a real surface contact, with planted legs providing
    # the small extra crouch. No root translation or animated bone scaling.
    score=18000*np.sum(penetration**2)+30000*np.sum(floor**2)+45000*np.sum((hand_floor-.04)**2)
    score+=.12*np.sum(values[:,:2]**2)+28*np.sum(np.diff(values[:,:2],axis=0)**2)+45*np.sum(values[:,2]**2)
    score+=100*np.sum(np.diff(values[:,2])**2)
    return float(score)
params=np.zeros((len(knots),3));params[2:-2,0]=math.radians(-12)
for angle_step,drop_step in ((18,.10),(9,.05),(4.5,.025),(2.25,.0125)):
    for iteration in range(4):
        changed=False
        for i in range(1,len(knots)-1):
            for axis in range(3):
                if axis==2 and not 1.35<=knots[i]<=2.3:continue
                step=drop_step if axis==2 else math.radians(angle_step);best=objective(params);choice=params[i,axis]
                for sign in (-1,1):
                    candidate=params.copy();candidate[i,axis]+=sign*step
                    if axis==2 and not 0<=candidate[i,axis]<=.52:continue
                    if axis<2 and abs(candidate[i,axis])>math.radians(65):continue
                    score=objective(candidate)
                    if score<best-1e-6:best=score;choice=candidate[i,axis];changed=True
                params[i,axis]=choice
        if not changed:break
points,values=corrected(params)
action=bpy.data.actions.new('A_M66_GroundSlam_V13');action.use_fake_user=True;rig.animation_data.action=action
scene.frame_start=0;scene.frame_end=COUNT-1;previous={};path=[]
for frame,(worlds,s,e,w,uq,lq,hq,_) in enumerate(poses):
    scene.frame_set(frame);yaw,pitch,drop=values[frame];adjust=Quaternion((0,0,1),yaw)@Quaternion((1,0,0),pitch)
    e=s+adjust@(e-s);w=s+adjust@(w-s);uq,lq,hq=adjust@uq,adjust@lq,adjust@hq
    worlds[upper]=Matrix.LocRotScale(s,uq,Vector((1,1,1)));worlds[lower]=Matrix.LocRotScale(e,lq,Vector((1,1,1)))
    lower_delta=worlds[lower]@neutral[lower].inverted()
    for n in ('Bone_025','Bone_024'):worlds[n]=lower_delta@neutral[n]
    worlds[wrist]=Matrix.LocRotScale(w,hq,Vector((1,1,1)))
    # Include the full branch, including V08's repaired Bone_035/Bone_034.
    for n in ordered:
        if n in arm_names and n not in (upper,lower,'Bone_025','Bone_024',wrist):worlds[n]=worlds[parents[n]]@nlocal[n]
    for n in ordered:
        if n=='Bone_000' or below(n,'Bone_000'):worlds[n].translation.z-=drop
    solve_planted_legs(worlds);apply_worlds(worlds)
    for pb in rig.pose.bones:
        q=pb.rotation_quaternion.copy()
        if pb.name in previous and q.dot(previous[pb.name])<0:q.negate()
        pb.rotation_quaternion=q;previous[pb.name]=q.copy()
        for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame,group=pb.name)
    path.append({'time':frame/FPS,'wrist':list(worlds[wrist].translation),'hand_lowest':float(points[frame,7:,2].min())})
if action.slots:rig.animation_data.action_slot=action.slots[0]
for layer in action.layers:
    for strip in layer.strips:
        for curve in strip.channelbag(action.slots[0]).fcurves:
            for key in curve.keyframe_points:key.interpolation='LINEAR'
action['M66_source']='Epic Rampage GroundSmash Start + End, complete shoulder/elbow/wrist/body adaptation; accepted V10 skin retained'
action['contact_start']=1.48;action['contact_end']=1.72;action['loop']=False
scene.frame_set(0);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=ROOT/'Export/A_M66_GroundSlam_V13.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
    bake_anim_step=1.,bake_anim_simplify_factor=0.,use_mesh_modifiers=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
authoring=ROOT/'Authoring/M66_ground_slam_v13.blend';bpy.ops.wm.save_as_mainfile(filepath=str(authoring))
manifest={'source':str(BASE/'ThumbDrapeV10/Authoring/M66_thumb_drape_v10.blend'),'donor_directory':str(DONOR),'authoring':str(authoring),
    'clips':[{'role':'GroundSlam','action':action.name,'fbx':str(fbx),'seconds':DURATION,'fps':FPS,'frames':COUNT,'loop':False}],
    'contact_start_seconds':1.48,'contact_end_seconds':1.72,'bones':len(rest),'mesh_modified':False,'weights_modified':False,
    'runtime_tested':False,'rendered':False,'fitting_score':objective(params),'correction_knots':knots.tolist(),'corrections_yaw_pitch_radians_crouch_m':params.tolist()}
(ROOT/'Records/animation_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(ROOT/'Records/authoring_path.json').write_text(json.dumps(path,indent=2),encoding='utf-8')
print('M66_GROUND_SLAM_AUTHORED '+json.dumps({'frames':COUNT,'bones':len(rest),'contact':[p for p in path if 1.55<=p['time']<=1.7]}),flush=True)
