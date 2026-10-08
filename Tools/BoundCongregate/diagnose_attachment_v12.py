"""Inspect the current source's tip weights and garment surface attachment."""
from pathlib import Path
import bpy,numpy as np,json,sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
OUT=ROOT/'SurfaceFitV12';OUT.mkdir(exist_ok=True)
candidate='--v12' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(OUT/'BoundCongregate_SurfaceFitV12.blend' if candidate else ROOT/'FullWhipV10/BoundCongregate_FullWhipV10.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis.identity()
bpy.context.view_layer.update();body=bpy.data.objects['BC_Flesh']
points=np.array([v.co[:] for v in body.data.vertices]);selected=set()
for p in body.data.polygons:
    if body.data.materials[p.material_index].name=='BC_AttackTentacle':selected.update(p.vertices)
chain=np.array([rig.data.bones[f'attack_tentacle_{i:02d}'].head_local[:] for i in range(57)]+[rig.data.bones['attack_tentacle_56'].tail_local[:]])
expect=np.full(len(points),-1.);group={g.index:g.name for g in body.vertex_groups}
arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(chain,axis=0),axis=1))]
bone_distance={f'attack_tentacle_{i:02d}':float((arc[i]+arc[i+1])*.5) for i in range(57)}
spur_start=arc[48]
for i in range(6):
    b=rig.data.bones.get(f'tip_spur_{i:02d}')
    if b:bone_distance[b.name]=float(spur_start+b.length*.5);spur_start+=b.length
expected_distance=np.full(len(points),-1.)
for i in selected:
    values=[(int(group[g.group].rsplit('_',1)[1]),g.weight) for g in body.data.vertices[i].groups if group[g.group].startswith('attack_tentacle_')]
    expect[i]=sum(j*w for j,w in values)/max(1e-9,sum(w for _,w in values))
    distance_weights=[(bone_distance[group[g.group]],g.weight) for g in body.data.vertices[i].groups if group[g.group] in bone_distance]
    expected_distance[i]=sum(j*w for j,w in distance_weights)/max(1e-9,sum(w for _,w in distance_weights))
bad=[]
for edge in body.data.edges:
    a,b=edge.vertices
    if a in selected and b in selected and max(expect[a],expect[b])>30:
        length=float(np.linalg.norm(points[a]-points[b]));jump=abs(expected_distance[a]-expected_distance[b])*100
        if jump>max(20,length*400):bad.append({'ids':[int(a),int(b)],'cm':length*100,'arc_jump_cm':jump,'bones':[expect[a],expect[b]],'points':[points[a].tolist(),points[b].tolist()]})
body.data.calc_loop_triangles()
tree=BVHTree.FromPolygons(points.tolist(),[t.vertices[:] for t in body.data.loop_triangles],all_triangles=True)
report={'tail_bad_edges':sorted(bad,key=lambda e:-e['arc_jump_cm'])[:40],'tail_bad_edge_count':len(bad),'tail_jump_metric':'arc distance on actual bone branches > max(20cm,4x mesh edge)','chain':chain.tolist(),'bone_lengths_cm':(np.linalg.norm(np.diff(chain,axis=0),axis=1)*100).tolist(),'garments':{}}
for ob in [o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name.endswith('_SimulationProxy') or o.name=='BC_ShoulderRestraint')]:
    pts=np.array([v.co[:] for v in ob.data.vertices]);signed=[];gap=[];upper=[]
    for p in pts:
        q,n,_,d=tree.find_nearest(Vector(p));gap.append(d*100);signed.append(float((Vector(p)-q).dot(n)*100))
        if p[2]>1.35:upper.append(d*100)
    report['garments'][ob.name]={'bounds':[pts.min(0).tolist(),pts.max(0).tolist()],'gap_cm_p50_p90_max':np.percentile(gap,[50,90,100]).tolist(),'upper_gap_cm_p50_p90_max':np.percentile(upper,[50,90,100]).tolist() if upper else [],'inside_vertices':sum(s<0 for s in signed),'vertex_count':len(pts)}
(OUT/('diagnosis-after.json' if candidate else 'diagnosis.json')).write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ('chain','tail_bad_edges')}),flush=True)
