import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));from grip_math import load,pose,matrix,skinned
d=load('SK_Super90_V7');profiles=load('profiles_after');poses=load('poses');family='angled'
layer=next(c for c in profiles[family]['clips'] if c['base'].split('/')[-1].startswith('A_Super90_idle.'))
w,_=pose(d,poses[layer['base']]['samples'][0],layer);normal=matrix(d['rest']['WPN_root'])@w['WPN_root'].inverted();w={n:normal@m for n,m in w.items()}
v=skinned(d,w)*np.array([.01,-.01,.01]);mount=Matrix(((0,-1,0,0),(1,0,0,.16),(0,0,1,-.8015),(0,0,0,1)));inv=np.array(mount.inverted());v=v@inv[:3,:3].T+inv[:3,3]
bpy.ops.wm.open_mainfile(filepath=str(O/'Exports/SM_Super90_angled_Editable.blend'));ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
tree=BVHTree.FromPolygons([p.co for p in ob.data.vertices],[list(f.vertices) for f in ob.data.polygons])
result={}
for group in ('hand','thumb','index','middle','ring','pinky'):
    values=[];inside=[]
    for i,weights in enumerate(d['weights']):
        if sum(a for n,a in weights.items() if n.startswith(group) and n.endswith('_l'))<.8:continue
        p=Vector(v[i]);hit,n,_,distance=tree.find_nearest(p)
        if (p-hit).dot(n)<0:
            values.append(distance*1000)
            if distance>.004:inside.append([i,round(distance*1000,2),list(p)])
    result[group]={'negative_samples':len(values),'max_mm':max(values,default=0),'deepest':sorted(inside,key=lambda a:-a[1])[:2]}
print(json.dumps(result,indent=2));(O/'contact_groups.json').write_text(json.dumps(result,indent=2))
