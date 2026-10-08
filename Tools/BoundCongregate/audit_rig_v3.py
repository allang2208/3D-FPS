"""User-requested source rig, full-body deformation and garment diagnostics."""
from pathlib import Path
import bpy, json, math, sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
OUT=ROOT/'RigRepairV3';OUT.mkdir(exist_ok=True)
after='--after' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(OUT/'BoundCongregate_RigV3.blend' if after else ROOT/'LocomotionV2/BoundCongregate_LocomotionV2.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE');body=bpy.data.objects['BC_Flesh']
garments=[o for o in scene.objects if o.type=='MESH' and o.name.startswith(('BC_DonorSleeve','BC_LeftTornRobe','BC_RightLining')) and not o.hide_render]
names=[b.name for b in rig.data.bones]
def coords(ob):
    evaluated=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    p=np.empty(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',p)
    evaluated.to_mesh_clear();return p.reshape(-1,3)
base=np.array([v.co[:] for v in body.data.vertices])
edges=np.array([e.vertices[:] for e in body.data.edges]);base_lengths=np.linalg.norm(base[edges[:,0]]-base[edges[:,1]],axis=1)
usable=base_lengths>.003;edges=edges[usable];base_lengths=base_lengths[usable]
weights=np.zeros((len(base),len(body.vertex_groups)))
for v in body.data.vertices:
    for g in v.groups: weights[v.index,g.group]=g.weight
dominant=np.argmax(weights,axis=1)
gnames=[g.name for g in body.vertex_groups]
report=dict(source=str(bpy.data.filepath),bones=len(names),actions=[a.name for a in bpy.data.actions],
    skin=dict(vertices=len(base),unweighted=int(np.sum(weights.sum(1)<.99)),max_influences=int(np.max((weights>0).sum(1)))),clips={},garments={})

def garment_state(label):
    p=coords(body)
    bvh=BVHTree.FromPolygons(p.tolist(),[poly.vertices[:] for poly in body.data.polygons])
    values={}
    for ob in garments:
        q=coords(ob);gaps=[];nearest_groups=[]
        for pos in q:
            hit,normal,face,distance=bvh.find_nearest(Vector(pos))
            gaps.append((Vector(pos)-hit).dot(normal))
            poly=body.data.polygons[face]
            nearest_groups.append(gnames[dominant[min(poly.vertices,key=lambda v:np.linalg.norm(p[v]-pos))]])
        gaps=np.array(gaps)
        counts={n:nearest_groups.count(n) for n in set(nearest_groups)}
        values[ob.name]=dict(min_gap_cm=float(gaps.min()*100),median_gap_cm=float(np.median(gaps)*100),
                            penetration_vertices=int(np.sum(gaps<-.003)),vertices=len(q),
                            penetrations=np.flatnonzero(gaps<-.003).tolist(),
                            near_surface_bones=dict(sorted(counts.items(),key=lambda x:-x[1])[:8]))
    report['garments'][label]=values

rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis.identity()
bpy.context.view_layer.update();garment_state('rest')
for role in (('Idle','Walk','TurnLeft','TurnRight','Bite','Hit','Death') if after else ('Walk','TurnLeft','TurnRight')):
    action=bpy.data.actions['A_BoundCongregate_'+role+('V2' if role in ('Walk','TurnLeft','TurnRight') else 'V3')];rig.animation_data.action=action
    tracks=[];rots=[];deformation=[]
    sample_count=round((action.frame_range[1]-1)*2)+1
    for sample in range(sample_count):
        f=1+sample*.5;scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
        tracks.append([list(rig.pose.bones[n].matrix.translation) for n in names])
        rots.append([list(rig.pose.bones[n].matrix.to_quaternion()) for n in names])
        if sample%12==0:
            p=coords(body);ratios=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1)/base_lengths
            worst=np.argsort(ratios)[-20:][::-1]
            deformation.append(dict(frame=f,max_edge_ratio=float(ratios.max()),p999=float(np.percentile(ratios,99.9)),
                worst=[dict(ratio=float(ratios[e]),vertex=int(edges[e,0]),bone=gnames[dominant[edges[e,0]]]) for e in worst[:5]]))
        if sample%12==0:garment_state(role.lower()+'_'+str(f))
    tracks=np.array(tracks);rots=np.array(rots)
    steps=np.linalg.norm(np.diff(tracks,axis=0),axis=2)*100
    angles=2*np.arccos(np.clip(np.abs(np.sum(rots[1:]*rots[:-1],axis=2)),0,1))*180/math.pi
    report['clips'][role]=dict(loop_error_cm=float(np.max(np.linalg.norm(tracks[-1]-tracks[0],axis=1))*100),
        bones={n:dict(max_step_cm=float(steps[:,i].max()),max_rotation_deg=float(angles[:,i].max()),
                      jump_frame=float(1+np.argmax(steps[:,i])*.5)) for i,n in enumerate(names)},deformation=deformation)
    np.savez_compressed(OUT/(role+('_after.npz' if after else '_before.npz')),positions=tracks,rotations=rots,names=np.array(names))
    print('AUDITED',role,flush=True)
(OUT/('source_after.json' if after else 'source_before.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(skin=report['skin'],garments=report['garments']['rest'],
                     motion={k:sorted([(n,b['max_step_cm'],b['max_rotation_deg']) for n,b in v['bones'].items()],key=lambda p:-p[1])[:5] for k,v in report['clips'].items()})),flush=True)
