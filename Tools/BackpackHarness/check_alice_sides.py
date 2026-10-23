"""Requested local geometry checks, including untouched straps and actual pocket recesses."""
import json,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
import trimesh

R=Path('D:/FPS3D/FPSGAME/SourceAssets/BackpacksReview20261021')
source=json.loads((R/'alice_source.json').read_text());d=json.loads((R/'alice_authored.json').read_text())
v=np.array(d['positions']);t=np.array(d['triangles']);m=np.array(d['triangle_materials']);uv=np.array(d['uv'])
sv=np.array(source['positions']);centre=(sv.min(0)+sv.max(0))/2;sv=(sv-centre)*[100,100,-100]
st=np.array(source['triangles']);sm=np.array(source['triangle_materials'])
source_area=np.linalg.norm(np.cross(sv[st[:,1]]-sv[st[:,0]],sv[st[:,2]]-sv[st[:,0]]),axis=1)
sm=sm[source_area>1e-7];st=st[source_area>1e-7]
def signatures(v,t,m):return Counter((int(material),*sum(sorted(tuple(np.round(p,4)) for p in v[face]),())) for face,material in zip(t,m))
protected=signatures(v,t[np.isin(m,[1,2,3])],m[np.isin(m,[1,2,3])])==signatures(sv,st[np.isin(sm,[1,2,3])],sm[np.isin(sm,[1,2,3])])
a,b=uv[:,1]-uv[:,0],uv[:,2]-uv[:,0];uv_bad=int(np.sum(abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])<1e-12))
cross=np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]]);areas=np.linalg.norm(cross,axis=1)
new_mesh=trimesh.Trimesh(v,t,process=False);old_mesh=trimesh.Trimesh(sv,st,process=False)
depth=[]
for side in [-1,1]:
    for y in [-.102,-.026]:
        z=-.015+.0025*np.sin(np.pi*(y+.114)/.102)
        start=(np.array([side*.30,y,z])-centre)*[100,100,-100];direction=np.array([-side,0,0])
        old,_,_=old_mesh.ray.intersects_location([start],[direction],multiple_hits=False)
        new,_,_=new_mesh.ray.intersects_location([start],[direction],multiple_hits=False)
        difference=float(np.linalg.norm(new[0]-start)-np.linalg.norm(old[0]-start)) if len(old) and len(new) else -1
        depth.append(dict(side=side,y=y,recess_cm=difference))
passed=bool(np.isfinite(v).all() and protected and areas.min()>1e-7 and uv_bad==0 and all(x['recess_cm']>.5 for x in depth))
result=dict(passed=passed,sha256=hashlib.sha256((R/'alice_authored.json').read_bytes()).hexdigest(),triangles=len(t),
    protected_straps_leather_hardware_equal=protected,uv_degenerate=uv_bad,min_double_area_cm2=float(areas.min()),pocket_recesses=depth,
    scope='source mesh only; no game or cloth acceptance')
(R/'alice_geometry_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(result)
if not passed:raise SystemExit(1)
