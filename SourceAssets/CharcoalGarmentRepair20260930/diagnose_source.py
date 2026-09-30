import json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/CharcoalGarmentRepair20260930'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
d=read(P/'SourceAssets/FieldSweaterKnit20260929/ShortSleeve/Body.json')
skin=read(P/'SourceAssets/ModularOutfit20260924/NativeSkin/Body_skin.json')
p=np.array(skin['vertices']);f=np.array(skin['triangles']);n=np.array(skin['normals'])
tree=BVHTree.FromPolygons([Vector(x) for x in p],f.tolist(),all_triangles=True)
rows=[]
for i,x in enumerate(d['positions']):
    near,_,fi,dist=tree.find_nearest(Vector(x));normal=n[f[fi]].mean(0);normal/=max(np.linalg.norm(normal),1e-8)
    signed=float((np.array(x)-near)@normal)
    if signed<-.1:rows.append(dict(vertex=i,position=x,inside_cm=-signed,skin_material=skin['materials'][fi]))
print('BODY_INSIDE',len(rows),'max',max((x['inside_cm'] for x in rows),default=0))
for key,pred in [('neck',lambda x:x[2]>150),('shoulder',lambda x:abs(x[0])>15 and x[2]>138),('torso',lambda x:abs(x[0])<15 and 98<x[2]<150),('hem',lambda x:x[2]<98)]:
    picked=[r for r in rows if pred(r['position'])];print(key,len(picked),max((r['inside_cm'] for r in picked),default=0))
mid=p[f].mean(1);m=np.array(skin['materials']);print('hidden_neck_faces',int(sum((m==3)&(mid[:,2]>150))),'hidden_neck_max_z',float(mid[m==3,2].max()))
(R/'body-source-penetration.json').write_text(json.dumps(rows))
