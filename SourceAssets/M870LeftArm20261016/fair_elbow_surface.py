"""Local M870 elbow fold corrective, inverted through unchanged skin weights."""
import json,gzip,numpy as np
from scipy.sparse import csr_matrix,diags
from pathlib import Path
O=Path(__file__).parent
with gzip.open(O/'weapon_skin.json.gz','rt',encoding='utf-8') as f:g=json.load(f)
v=np.array(g['vertices'])*[.01,-.01,.01];rest={n:np.array(m) for n,m in json.loads((O/'before_diagnosis.json').read_text())['rest'].items()};pose={n:np.array(m) for n,m in json.loads((O/'surface_pose.json').read_text()).items()}
# Weld only the fairing graph across coincident UV/material splits; no topology changes.
keys=np.round(v,6);_,first,alias=np.unique(keys,axis=0,return_index=True,return_inverse=True);N=len(first)
transforms={n:pose[n]@np.linalg.inv(rest[n]) for n in rest};M=np.zeros((len(v),4,4));left=np.zeros(len(v))
for i,w in enumerate(g['weights']):
 for n,weight in w.items():
  if n in transforms:M[i]+=weight*transforms[n]
  if n.endswith('_l'):left[i]+=weight
p=np.einsum('nij,nj->ni',M,np.c_[v,np.ones(len(v))])[:,:3];wp=p[first].copy()
axis=pose['lowerarm_l'][:3,3]-pose['upperarm_l'][:3,3];axis/=np.linalg.norm(axis);station=(wp-pose['lowerarm_l'][:3,3])@axis
# Only the narrow inner-elbow transition; wrist, hand and broad muscle outline stay fixed.
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
mask=smooth((station+.055)/.025)*(1-smooth((station-.025)/.03))*(left[first]>.99)
edges=set()
for face in g['faces']:
 for i,a in enumerate(face):
  b=face[(i+1)%len(face)];a=int(alias[a]);b=int(alias[b])
  if a!=b:edges.add((a,b));edges.add((b,a))
rr,cc=zip(*edges);adj=csr_matrix((np.ones(len(rr)),(rr,cc)),shape=(N,N));adj=diags(1/np.maximum(1,np.asarray(adj.sum(axis=1)).ravel()))@adj
new=wp.copy()
for _ in range(160):
 for amount in (.5,-.53):new+=amount*mask[:,None]*(adj@new-new)
shift=(new-wp)[alias];changed=np.flatnonzero(np.linalg.norm(shift,axis=1)>1e-6)
vnew=v.copy()
for i in changed:vnew[i]+=np.linalg.solve(M[i,:3,:3],shift[i])
assert np.isfinite(vnew).all()
maxmove=float(np.linalg.norm(vnew-v,axis=1).max());assert maxmove<.02
bounds=np.array([v.min(axis=0),v.max(axis=0)]);newbounds=np.array([vnew.min(axis=0),vnew.max(axis=0)]);assert abs(newbounds-bounds).max()<.002
edits=[{'index':int(i),'before':v[i].tolist(),'after':vnew[i].tolist()} for i in changed]
active_edges=np.array([(a,b) for a,b in edges if mask[a]>0 or mask[b]>0]);before_len=np.linalg.norm(wp[active_edges[:,0]]-wp[active_edges[:,1]],axis=1);after_len=np.linalg.norm(new[active_edges[:,0]]-new[active_edges[:,1]],axis=1)
report={'source_mesh':g['path'],'source_hash':g['sha256'],'method':'Local seam-coherent Taubin fairing in the held elbow pose, inverted through existing skin transforms; no weights or rest changed','edits':edits,'vertices':len(edits),'max_displacement_mm':maxmove*1000,'bounds_delta_mm':float(abs(newbounds-bounds).max()*1000),'changed_edge_max_before_mm':float(max(before_len)*1000),'changed_edge_max_after_mm':float(max(after_len)*1000),'finite_coordinates':True,'runtime_tested':False}
groups={}
for e in edits:groups.setdefault(tuple(round(v,6) for v in e['before']),[]).append(e)
report['coordinate_edits']=[{'before':np.mean([e['before'] for e in v],axis=0).tolist(),'after':np.mean([e['after'] for e in v],axis=0).tolist()} for v in groups.values()]
(O/'elbow_surface.json').write_text(json.dumps(report,separators=(',',':')))
print(json.dumps({k:v for k,v in report.items() if k not in ('edits','coordinate_edits')},indent=2))
