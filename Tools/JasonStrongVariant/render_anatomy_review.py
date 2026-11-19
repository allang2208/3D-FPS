"""Offline joint review using saved UE vertices, bind matrices and LBS weights.

Controlled joint poses only; this does not evaluate an Unreal Animation Blueprint
or its pose-driver correctives. Original and derived use the same joint angles.
"""
import bpy,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector

OUT=Path(globals().get('review_output','D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117/R2_LongLegs'))
REVIEW=Path(globals().get('review_folder',OUT/'AnatomyReview'))
datasets=globals().get('review_datasets')
if datasets is None:datasets=[json.loads((REVIEW/(n+'_saved_mesh.json')).read_text()) for n in ['original','derived']]
head=json.loads((OUT/'head_source.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=globals().get('review_width',1600);scene.render.resolution_y=globals().get('review_height',1200);scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.11,.13,.17,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
scene.view_settings.view_transform='AgX'

def material(name,color,rough=.7):
    m=bpy.data.materials.new(name);m.use_nodes=True
    n=m.node_tree.nodes;n.clear();bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough
    m.node_tree.links.new(bs.outputs[0],out.inputs[0]);return m
clay=material('Neutral anatomy clay',(.35,.40,.44))
floor_mat=material('Review floor',(.055,.067,.085))
joint_mat=material('Joint centers',(.05,.65,.9),.4)

def mesh(name,data,positions):
    me=bpy.data.meshes.new(name);me.from_pydata((np.array(positions)*.01).tolist(),[],data['triangles']);me.update()
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);me.materials.append(clay)
    for poly in me.polygons:poly.use_smooth=True
    return ob
objects=[]
for i,data in enumerate(datasets):
    body=mesh(['Original','StrongTall_R2_refined'][i],data,data['positions'])
    face=mesh(['Original_head','Original_head_on_R2'][i],head,head['positions'])
    spacing=globals().get('review_spacing',.64)
    body.location.x=face.location.x=spacing if i==0 else -spacing
    objects.append((body,face))

bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.004));bpy.context.object.data.materials.append(floor_mat)
for name,loc,power,size in [('Key',(-3,4,4),650,3),('Fill',(3,2,3),400,3),('Rim',(0,-3,3),700,3)]:
    li=bpy.data.lights.new(name,'AREA');li.energy=power;li.size=size
    ob=bpy.data.objects.new(name,li);scene.collection.objects.link(ob);ob.location=loc
    ob.rotation_euler=(Vector((0,0,1))-ob.location).to_track_quat('-Z','Y').to_euler()
ca=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',ca);scene.collection.objects.link(cam);scene.camera=cam
ca.type='ORTHO'

def rotation(axis,degrees):
    a=np.array(axis,dtype=float);a/=np.linalg.norm(a);x,y,z=a
    k=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    t=math.radians(degrees)
    return np.eye(3)+math.sin(t)*k+(1-math.cos(t))*(k@k)

def elbow_axis(data,side):
    bones={x['name']:np.array(x['position']) for x in data['bones']}
    u=bones['lowerarm_'+side]-bones['upperarm_'+side]
    v=bones['hand_'+side]-bones['lowerarm_'+side]
    return np.cross(u,v)

