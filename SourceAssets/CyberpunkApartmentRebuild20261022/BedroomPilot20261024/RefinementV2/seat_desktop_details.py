"""Measure the two legacy surface-detail groups against the saved tabletop/keycaps."""
import json
from pathlib import Path
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent/'Audit/after'
data=json.loads((R/'components.json').read_text('utf8'))
def mesh(actor):
    row=next(r for r in data['components'] if r['actor']==actor)
    raw=json.loads((R/(row['key']+'.json')).read_text('utf8'))
    t=row['transform'];vs=[tuple((t['origin'][i]+sum(v[j]*t['axes'][j][i] for j in range(3)))/100 for i in range(3)) for v in raw['vertices']]
    return vs,raw['triangles']
vs,fs=mesh('AP_Bed2_Desk');desk=BVHTree.FromPolygons(vs,fs,all_triangles=True)
results=[]
for actor in ('AP7_Bed2_KeyLegends','AP7_Bed2_DeskSeams'):
    vs,fs=mesh(actor);trials=[]
    for mm in (0.,.25,.5,.6,.75,1.,1.5,2.,2.5,3.):
        points=[(x,y,z+mm/1000) for x,y,z in vs]
        hits=desk.overlap(BVHTree.FromPolygons(points,fs,all_triangles=True))
        trials.append(dict(raise_mm=mm,triangle_pairs=len(hits)))
    results.append(dict(actor=actor,trials=trials))
(R/'desktop-detail-seating.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print(json.dumps(results))
