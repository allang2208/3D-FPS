"""Inspect copies in memory; never save/modify production rigs, clips or skin."""
import bpy,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
report={'read_only_production':True,'static':{},'motion':{},'isolated_joint_probes':{}}
def load(file):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if str(file).endswith('.blend'):bpy.ops.wm.open_mainfile(filepath=str(file))
    else:bpy.ops.import_scene.fbx(filepath=str(file),use_image_search=False)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    if rig.animation_data:
        for t in rig.animation_data.nla_tracks:t.mute=True
    return rig,meshes
def reset(rig):
    rig.animation_data_create();rig.animation_data.action=None
    for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
def active(rig,a):
    rig.animation_data_create();rig.animation_data.action=a
    if a.slots:rig.animation_data.action_slot=a.slots[0]
def coords(o,evaluated=False):
    obj=o.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else o
    m=obj.to_mesh() if evaluated else obj.data
    raw=np.array([list(v.co) for v in m.vertices],dtype=float)
    mat=np.array(obj.matrix_world,dtype=float)
    xyz=raw@mat[:3,:3].T+mat[:3,3]
    if evaluated:obj.to_mesh_clear()
    return xyz
def stat(a):
    a=np.asarray(a,dtype=float)
    return {k:float(v) for k,v in zip(['min','p05','median','p95','max'],np.percentile(a,[0,5,50,95,100]))} if a.size else None
def static(label,file):
    rig,meshes=load(file);reset(rig)
    row={'path':str(file),'bones':{},'meshes':[],'rig_world':list(map(list,rig.matrix_world))}
    for b in rig.data.bones:
        row['bones'][b.name]=dict(parent=b.parent.name if b.parent else None,
          head=list(rig.matrix_world@b.head_local),tail=list(rig.matrix_world@b.tail_local),deform=b.use_deform)
    for o in meshes:
        xyz=coords(o);posed=coords(o,True)
        weight_names={g.index:g.name for g in o.vertex_groups}
        sums=[];counts=[];cross=[];digest=hashlib.sha256();groups={}
        W={}
        for vertex,p in zip(o.data.vertices,xyz):
            pairs=sorted((weight_names[g.group],float(g.weight)) for g in vertex.groups if g.weight>1e-6)
            pairs=[(n,w) for n,w in pairs if n in rig.data.bones and rig.data.bones[n].use_deform]
            W[vertex.index]=dict(pairs);sums.append(sum(w for n,w in pairs));counts.append(len(pairs))
            digest.update(json.dumps(pairs,separators=(',',':')).encode())
            if abs(p[0])>.16:
                wrong='Right' if p[0]>0 else 'Left'
                w=sum(w for n,w in pairs if n.startswith(wrong))
                if w>.05:cross.append(dict(vertex=vertex.index,point=p.tolist(),weight=w))
            for n,w in pairs:groups.setdefault(n,[]).append((vertex.index,w))
        group_stats={}
        for n,pairs in groups.items():
            ids=np.array([i for i,w in pairs]);weights=np.array([w for i,w in pairs]);points=xyz[ids]
            group_stats[n]=dict(vertices=len(ids),weight_sum=float(weights.sum()),
                centroid=(np.sum(points*weights[:,None],axis=0)/weights.sum()).tolist(),
                min=points.min(axis=0).tolist(),max=points.max(axis=0).tolist())
        joints={}
        for n,upper in [('LeftLeg','LeftUpLeg'),('RightLeg','RightUpLeg'),('LeftForeArm','LeftArm'),('RightForeArm','RightArm')]:
            joint=np.array(rig.matrix_world@rig.data.bones[n].head_local)
            ids=np.where(np.linalg.norm(xyz-joint,axis=1)<.08)[0]
            blended=sum(W[int(i)].get(n,0)>.05 and W[int(i)].get(upper,0)>.05 for i in ids)
            joints[n]=dict(near_vertices=len(ids),shared_upper_lower_gt05=int(blended),
                fraction=float(blended/max(1,len(ids))))
        o.data.calc_loop_triangles()
        row['meshes'].append(dict(name=o.name,vertices=len(xyz),triangles=len(o.data.loop_triangles),
            world=list(map(list,o.matrix_world)),bounds=[xyz.min(axis=0).tolist(),xyz.max(axis=0).tolist()],
            modifiers=[dict(type=m.type,target=m.object.name if m.type=='ARMATURE' and m.object else None) for m in o.modifiers],
            rest_deformation_metres=stat(np.linalg.norm(posed-xyz,axis=1)),
            weights_sha256=digest.hexdigest(),weight_sum=stat(sums),
            zero_weight_vertices=sum(s<1e-6 for s in sums),non_normalized_vertices=sum(abs(s-1)>.001 for s in sums),
            influence_histogram={str(n):counts.count(n) for n in sorted(set(counts))},
            opposite_side_vertices=len(cross),opposite_side_examples=cross[:8],groups=group_stats,joint_blends=joints))
    report['static'][label]=row
    print('STATIC_DONE',label,flush=True)
    return rig,meshes

