import bpy,json,numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/MeshyRigV01')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/M66_source.blend'))
obj=bpy.data.objects['output'];mesh=obj.data
p=np.array([obj.matrix_world@v.co for v in mesh.vertices])
keys={};weld=[];unique=[]
for point in p:
    key=tuple(np.rint(point/1e-5).astype(int))
    if key not in keys:keys[key]=len(unique);unique.append(point)
    weld.append(keys[key])
unique=np.array(unique);weld=np.array(weld);edges=np.array([(weld[e.vertices[0]],weld[e.vertices[1]]) for e in mesh.edges])
rows=[]
for height in [1.40,1.45,1.50,1.55,1.60,1.65]:
    selected=unique[:,2]>height;parent=np.arange(len(unique))
    def find(a):
        while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
        return a
    for a,b in edges:
        if selected[a] and selected[b]:
            ra,rb=find(a),find(b)
            if ra!=rb:parent[rb]=ra
    groups={}
    for n in np.flatnonzero(selected):groups.setdefault(find(n),[]).append(int(n))
    groups=sorted(groups.values(),key=len,reverse=True)
    row={'height':height,'components':[]}
    for g in groups[:10]:
        if len(g)<25:continue
        q=unique[g];row['components'].append({'n':len(g),'center':q.mean(axis=0).round(4).tolist(),'min':q.min(axis=0).round(4).tolist(),'max':q.max(axis=0).round(4).tolist()})
    rows.append(row)
print('UPPER_COMPONENTS '+json.dumps(rows))
back=[]
for z0,z1 in [(.75,.95),(.95,1.15),(1.15,1.35),(1.35,1.5)]:
    for x0,x1 in [(-.3,0),(0,.2),(.2,.5)]:
        indices=np.flatnonzero((p[:,0]>=x0)&(p[:,0]<x1)&(p[:,1]>.10)&(p[:,2]>=z0)&(p[:,2]<z1))
        if len(indices)<10:continue
        weights={}
        for i in indices:
            for g in mesh.vertices[int(i)].groups:
                name=obj.vertex_groups[g.group].name;weights[name]=weights.get(name,0)+g.weight
        back.append({'x':[x0,x1],'z':[z0,z1],'n':len(indices),'center':p[indices].mean(axis=0).round(4).tolist(),'weights':sorted(weights.items(),key=lambda x:-x[1])[:4]})
print('BACK_FIELDS '+json.dumps(back))
(ROOT/'Records/back_fields.json').write_text(json.dumps({'upper_components':rows,'back':back},indent=2),encoding='utf-8')
