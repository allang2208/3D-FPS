"""Close the native giant hand, then fit the existing slam to its fist surface."""
import ast,bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'FistSlamV14'
for d in ('Authoring','Export','Records'):(ROOT/d).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'GroundSlamV13/Authoring/M66_ground_slam_v13.blend'))
rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body'];scene=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local={n:rest[parents[n]].inverted()@m if parents[n] else m.copy() for n,m in rest.items()}
def depth(n):return depth(parents[n])+1 if parents[n] else 0
ordered=sorted(rest,key=depth)
def below(n,root):
    while n:
        if n==root:return True
        n=parents[n]
    return False
def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)
def frame_axis(direction,dorsal):
    y=direction.normalized();z=(dorsal-y*dorsal.dot(y)).normalized()
    return Matrix((y.cross(z),y,z)).transposed()

FPS=60;COUNT=211;wrist='Bone_037';upper='Bone_027';lower='Bone_026'
source=[]
for f in range(COUNT):
    scene.frame_set(f);bpy.context.view_layer.update()
    source.append({n:rig.pose.bones[n].matrix.copy() for n in ordered})
neutral=source[0];nlocal={n:neutral[parents[n]].inverted()@m if parents[n] else m.copy() for n,m in neutral.items()}
chains=[('L','Bone_012','Bone_011','Bone_010'),('R','Bone_017','Bone_016','Bone_015')]
base_feet={side:neutral[foot].translation.copy() for side,_,_,foot in chains}
for node in ast.parse((BASE/'ReactionsV03/author_reactions.py').read_text(encoding='utf-8')).body:
    if isinstance(node,ast.FunctionDef) and node.name in {'apply_worlds','solve_planted_legs'}:
        exec(compile(ast.Module(body=[node],type_ignores=[]),'M66_existing_support','exec'))

# The profile is expressed in palm directions, never copied as local Euler.
profile_path=Path('D:/FPS3D/FPSGAME/SourceAssets/StaffQuickCombat20261001/FixV2/fist-profile-v2.json')
profile=json.loads(profile_path.read_text(encoding='utf-8-sig'))
digits={'thumb':57,'index':65,'middle':73,'ring':69,'pinky':61}
origin=rest[wrist].translation
forward=(rest['Bone_073'].translation-origin).normalized()
radial=rest['Bone_065'].translation-rest['Bone_061'].translation
radial=(radial-forward*radial.dot(forward)).normalized();dorsal=forward.cross(radial).normalized()
closed={n:m.copy() for n,m in rest.items()}
for n in ordered:
    if not below(n,wrist):continue
    m=closed[parents[n]]@local[n]
    digit=next((d for d,r in digits.items() if int(n[-3:]) in range(r-3,r+1)),None) if n.startswith('Bone_') else None
    if digit:
        k=digits[digit]-int(n[-3:]);p=profile[digit];j=min(k,2)
        spread=math.radians(p['spread'][j]);flex=math.radians(p['flex'][j])
        direction=forward*math.cos(spread)-radial*math.sin(spread)
        # Positive flex moves the native phalanx toward the palm.
        axis=dorsal.cross(direction).normalized();direction=Quaternion(axis,flex)@direction
        bd=rig.data.bones[n].tail_local-rig.data.bones[n].head_local
        target_dorsal=Quaternion(axis,flex)@dorsal
        if digit=='thumb':target_dorsal=dorsal+radial*(.55,.18,0.,0.)[k]
        rotation=frame_axis(direction,target_dorsal)@frame_axis(bd,dorsal).inverted()@rest[n].to_3x3()
        m=rotation.to_4x4();m.translation=(closed[parents[n]]@local[n]).translation
    closed[n]=m
closed_local={n:closed[parents[n]].inverted()@closed[n] for n in ordered if below(n,wrist) and n!=wrist}
finger_names={f'Bone_{i:03d}' for r in digits.values() for i in range(r-3,r+1)}

def close_hand(worlds,t):
    # Fingers collect during the lift; the thumb closes last on the exterior.
    for n in ordered:
        if n not in finger_names:continue
        is_thumb=54<=int(n[-3:])<=57
        start,end=(.42,1.10) if is_thumb else (.20,.88)
        weight=smooth((t-start)/(end-start))*(1-smooth((t-2.35)/.90))
        a=nlocal[n];b=closed_local[n]
        rel=Matrix.LocRotScale(a.translation,a.to_quaternion().slerp(b.to_quaternion(),weight),a.to_scale())
        worlds[n]=worlds[parents[n]]@rel

positions=np.array([v.co[:] for v in mesh.data.vertices]);groupnames=[g.name for g in mesh.vertex_groups]
hand_names={n for n in ordered if below(n,wrist)}
hand_ids=np.array([v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if groupnames[g.group] in hand_names)>.70])
# Voxel-reduce only the fitting samples; the actual mesh is unchanged.
_,take=np.unique(np.floor(positions[hand_ids]/.035).astype(int),axis=0,return_index=True)
sample_ids=hand_ids[take];bone_index={n:i for i,n in enumerate(ordered)}
indices=np.zeros((len(sample_ids),8),int);amounts=np.zeros((len(sample_ids),8))
for k,i in enumerate(sample_ids):
    weights=[(bone_index[groupnames[g.group]],g.weight) for g in mesh.data.vertices[int(i)].groups if groupnames[g.group] in bone_index]
    for j,(n,w) in enumerate(sorted(weights,key=lambda p:-p[1])[:8]):indices[k,j]=n;amounts[k,j]=w
