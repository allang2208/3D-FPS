import bpy,json,heapq,numpy as np
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
bpy.ops.wm.open_mainfile(filepath=str(root/'FullWhipV10/BoundCongregate_FullWhipV10.blend'))
ob=bpy.data.objects['BC_Flesh'];pts=np.array([v.co[:] for v in ob.data.vertices]);par={};sel=set();adj={}
for f in ob.data.polygons:
    if ob.data.materials[f.material_index].name=='BC_AttackTentacle':sel.update(f.vertices)
for i in sel:
    w=[(int(ob.vertex_groups[g.group].name.rsplit('_',1)[1]),g.weight) for g in ob.data.vertices[i].groups if ob.vertex_groups[g.group].name.startswith('attack_tentacle_')]
    par[i]=sum(n*v for n,v in w)/max(1e-9,sum(v for n,v in w));adj[i]=[]
for e in ob.data.edges:
    a,b=e.vertices
    if a in sel and b in sel:
        d=float(np.linalg.norm(pts[a]-pts[b]));adj[a].append((b,d));adj[b].append((a,d))
seed=[i for i in sel if 39.7<par[i]<40.3];dist={i:1e9 for i in sel};queue=[]
for i in seed:dist[i]=0;heapq.heappush(queue,(0,i))
while queue:
    d,i=heapq.heappop(queue)
    if d>dist[i]:continue
    for j,l in adj[i]:
        if d+l<dist[j]:dist[j]=d+l;heapq.heappush(queue,(d+l,j))
bad=set()
for i in sel:
    if par[i]<40:continue
    for j,l in adj[i]:
        if abs(par[i]-par[j])>2:bad.update((i,j))
rows=[{'id':i,'par':par[i],'distance':dist[i],'xyz':pts[i].tolist(),'neighbors':[{'id':j,'par':par[j],'distance':dist[j]} for j,l in adj[i]]} for i in sorted(bad)]
bins=[{'bone':b,'distance':np.percentile([dist[i] for i in sel if b-.5<par[i]<b+.5],[0,25,50,75,100]).tolist()} for b in range(41,56) if any(b-.5<par[i]<b+.5 for i in sel)]
(root/'SurfaceFitV12/tip-topology.json').write_text(json.dumps({'bad':rows,'bins':bins},indent=2))
chain=np.array([bpy.data.objects['BC_Rig'].data.bones[f'attack_tentacle_{i:02d}'].head_local[:] for i in range(40,57)]) if 'BC_Rig' in bpy.data.objects else np.array([next(o for o in bpy.context.scene.objects if o.type=='ARMATURE').data.bones[f'attack_tentacle_{i:02d}'].head_local[:] for i in range(40,57)])
ids=sorted(i for i in sel if par[i]>40)
np.savez(root/'SurfaceFitV12/tip-topology.npz',points=pts[ids],parameter=np.array([par[i] for i in ids]),distance=np.array([dist[i] for i in ids]),chain=chain)
print(json.dumps({'bins':bins,'rows':rows}),flush=True)