rig,meshes=static('original_meshy',BASE/'Meshy/rig/downloads/result_rigged_character_fbx_url.fbx')
# Isolated controlled deformations separate skin quality from source animation.
for name,degrees in [('LeftForeArm',90),('LeftLeg',90),('LeftArm',60)]:
    reset(rig);b=rig.pose.bones[name];m=rig.matrix_world@b.matrix
    axis=Vector((1,0,0)) if name!='LeftArm' else Vector((0,1,0))
    joint=np.array(m.translation);before=[coords(o) for o in meshes]
    b.matrix=rig.matrix_world.inverted()@Matrix.LocRotScale(m.translation,Quaternion(axis,math.radians(degrees))@m.to_quaternion(),m.to_scale())
    bpy.context.view_layer.update();rows=[]
    for o,raw in zip(meshes,before):
        posed=coords(o,True);ids=np.where(np.linalg.norm(raw-joint,axis=1)<.12)[0]
        ratios=[]
        for e in o.data.edges:
            a,c=e.vertices
            if np.linalg.norm((raw[a]+raw[c])*.5-joint)>.12:continue
            length=np.linalg.norm(raw[a]-raw[c])
            if length>1e-6:ratios.append(np.linalg.norm(posed[a]-posed[c])/length)
        rows.append(dict(mesh=o.name,region_vertices=len(ids),edge_length_ratio=stat(ratios)))
    report['isolated_joint_probes'][name]=dict(degrees=degrees,meshes=rows)
static('prepared',BASE/'SpitterZombie_Meshy_Source.blend')
static('v7_working_skin',BASE/'LibraryMotionV7/SpitterZombie_LibraryMotionV7.blend')

target_names=['Hips','Spine02','Spine','neck','Head','LeftArm','LeftForeArm','LeftHand','RightArm','RightForeArm','RightHand',
 'LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase']
source_names=['pelvis','spine_01','spine_05','neck_01','head','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r',
 'thigh_l','calf_l','foot_l','ball_l','thigh_r','calf_r','foot_r','ball_r']
def motion(label,file,action_name=None,source=False,skin=False):
    rig,meshes=load(file);scene=bpy.context.scene
    a=bpy.data.actions[action_name] if action_name else rig.animation_data.action
    active(rig,a);rate=scene.render.fps/scene.render.fps_base;first,last=a.frame_range
    seconds=(last-first)/rate;names=source_names if source else target_names
    times=np.linspace(0,seconds,61);rows=[]
    for t in times:
        f=first+t*rate;scene.frame_set(math.floor(f),subframe=f%1);bpy.context.view_layer.update()
        row=dict(t=float(t),bones={})
        for n in names:
            if n not in rig.pose.bones:continue
            b=rig.pose.bones[n];m=rig.matrix_world@b.matrix
            row['bones'][n]=dict(p=list(m.translation),q=list(m.to_quaternion()),scale=list(m.to_scale()),
                local_q=list(b.matrix_basis.to_quaternion()))
        if skin:
            low=min(float(coords(o,True)[:,2].min()) for o in meshes)
            row['skin_floor_m']=low
        rows.append(row)
    report['motion'][label]=dict(file=str(file),action=a.name,seconds=seconds,fps=rate,frames=rows)
    print('MOTION_DONE',label,seconds,flush=True)
motion('meshy_builtin_walk',BASE/'Meshy/rig/downloads/result_basic_animations_walking_fbx_url.fbx',skin=True)
for role in ['Walk_A','Walk_B','Walk_C','Run_A']:
    motion('source_'+role,BASE/f'LibraryReview20260928/SourceFBX/anim_{role}.fbx',source=True)
    motion('native_'+role,BASE/f'LibraryMotionV7/Native/A_SpitterLibraryRaw_{role}.fbx')
    motion('authored_'+role,BASE/'LibraryMotionV7/SpitterZombie_LibraryMotionV7.blend','A_Spitter_LibraryV7_'+role,skin=True)
    motion('fbx_'+role,BASE/f'LibraryMotionV7/Final/A_Spitter_LibraryV7_{role}.fbx')
(ROOT/'blender_read.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SPITTER_RIG_AUDIT_DONE',flush=True)