amounts/=amounts.sum(1)[:,None];inverse=np.array([list(map(list,rest[n].inverted())) for n in ordered])
homogeneous=np.column_stack((positions[sample_ids],np.ones(len(sample_ids))))
def skin(worlds):
    matrices=np.array([list(map(list,worlds[n])) for n in ordered])@inverse
    return np.sum(np.einsum('vkij,vj->vki',matrices[indices],homogeneous)*amounts[:,:,None],axis=1)[:,:3]

arm_names={n for n in ordered if below(n,upper)}
armmass=np.array([sum(g.weight for g in v.groups if groupnames[g.group] in arm_names) for v in mesh.data.vertices])
body=positions[(armmass<.03)&(positions[:,2]>1.)&(positions[:,2]<3.65)];profile_body=[]
for z in np.arange(1.1,3.61,.18):
    p=body[np.abs(body[:,2]-z)<.18]
    if len(p):
        lo,hi=np.percentile(p[:,:2],[.3,99.7],axis=0);profile_body.append([z,*((lo+hi)*.5),*((hi-lo)*.5+.035)])
profile_body=np.array(profile_body)
poses=[];hand_surface=[]
for f,base in enumerate(source):
    worlds={n:m.copy() for n,m in base.items()};close_hand(worlds,f/FPS)
    poses.append(worlds);hand_surface.append(skin(worlds))
hand_surface=np.array(hand_surface);shoulders=np.array([w[upper].translation[:] for w in poses])
geometry=hand_surface-shoulders[:,None,:]
body_inv=np.array([list(map(list,(w['Bone_005']@rest['Bone_005'].inverted()).inverted())) for w in poses])
times=np.arange(COUNT)/FPS;knots=np.array([0,.6,1.1,1.35,1.5,1.63,1.78,2.1,2.6,3.1,3.5]);weights=np.zeros((COUNT,len(knots)))
for i,t in enumerate(times):
    j=min(len(knots)-2,max(0,int(np.searchsorted(knots,t,side='right')-1)));v=smooth((t-knots[j])/(knots[j+1]-knots[j]));weights[i,j]=1-v;weights[i,j+1]=v
def corrected(params):
    values=weights@params;ya,pi,drop=values.T;cy,sy,cp,sp=np.cos(ya),np.sin(ya),np.cos(pi),np.sin(pi)
    rot=np.zeros((COUNT,3,3));rot[:,0,0]=cy;rot[:,0,1]=-sy*cp;rot[:,0,2]=sy*sp;rot[:,1,0]=sy;rot[:,1,1]=cy*cp;rot[:,1,2]=-cy*sp;rot[:,2,1]=sp;rot[:,2,2]=cp
    p=np.einsum('fij,fpj->fpi',rot,geometry)+shoulders[:,None,:];p[:,:,2]-=drop[:,None]
    return p,values
def score(params):
    p,values=corrected(params);recenter=p.copy();recenter[:,:,2]+=values[:,2,None]
    q=np.einsum('fij,fpj->fpi',body_inv[:,:3,:3],recenter)+body_inv[:,:3,3][:,None,:];z=q[:,:,2]
    cx,cy,rx,ry=[np.interp(z,profile_body[:,0],profile_body[:,i]) for i in range(1,5)]
    penetration=np.maximum(0,1-np.sqrt(((q[:,:,0]-cx)/(rx+.025))**2+((q[:,:,1]-cy)/(ry+.025))**2))*np.minimum(rx,ry)
    penetration[(z<1)|(z>3.65)]=0
    contact=(times>=1.59)&(times<=1.66)
    return float(18000*np.sum(penetration**2)+35000*np.sum(np.maximum(0,.025-p[:,:,2])**2)
        +45000*np.sum((p[contact,:,2].min(1)-.045)**2)+12*np.sum(values[:,:2]**2)
        +180*np.sum(np.diff(values[:,:2],axis=0)**2)+180*np.sum(values[:,2]**2)+350*np.sum(np.diff(values[:,2])**2))
params=np.zeros((len(knots),3))
for astep,dstep in ((12,.06),(6,.03),(3,.015),(1.5,.0075)):
    for repeat in range(3):
        changed=False
        for i in range(1,len(knots)-1):
            for axis in range(3):
                if axis==2 and not 1.35<=knots[i]<=2.1:continue
                step=dstep if axis==2 else math.radians(astep);best=score(params);choice=params[i,axis]
                for sign in (-1,1):
                    test=params.copy();test[i,axis]+=step*sign
                    if axis==2 and not 0<=test[i,axis]<=.30:continue
                    if axis<2 and abs(test[i,axis])>math.radians(36):continue
                    v=score(test)
                    if v<best-1e-5:best=v;choice=test[i,axis];changed=True
                params[i,axis]=choice
        if not changed:break