def pose(data,kind):
    bones=data['bones'];n=len(bones)
    bind=np.repeat(np.eye(4)[None,:,:],n,axis=0)
    for i,b in enumerate(bones):bind[i,:3,:3]=np.array(b['axes']).T;bind[i,:3,3]=b['position']
    inv=np.linalg.inv(bind)
    commands={}
    if kind in ['elbows','squat','raised_elbows']:
        for side,sign in [('l',1),('r',-1)]:
            commands['upperarm_'+side]=([0,1,0],25*sign)
            commands['lowerarm_'+side]=(elbow_axis(data,side),50)
    if kind in ['shoulders','raised_elbows']:
        for side,sign in [('l',1),('r',-1)]:
            commands['clavicle_'+side]=([0,1,0],-8*sign)
            commands['upperarm_'+side]=([0,1,0],-42*sign)
    if kind=='shoulders_high':
        for side,sign in [('l',1),('r',-1)]:
            commands['clavicle_'+side]=([0,1,0],-15*sign)
            commands['upperarm_'+side]=([0,1,0],-65*sign)
    if kind=='leg':
        commands.update(thigh_l=([1,0,0],65),calf_l=([1,0,0],-95),foot_l=([1,0,0],30))
    if kind=='squat':
        for side in ['l','r']:
            commands['thigh_'+side]=([1,0,0],55)
            commands['calf_'+side]=([1,0,0],-95)
            commands['foot_'+side]=([1,0,0],40)
    posed=bind.copy()
    for i,b in enumerate(bones):
        parent=b['parent'];local=inv[parent]@bind[i] if parent>=0 else bind[i].copy()
        if b['name'] in commands:
            axis,degrees=commands[b['name']]
            delta=np.eye(4);delta[:3,:3]=rotation(bind[i,:3,:3].T@axis,degrees)
            local=local@delta
        posed[i]=posed[parent]@local if parent>=0 else local
    native_sample=globals().get('review_sample_poses',{}).get(kind)
    if native_sample is not None:posed=np.array(native_sample)
    skin=posed@inv
    def skin_points(positions,weights):
        p=np.c_[np.array(positions),np.ones(len(positions))]
        q=np.zeros((len(p),3))
        for col in range(max(map(len,weights))):
            ids=np.array([i for i,ws in enumerate(weights) if len(ws)>col])
            bis=np.array([weights[i][col][0] for i in ids]);ws=np.array([weights[i][col][1] for i in ids])
            q[ids]+=np.einsum('ijk,ik->ij',skin[bis,:3,:],p[ids])*ws[:,None]
        return q
    review_positions=data['positions']
    pose_weights={}
    if 'review_apply_forms' in globals():
        review_positions,pose_weights=review_apply_forms(data,bind,posed)
    q=skin_points(review_positions,data['weights'])
    dz=-.3-float(q[:,2].min()) if kind=='squat' else 0
    q[:,2]+=dz;posed[:,2,3]+=dz
    heads=np.array(head['positions']);heads[:,2]+=data.get('head_z_cm',4.5 if data is datasets[1] else 0)
    body_names={b['name']:i for i,b in enumerate(bones)}
    head_map={}
    for b in head['bones']:
        ancestor=b
        while ancestor['name'] not in body_names and ancestor['parent']>=0:
            ancestor=head['bones'][ancestor['parent']]
        head_map[b['index']]=body_names[ancestor['name']]
    head_weights=[]
    for ws in head['weights']:
        mapped={}
        for i,w in ws:mapped[head_map[i]]=mapped.get(head_map[i],0)+w
        head_weights.append(list(mapped.items()))
    heads=skin_points(heads,head_weights);heads[:,2]+=dz
    det=np.linalg.det(posed[:,:3,:3])
    return q,heads,posed,{'posed_basis_determinant_min':float(det.min()),'posed_basis_determinant_max':float(det.max()),'finite_mesh':bool(np.isfinite(q).all()),'joint_rotations_degrees':{k:float(v[1]) for k,v in commands.items()},'corrective_weights':pose_weights}

report={'method':globals().get('review_method','Saved UE LOD0 vertices, reference matrices and native weights; offline linear blend skinning. No animation blueprint or corrective pose drivers.'), 'comparisons':[]}
shots=globals().get('review_shots',[('01_rest_front','rest',0,2.8,.88),('02_rest_back','rest',180,2.8,.88),('03_elbows','elbows',-30,2.8,.88),('04_shoulders','shoulders',0,3.05,.86),('05_hip_knee','leg',-80,2.8,.88),('06_squat','squat',-65,2.8,.72)])
for filename,kind,angle,scale,height in shots:
    entry={'image':filename+'.png','pose':kind,'variants':[]}
    for data,(body,face) in zip(datasets,objects):
        p,h,posed,stats=pose(data,kind)
        body.data.vertices.foreach_set('co',(p*.01).ravel());body.data.update()
        face.data.vertices.foreach_set('co',(h*.01).ravel());face.data.update()
        for ob in [body,face]:ob.rotation_euler.z=math.radians(angle)
        stats['joint_centers_cm']={b['name']:posed[i,:3,3].tolist() for i,b in enumerate(data['bones']) if b['name'] in ['upperarm_l','lowerarm_l','hand_l','thigh_l','calf_l','foot_l']}
        entry['variants'].append(stats)
    ca.ortho_scale=scale;cam.location=(0,6,height+.05)
    cam.rotation_euler=(Vector((0,0,height))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(REVIEW/(filename+'.png'))
    bpy.ops.render.render(write_still=True)
    report['comparisons'].append(entry)
    print('JASON_POSE_RENDERED '+filename,flush=True)
(REVIEW/'pose_review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
# Deliver the diagnostic scene in the final knee pose, independent of the asset source.
bpy.ops.wm.save_as_mainfile(filepath=str(REVIEW/'Jason_AnatomyReview.blend'))
print('JASON_ANATOMY_POSE_REVIEW_COMPLETE',flush=True)
