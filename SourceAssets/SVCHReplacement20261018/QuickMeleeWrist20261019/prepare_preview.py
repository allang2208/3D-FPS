from pathlib import Path
import sys,json,gzip
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'ForegripFit20261019'))
from arm_math import *
poses=np.load(OUT/'poses.npz')
data={'skin_triangles':arms['triangles'],'gun_triangles':[t for t,m in zip(weapon['triangles'],weapon['material_ids']) if m>=2 and m not in (5,7)]}
v=np.asarray(weapon['positions']);weights=np.zeros((len(v),len(names)))
for k,ws in enumerate(weapon['weights']):
    for b,w in ws:weights[k,ids[weapon['weight_bones'][b]]]=w
restinv=np.linalg.inv(matrices(weapon['reference']))
for key in ('before','after'):
    p=poses[key][68];gun=np.zeros_like(v)
    for j in np.flatnonzero(weights.max(0)>0):
        m=p[j]@restinv[j];gun+=(v@m[:3,:3].T+m[:3,3])*weights[:,j,None]
    data[key]={'skin':skin(p,np.arange(len(V))).tolist(),'gun':gun.tolist()}
with gzip.open(OUT/'preview-meshes.json.gz','wt') as f:json.dump(data,f,separators=(',',':'))
