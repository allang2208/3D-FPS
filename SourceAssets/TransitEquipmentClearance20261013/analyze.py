"""Offline geometric screening of saved source LOD0 placements, not a play test."""
from pathlib import Path
import gzip,json,itertools
import numpy as np
ROOT=Path(__file__).resolve().parent
with gzip.open(ROOT/'Receipts/geometry-before.json.gz','rt',encoding='utf8') as f:data=json.load(f)
rows=data['rows'];meshes=data['meshes'];cache={}
def points(row):
    mesh=meshes[row['mesh']]
    ps=np.array(mesh.get('vertices',list(itertools.product(*zip(mesh['min'],mesh['max'])))))
    return ps@np.array(row['axes'])+np.array(row['origin'])
def bounds(row):
    ps=points(row);return ps.min(axis=0),ps.max(axis=0)
def label(row):return row['key']+' '+row.get('container_id',row.get('id',row.get('fixture_id','')))+' '+row['mesh'].split('/')[-1]
props=[r for r in rows if (r['key'].startswith('part:') and (36<=int(r['key'].split(':')[1])<=56 or r.get('fixture_id') or r['mesh'].endswith(('ServiceBench','MaintenancePanel')) or r.get('id','').startswith('Incident_') and not any(s in r['mesh'] for s in ('Paper','Folder')))) or r['key'].startswith('actor:') and any(s in r['key'] for s in (':body',':door'))]
structures=[r for r in rows if r['key'].startswith('part:') and any(r['mesh'].endswith(s) for s in ('Hall_Walls','Hall_Structure','Hall_GalleryColumns','Hall_OfficeWalls','Hall_OfficeFrames','Transit_Steps','Transit_Rails','Hall_Landings','Hall_StairPiers'))]
report=dict(bounds=[],structure_candidates=[],prop_candidates=[])
for r in props:
    lo,hi=bounds(r);report['bounds'].append(dict(key=r['key'],label=label(r),min=lo.tolist(),max=hi.tolist()))
    for s in structures:
        if s['key'] not in cache:
            tri=points(s)[np.array(meshes[s['mesh']]['triangles'])]
            cache[s['key']]=(tri.min(axis=1),tri.max(axis=1))
        tlo,thi=cache[s['key']]
        hit=((thi>lo+.2)&(tlo<hi-.2)).all(axis=1)
        if hit.any():report['structure_candidates'].append(dict(prop=label(r),structure=label(s),triangles=int(hit.sum()),intersection_min=np.maximum(lo,tlo[hit].min(axis=0)).tolist(),intersection_max=np.minimum(hi,thi[hit].max(axis=0)).tolist()))
for a,b in itertools.combinations(props,2):
    if a['key'].startswith('actor:') and a['key'].rsplit(':',1)[0]==b['key'].rsplit(':',1)[0]:continue
    alo,ahi=bounds(a);blo,bhi=bounds(b);overlap=np.minimum(ahi,bhi)-np.maximum(alo,blo)
    if (overlap>.5).all():report['prop_candidates'].append(dict(a=label(a),b=label(b),overlap=overlap.tolist()))
(ROOT/'Receipts/screening.json').write_text(json.dumps(report,indent=2),encoding='utf8')
for r in report['bounds']:print(r['label'],np.round(r['min'],1).tolist(),np.round(r['max'],1).tolist())
print('STRUCTURE CANDIDATES')
for r in report['structure_candidates']:print(r)
print('PROP CANDIDATES')
for r in report['prop_candidates']:print(r)
