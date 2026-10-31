"""Saved asset checks: door sweeps, fabric separation and real support surfaces."""
from pathlib import Path
import json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;D=R/'Audit/after'
data=json.loads((D/'components.json').read_text('utf8'))
rows=data['components'];raws={};world=[];trees=[];bounds=[]
for row in rows:
    raw=raws.setdefault(row['key'],json.loads((D/(row['key']+'.json')).read_text('utf8')))
    t=row['transform'];o=t['origin'];a=t['axes']
    vs=[]
    for v in raw['vertices']:
        p=[(o[i]+sum(v[j]*a[j][i] for j in range(3)))/100 for i in range(3)]
        vs.append(Vector((p[0],-p[1],p[2])))
    fs=[tuple(reversed(t)) for t in raw['triangles'] if min(t)>=0]
    world.append((vs,fs));trees.append(BVHTree.FromPolygons(vs,fs,all_triangles=True))
    bounds.append(([min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]))

def overlaps(a,b):return min(min(a[1][i],b[1][i])-max(a[0][i],b[0][i]) for i in range(3))>.00005


c=next(c for c in data['containers'] if 'Desk_Drawer' in c['actor'])
i=next(i for i,r in enumerate(rows) if r['actor']==c['actor'] and r['component']=='Door')
j=next(i for i,r in enumerate(rows) if r['actor']=='AP_Bed2_Desk')
v,f=world[i];tr=Vector((c['travel_world'][0]/100,-c['travel_world'][1]/100,c['travel_world'][2]/100));v=[p+tr for p in v]
hits=BVHTree.FromPolygons(v,f,all_triangles=True).overlap(trees[j])
print('DRAWER',c,'HITS',len(hits))
for a,b in hits[:20]:
 ca=sum((v[n] for n in f[a]),Vector())/3
 cb=sum((world[j][0][n] for n in world[j][1][b]),Vector())/3
 print('CONTACT',list(ca),list(cb))
