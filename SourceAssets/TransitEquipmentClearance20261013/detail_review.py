"""Resolve broad-phase candidates and check cabinet opening envelopes."""
from pathlib import Path
import json,gzip,itertools,math
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parent
with gzip.open(ROOT/'Receipts/geometry-before.json.gz','rt',encoding='utf8') as f:data=json.load(f)
rows={r['key']:r for r in data['rows']};assets=data['meshes'];cache={}
def verts(key):
    r=rows[key];return np.array(assets[r['mesh']]['vertices'])@np.array(r['axes'])+r['origin']
def mesh(key):
    if key not in cache:cache[key]=trimesh.Trimesh(verts(key),assets[rows[key]['mesh']]['triangles'],process=False)
    return cache[key]
def surface_crossings(a,b):
    am,bm=mesh(a),mesh(b);edges=am.vertices[am.edges_unique]
    box=bm.bounds
    edges=edges[((edges.max(1)>box[0]-.01)&(edges.min(1)<box[1]+.01)).all(1)]
    if not len(edges):return dict(count=0,points=[])
    vectors=edges[:,1]-edges[:,0];length=np.linalg.norm(vectors,axis=1);valid=length>1e-4
    edges=edges[valid];length=length[valid];vectors=vectors[valid]/length[:,None]
    points,ray,_=bm.ray.intersects_location(edges[:,0],vectors,multiple_hits=True)
    dist=np.linalg.norm(points-edges[ray,0],axis=1)
    keep=(dist>0.1)&(dist<length[ray]-.1)
    return dict(count=int(keep.sum()),points=points[keep][:8].round(2).tolist())
report=dict(surface_crossings={},portal_clearance=[],opening_candidates=[])
for a,b in [('part:124','part:125'),('part:36','part:37'),('actor:5:body','part:6')]:
    report['surface_crossings'][a+'/'+b]=[surface_crossings(a,b),surface_crossings(b,a)]
    print('CROSSINGS',a,b,report['surface_crossings'][a+'/'+b],flush=True)
zones={'Route1':([2250,-145,12],[2800,145,218]),'Route2':([655,-2200,12],[945,-1650,218]),'Route3':([655,1650,12],[945,2200,218])}
for route,(lo,hi) in zones.items():
    hits=[];tested=0
    for key,row in rows.items():
        if not key.startswith(route+':') or 'vertices' not in assets[row['mesh']]:continue
        tri=verts(key)[np.array(assets[row['mesh']]['triangles'])]
        hit=((tri.max(1)>np.array(lo)+.2)&(tri.min(1)<np.array(hi)-.2)).all(1)
        tested+=1
        if hit.any():hits.append(dict(key=key,mesh=row['mesh'],triangles=int(hit.sum())))
    report['portal_clearance'].append(dict(route=route,source_parts=tested,triangle_candidates=hits))
# Sweep cabinet doors in five-degree increments against benches, neighboring
# cabinet bodies and actual structural surfaces. Test the corrected final cabinet.
targets=['part:52','part:53']+['actor:'+str(i)+':body' for i in range(6)]
target_bounds={k:np.array([verts(k).min(0),verts(k).max(0)]) for k in targets}
target_bounds['actor:5:body'][:,0]+=90
structure=mesh('part:6').triangles
for i in range(6):
    key='actor:'+str(i)+':door';row=rows[key];local=np.array(assets[row['mesh']]['vertices']);actor=rows['actor:'+str(i)+':body']
    origin=np.array(actor['origin']);origin[0]+=90 if i==5 else 0
    hit_keys=set();envelope=[]
    for angle in np.linspace(0,-105,22):
        rad=math.radians(angle);rot=np.array([[math.cos(rad),math.sin(rad),0],[-math.sin(rad),math.cos(rad),0],[0,0,1]])
        ps=(local@rot+row['hinge'])@np.array(actor['axes'])+origin
        lo,hi=ps.min(0),ps.max(0);envelope.extend([lo,hi])
        for target,box in target_bounds.items():
            if target=='actor:'+str(i)+':body':continue
            if ((np.minimum(hi,box[1])-np.maximum(lo,box[0]))>.3).all():hit_keys.add(target)
        mask=((structure.max(1)>lo+.2)&(structure.min(1)<hi-.2)).all(1)
        if mask.any():hit_keys.add('column')
    report['opening_candidates'].append(dict(cabinet=i,conflicts=sorted(hit_keys),swept_min=np.min(envelope,axis=0).tolist(),swept_max=np.max(envelope,axis=0).tolist()))
(ROOT/'Receipts/detail-review.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