surface,values=corrected(params)
action=bpy.data.actions.new('A_M66_FistSlam_V14');action.use_fake_user=True;rig.animation_data.action=action
scene.frame_start=0;scene.frame_end=COUNT-1;previous={};path=[]
for f,worlds in enumerate(poses):
    scene.frame_set(f);yaw,pitch,drop=values[f];q=Quaternion((0,0,1),yaw)@Quaternion((1,0,0),pitch);pivot=worlds[upper].translation.copy()
    for n in ordered:
        if n in arm_names:
            m=worlds[n];worlds[n]=Matrix.LocRotScale(pivot+q@(m.translation-pivot),q@m.to_quaternion(),m.to_scale())
        if below(n,'Bone_000'):worlds[n].translation.z-=drop
    solve_planted_legs(worlds);apply_worlds(worlds)
    for pb in rig.pose.bones:
        q=pb.rotation_quaternion.copy()
        if pb.name in previous and q.dot(previous[pb.name])<0:q.negate()
        pb.rotation_quaternion=q;previous[pb.name]=q.copy()
        for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=f,group=pb.name)
    path.append({'time':f/FPS,'surface_min_z_m':float(surface[f,:,2].min()),'additional_crouch_m':float(drop)})
if action.slots:rig.animation_data.action_slot=action.slots[0]
for layer in action.layers:
    for strip in layer.strips:
        for curve in strip.channelbag(action.slots[0]).fcurves:
            for key in curve.keyframe_points:key.interpolation='LINEAR'

# Tight sphere cover of the actual closed fist, expressed in native wrist space.
# Same centres are used for eligibility and continuous server-side contact.
hold=96;worlds=poses[hold];localpoints=np.array([tuple(worlds[wrist].inverted()@Vector(p)) for p in skin(worlds)])
# Lloyd partition gives interior centres instead of expanded finger-end spheres.
centres=[localpoints.mean(0)]
for _ in range(23):
    dist=np.min(np.sum((localpoints[:,None,:]-np.array(centres)[None,:,:])**2,axis=2),axis=1)
    centres.append(localpoints[int(dist.argmax())])
centres=np.array(centres)
for _ in range(16):
    labels=np.argmin(np.sum((localpoints[:,None,:]-centres[None,:,:])**2,axis=2),axis=1)
    for j in range(len(centres)):
        if np.any(labels==j):centres[j]=localpoints[labels==j].mean(0)
cover=np.sqrt(np.min(np.sum((localpoints[:,None,:]-centres[None,:,:])**2,axis=2),axis=1)).max()
radius_cm=math.ceil((float(cover)+.015)*100)
reference_points=[list(rest[wrist]@Vector(p)) for p in centres]
contact={'source_reference_bones':{n:list(rest[n].translation) for n in (wrist,'Bone_036','Bone_065','Bone_061')},
    'reference_points_source_m':reference_points,'radius_cm':radius_cm,'centres':len(centres),
    'surface_cover_radius_cm':float(cover)*100,'method':'Closed skinned fist surface clustered into 24 interior spheres; 1.5 cm surface allowance',
    'contact_start':1.48,'contact_end':1.72}
(ROOT/'Records/fist_contact_definition.json').write_text(json.dumps(contact,indent=2))
action['M66_source']='V13 full-body slam plus native palm-frame closed fist; four-digit curl and exterior thumb'
action['contact_start']=1.48;action['contact_end']=1.72;action['loop']=False
scene.frame_set(0);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=ROOT/'Export/A_M66_FistSlam_V14.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
    bake_anim_step=1.,bake_anim_simplify_factor=0.,use_mesh_modifiers=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
authoring=ROOT/'Authoring/M66_fist_slam_v14.blend';bpy.ops.wm.save_as_mainfile(filepath=str(authoring))
manifest={'source':str(BASE/'GroundSlamV13/Authoring/M66_ground_slam_v13.blend'),'fist_profile_source':str(profile_path),'authoring':str(authoring),
    'clips':[{'role':'FistSlam','action':action.name,'fbx':str(fbx),'seconds':3.5,'fps':60,'frames':211,'loop':False}],
    'contact_start_seconds':1.48,'contact_end_seconds':1.72,'bones':len(rest),'mesh_modified':False,'weights_modified':False,
    'runtime_tested':False,'rendered':False,'finger_roots':digits,'correction_knots':knots.tolist(),'corrections':params.tolist()}
(ROOT/'Records/animation_manifest.json').write_text(json.dumps(manifest,indent=2))
(ROOT/'Records/authoring_path.json').write_text(json.dumps(path,indent=2))
print('M66_FIST_SLAM_AUTHORED '+json.dumps({'frames':211,'radius_cm':radius_cm,'centres':len(centres),'contact_surface':[p for p in path if 1.58<=p['time']<=1.68]}),flush=True)
