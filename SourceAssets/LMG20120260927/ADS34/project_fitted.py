"""Measure the requested ADS repair using the same original arm pose."""
import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
O=Path(__file__).parent;d=json.loads((O/'sources.json').read_text())['meshes'];a=json.loads((O/'projection.json').read_text());R=np.array(a['rotation']);loc=np.array(a['location'])
def matrix(t):
 m=np.eye(4);m[:3,:3]=Rotation.from_quat(t['q']).as_matrix()@np.diag(t['s']);m[:3,3]=t['p'];return m
def project(data):
 p=np.array(data['positions']);posed=np.zeros_like(p)
 for n,rest in d['shirt']['rest'].items():
  if n not in d['201']['poses']['aim']:continue
  w=np.array([row.get(n,0) for row in data['weights']]);ids=np.flatnonzero(w)
  if not len(ids):continue
  m=matrix(d['201']['poses']['aim'][n])@np.linalg.inv(matrix(rest));posed[ids]+=(p[ids]@m[:3,:3].T+m[:3,3])*w[ids,None]
 return posed@R.T+loc
saved=(O/'installed_weights.json').exists()
after_file='installed_weights.json' if saved else 'shirt_fitted_weights.json'
data=json.loads((O/after_file).read_text());v=project(data);faces=np.array(data['triangles']);names=['M_Chainmail_SharedSway','M_CuffSteel_SharedSway','M_Lining_SharedSway']
np.savez_compressed(O/'shirt_fitted_projection.npz',points=v,rest=np.array(data['positions']),faces=faces,material_ids=np.array(data['triangle_materials']),material_names=np.array(names))
report={'after_source':after_file}
original=json.loads((O/'shirt_weights.json').read_text())
report['topology_retained']=data['triangles']==original['triangles']
report['max_vertex_position_delta_cm']=float(np.max(np.linalg.norm(np.array(data['positions'])-original['positions'],axis=1)))
for state,file in [('before','shirt_weights.json'),('after',after_file)]:
 x=json.loads((O/file).read_text());p=project(x);f=np.array(x['triangles']);edges=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0)
 ids=np.flatnonzero(np.asarray(x['positions'])[:,0]>0);right=p[ids]
 inview=(right[:,0]>.1)&(right[:,1]>.60*right[:,0])&(right[:,1]<right[:,0])&(np.abs(right[:,2])<.60*right[:,0])
 r=np.array(x['positions']);rlen=np.linalg.norm(r[edges[:,1]]-r[edges[:,0]],axis=1);elen=np.linalg.norm(p[edges[:,1]]-p[edges[:,0]],axis=1)
 report[state]={'right_screen_edge_vertices':int(inview.sum()),'max_edge_cm':float(elen.max()),'stretched_edges_above_2cm':int(((elen>2*rlen)&(elen>2)).sum())}
(O/'fit_projection_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
