"""Narrow-phase triangle intersection for ground-prop broad-phase candidates."""
from pathlib import Path
import sys,json
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'pythonlib'))
import numpy as np,shapely
from scipy.spatial.transform import Rotation
S=json.loads((R/'saved_scene.json').read_text());F=json.loads((R/'findings.json').read_text())
rows={(r['actor'],r['component']):r for r in S['rows']};cache={}
def triangles(obj):
    key=(obj['actor'],obj['component'],obj['index'])
    if key not in cache:
        row=rows[key[:2]];t=row['transforms'][key[2]];m=S['meshes'][row['mesh']]
        if 'vertices' not in m:raise RuntimeError('No geometry '+row['mesh'])
        mat=Rotation.from_quat(t['q']).as_matrix()*np.array(t['s'])[None,:]
        v=(np.array(m['vertices'])@mat.T+np.array(t['p']))/100
        tris=v[np.array(m['triangles'],dtype=int)];lo=tris.min(axis=1);hi=tris.max(axis=1)
        cache[key]=(tris,lo,hi)
    return cache[key]
def edge_hits(a,b):
    # Non-coplanar interior intersections, including an edge of A piercing B.
    e1=b[:,1]-b[:,0];e2=b[:,2]-b[:,0];hits=np.zeros(len(a),dtype=bool);where=np.zeros((len(a),3))
    for i,j in [(0,1),(1,2),(2,0)]:
        d=a[:,j]-a[:,i];h=np.cross(d,e2);det=np.sum(e1*h,axis=1);valid=np.abs(det)>1e-11
        inv=np.divide(1,det,out=np.zeros_like(det),where=valid);s=a[:,i]-b[:,0]
        uu=np.sum(s*h,axis=1)*inv;q=np.cross(s,e1);vv=np.sum(d*q,axis=1)*inv;tt=np.sum(e2*q,axis=1)*inv
        hit=valid&(uu>1e-6)&(vv>1e-6)&(uu+vv<1-1e-6)&(tt>1e-6)&(tt<1-1e-6)
        where[hit]=a[hit,i]+tt[hit,None]*d[hit];hits|=hit
    return hits,where
confirmed=[];rejected=[];unresolved=[]
for n,p in enumerate(F['ground_prop_overlaps']):
    try:
        a,al,ah=triangles(p['a']);b,bl,bh=triangles(p['b'])
        ai=np.where(np.all(ah>bl.min(0),axis=1)&np.all(al<bh.max(0),axis=1))[0]
        bi=np.where(np.all(bh>al.min(0),axis=1)&np.all(bl<ah.max(0),axis=1))[0]
        bt=shapely.STRtree(shapely.box(bl[bi,0],bl[bi,1],bh[bi,0],bh[bi,1]))
        pairs=bt.query(shapely.box(al[ai,0],al[ai,1],ah[ai,0],ah[ai,1]));ia=ai[pairs[0]];ib=bi[pairs[1]]
        keep=(ah[ia,2]>bl[ib,2]+1e-6)&(al[ia,2]<bh[ib,2]-1e-6)
        ia=ia[keep];ib=ib[keep];count=0;examples=[]
        for start in range(0,len(ia),150000):
            aa=a[ia[start:start+150000]];bb=b[ib[start:start+150000]]
            h1,w1=edge_hits(aa,bb);h2,w2=edge_hits(bb,aa);count+=int(np.count_nonzero(h1|h2))
            if len(examples)<3:examples.extend(w1[h1][:3-len(examples)].tolist());examples.extend(w2[h2][:3-len(examples)].tolist())
        record=dict(p,intersecting_triangle_pairs=count,contact_examples_world_m=examples)
        (confirmed if count else rejected).append(record)
        if n%15==0:print('PRECISE_CONTACTS',n+1,'confirmed',len(confirmed),flush=True)
    except Exception as e:unresolved.append(dict(p,error=str(e)))
    if len(cache)>4:cache.clear()
result=dict(method='source LOD0 mesh triangles; strict transverse edge-triangle intersections',confirmed=confirmed,broad_phase_only=rejected,unresolved=unresolved)
(R/'precise_contacts.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('PRECISE_COMPLETE',len(confirmed),len(rejected),len(unresolved),flush=True)
