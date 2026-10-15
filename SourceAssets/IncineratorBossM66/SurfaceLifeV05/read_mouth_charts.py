import bpy,json
import numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/SurfaceLifeV05')
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'MeshyRigV01/Authoring/M66_back_completed_v01.blend'))
mesh=bpy.data.objects['M66_Body'];n=len(mesh.data.vertices);parent=list(range(n))
def find(a):
    while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
    return a
for edge in mesh.data.edges:
    a,b=(find(int(v)) for v in edge.vertices)
    if a!=b:parent[b]=a
groups={}
for i in range(n):groups.setdefault(find(i),[]).append(i)
factor=json.loads((ROOT.parent/'MeshyRigV01/Records/rig_completion.json').read_text())['uniform_scale']
pos=np.array([v.co[:] for v in mesh.data.vertices])/factor
names=[g.name for g in mesh.vertex_groups];uv=mesh.data.uv_layers.active.data
vertex_uv={l.vertex_index:uv[l.index].uv[:] for l in mesh.data.loops}
rows=[]
for root,ids in groups.items():
    p=pos[ids];front=(p[:,0]>-.2)&(p[:,0]<.18)&(p[:,1]<-.12)&(p[:,2]>.55)&(p[:,2]<1.2)
    if front.sum()<25:continue
    w={}
    for i in ids:
        for g in mesh.data.vertices[i].groups:w[names[g.group]]=w.get(names[g.group],0)+g.weight
    rows.append({'root':root,'vertices':len(ids),'mouth_roi':int(front.sum()),'xyz_bounds':[p.min(axis=0).tolist(),p.max(axis=0).tolist()],
                 'uv_bounds':[np.min([vertex_uv[i] for i in ids],axis=0).tolist(),np.max([vertex_uv[i] for i in ids],axis=0).tolist()],
                 'dominant_weights':sorted(w.items(),key=lambda row:-row[1])[:6]})
rows.sort(key=lambda row:-row['mouth_roi'])
(ROOT/'Records/mouth_charts.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('M66_MOUTH_CHARTS '+json.dumps(rows[:16]))
