"""Scoped source diagnosis of the reported garment spikes and body intersections."""
from pathlib import Path
import bpy, numpy as np, json, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
OUT=ROOT/'ClothContactV7';OUT.mkdir(exist_ok=True)
after='--after' in sys.argv
source=OUT/'BoundCongregate_ClothV7.blend' if after else ROOT/'TentacleDynamicsV6/BoundCongregate_DynamicsV6.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');scene=bpy.context.scene
body=bpy.data.objects['BC_Flesh'];names=[b.name for b in rig.data.bones]
inv={b.name:b.matrix_local.inverted() for b in rig.data.bones}
proxies=[o for o in scene.objects if o.type=='MESH' and o.name.endswith('_SimulationProxy')]
report={'source':str(source),'garments':{},'poses':[]};data={}
for ob in proxies:
    p=np.array([v.co[:] for v in ob.data.vertices]);edges=np.array([e.vertices[:] for e in ob.data.edges]);length=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1)
    weights=np.zeros((len(p),len(names)))
    for v in ob.data.vertices:
        for g in v.groups:
            name=ob.vertex_groups[g.group].name
            if name in names:weights[v.index,names.index(name)]=g.weight
    ob.data.calc_loop_triangles();tris=np.array([t.vertices[:] for t in ob.data.loop_triangles])
    area=np.linalg.norm(np.cross(p[tris[:,1]]-p[tris[:,0]],p[tris[:,2]]-p[tris[:,0]]),axis=1)*.5
    render=bpy.data.objects[ob.name.replace('_SimulationProxy','')]
    shell=[]
    if len(render.data.vertices)==len(p)*2:
        rp=np.array([v.co[:] for v in render.data.vertices]);shell=np.linalg.norm(rp[len(p):]-rp[:len(p)],axis=1)
    colors=ob.data.color_attributes['ClothTravel'];travel=np.array([c.color[0]*.45 for c in colors.data])
    report['garments'][ob.name]={'vertices':len(p),'pinned':int(sum(travel<.0075)),
        'zero_area_triangles':int(sum(area<1e-9)), 'short_edges_under_1mm':int(sum(length<.001)),
        'longest_edge_cm':float(length.max()*100),'shell_thickness_max_cm':float(max(shell,default=0)*100),
        'shell_vertices_over_15mm':int(sum(shell>.015)) if len(shell) else 0,
        'largest_neighbour_weight_jump':float(np.abs(weights[edges[:,0]]-weights[edges[:,1]]).sum(axis=1).max()),
        'pose_samples':[]}
    data[ob.name]=(p,edges,length,weights)
samples=[(None,1)]
for role in ('Idle','Walk','TurnLeft','TurnRight','Bite'):
    action=bpy.data.actions['A_BoundCongregate_'+role+('V2' if role in ('Walk','TurnLeft','TurnRight') else 'V3')]
    for phase in (0,.25,.5,.75):samples.append((action,1+phase*(action.frame_range[1]-1)))
for action,f in samples:
    rig.animation_data.action=action
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    if action and len(action.slots):rig.animation_data.action_slot=action.slots[0]
    scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    palette=np.array([np.array(rig.pose.bones[n].matrix@inv[n]) for n in names])
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    bvh=BVHTree.FromPolygons([v.co[:] for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons]);evaluated.to_mesh_clear()
    label=(action.name if action else 'rest')+':'+str(round(f,2));report['poses'].append(label)
    for ob in proxies:
        p,edges,length,weights=data[ob.name];m=np.einsum('vn,nab->vab',weights,palette)
        posed=np.einsum('vab,vb->va',m[:,:3,:3],p)+m[:,:3,3]
        gap=[]
        for point in posed:
            q,n,_,_=bvh.find_nearest(Vector(point));gap.append((Vector(point)-q).dot(n))
        gap=np.array(gap);stretch=np.linalg.norm(posed[edges[:,0]]-posed[edges[:,1]],axis=1)/np.maximum(length,1e-6)
        worst=np.argsort(gap)[:4]
        report['garments'][ob.name]['pose_samples'].append({'pose':label,'min_gap_cm':float(gap.min()*100),
            'inside_over_1cm':int(sum(gap<-.01)),'max_edge_stretch':float(stretch.max()),
            'edge_stretch_p99':float(np.quantile(stretch,.99)),
            'max_edge_expansion_cm':float(((stretch-1)*length).max()*100),
            'worst_vertices':[{'i':int(i),'p':p[i].tolist(),'gap_cm':float(gap[i]*100)} for i in worst]})
out=OUT/('source_after.json' if after else 'source_before.json');out.write_text(json.dumps(report,indent=2))
for name,row in report['garments'].items():
    compact={k:v for k,v in row.items() if k!='pose_samples'}
    compact['worst_gap_cm']=min(x['min_gap_cm'] for x in row['pose_samples'])
    compact['worst_stretch']=max(x['max_edge_stretch'] for x in row['pose_samples'])
    compact['max_inside_over_1cm']=max(x['inside_over_1cm'] for x in row['pose_samples'])
    print(name,json.dumps(compact),flush=True)
