"""Inspect right-hand clearance only during reaching, contact and release."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent
script=P/'generated_contact_v4.py';ns={'__file__':str(script)}
exec(compile(script.read_text().split('bpy.ops.wm.open_mainfile')[0],str(script),'exec'),ns)
data=ns['ns']['data'];R=ns['R'];rest=ns['rest']
envelope=np.load(P/'contact-envelope.npz')
tree=BVHTree.FromPolygons(envelope['vertices'].tolist(),envelope['faces'].tolist())
sections=envelope['vertices'].reshape((-1,96,3))
def inside(p):
    k=(p.z-15)/.25;i=int(k)
    if i<0 or i>=len(sections)-1:return False
    q=sections[i]*(1-(k-i))+sections[i+1]*(k-i);r=np.roll(q,1,axis=0)
    edges=((q[:,1]>p.y)!=(r[:,1]>p.y))
    crossing=q[:,0]+(p.y-q[:,1])*(r[:,0]-q[:,0])/(r[:,1]-q[:,1]+1e-20)
    return bool(np.count_nonzero(edges&(p.x<crossing))%2)
ids=[i for i,weights in enumerate(data['weights']) if sum(v for n,v in weights.items() if n=='hand_r' or (n.endswith('_r') and n.split('_')[0] in ('index','middle','ring','pinky','thumb')))>0.8]
rows=[]
for t in [.08,.09,.10,.105,.11,.115,.12,.125,.13,.135,.14,.18,.22,.32,.44,.62,.63,.64,.65,.66,.68,.7]:
    w=ns['pose'](t);skin={n:w['bow_grip'].inverted()@m@rest[n].inverted() for n,m in w.items()}
    depths=[]
    for i in ids:
        p=sum((skin[n]@(R@Vector(data['positions'][i]))*v for n,v in data['weights'][i].items()),Vector())
        if not 16<p.z<42:continue
        co,no,idx,dist=tree.find_nearest(p);depths.append(-dist if inside(p) else dist)
    rows.append({'t':t,'min_clearance_cm':min(depths),'penetration_vertices':sum(d<-.05 for d in depths)})
(P/'motion-clearance.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
