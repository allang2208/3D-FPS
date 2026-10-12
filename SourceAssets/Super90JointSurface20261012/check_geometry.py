"""Check authored/read-back positions, native binding, UVs and sampled poses."""
import sys,json,hashlib
import numpy as np
from scipy.spatial import cKDTree
from geometry import O,load,mat
d=load('arms_before.json.gz');p=np.array(d['positions']);t=np.array(d['triangles']);patch=np.load(O/'geometry_patch.npz');q=patch['after']
def facevec(v):return np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]])
bad_vertices=set()
def flips(a,b):
 x,y=facevec(a),facevec(b);bad=(np.einsum('ij,ij->i',x,y)<0)&(np.linalg.norm(x,axis=1)>1e-7)
 bad_vertices.update(int(i) for i in t[bad].ravel());return int(np.sum(bad))
vn=np.zeros_like(p)
for c in range(3):np.add.at(vn,t[:,c],np.array(d['normals'])[:,c])
vn/=np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1e-12)
normal_dot=np.sum(vn[patch['normalids']]*patch['normals'][patch['normalids']],axis=1)
assert float(np.median(normal_dot))>.95,'Authored normal orientation disagrees with UE overlay'
distal=np.array([sum(x for k,x in w.items() if ('_02_' in k or '_03_' in k) and k.startswith(('thumb','index','middle','ring','pinky'))) for w in d['weights']])>.5
assert np.max(np.linalg.norm(p-q,axis=1)[distal])==0
report=dict(reference_new_flipped_faces=flips(p,q),max_reference_delta_mm=float(np.max(np.linalg.norm(q-p,axis=1))*10),normal_direction_median_dot=float(np.median(normal_dot)),distal_finger_vertices_unchanged=int(sum(distal)),poses={},readback={})
parts=[]
for name,b in d['bones'].items():
 weights=np.array([w.get(name,0.) for w in d['weights']]);ids=np.flatnonzero(weights)
 if len(ids):parts.append((name,np.linalg.inv(mat(b)),ids,weights[ids,None]))
def skinned(row,v):
 result=np.zeros_like(v)
 for name,inv,ids,w in parts:
  m=mat(row['bones'][name])@inv;result[ids]+=(v[ids]@m[:3,:3].T+m[:3,3])*w
 return result
poses=load('poses.json.gz')
for name,clip in poses.items():
 maxdisp=0;inverted=0
 for row in clip['rows']:
  a,b=skinned(row,p),skinned(row,q)
  maxdisp=max(maxdisp,float(np.max(np.linalg.norm(a-b,axis=1))*10));inverted=max(inverted,flips(a,b))
 report['poses'][name]={'frames':len(clip['rows']),'max_delta_mm':maxdisp,'max_new_reversed_faces':inverted}
 print('POSE_CHECK',name,report['poses'][name],flush=True)
# Actual saved candidate data is checked by index when the conversion preserves
# indices; otherwise establish an exact position/weight-aware correspondence.
for key in ('arms','full'):
 f=O/(key+'_candidate.json.gz')
 if not f.exists():continue
 before=load(key+'_before.json.gz');saved=load(f.name);auth=json.loads((O/'patches.json').read_text())[key]
 expected=np.array(before['positions'])
 for vi,pos in auth['positions']:expected[vi]=pos
 actual=np.array(saved['positions']);dist,idx=cKDTree(expected).query(actual)
 same_order=bool(actual.shape==expected.shape and np.max(np.abs(actual-expected))<2e-5)
 if same_order:idx=np.arange(len(actual))
 weight_error=max((abs(w.get(n,0)-before['weights'][int(i)].get(n,0)) for i,w in zip(idx,saved['weights']) for n in set(w)|set(before['weights'][int(i)])),default=0)
 triangles_equal=saved['triangles']==before['triangles']
 uvs_equal=saved['uv']==before['uv'] if triangles_equal else False
 bones_equal=saved['bones']==before['bones'];materials_equal=saved['materials']==before['materials']
 normal_expected=np.array(before['normals']);overrides={i:n for i,n in auth['normals']}
 for ti,tri in enumerate(before['triangles']):
  for c,vi in enumerate(tri):
   if vi in overrides:normal_expected[ti,c]=overrides[vi]
 normal_error=float(np.max(np.abs(np.array(saved['normals'])-normal_expected)))
 item=dict(vertices_before=len(expected),vertices_after=len(actual),max_position_error_mm=float(dist.max()*10),same_vertex_order=same_order,weight_error=weight_error,triangles_equal=triangles_equal,uvs_equal=uvs_equal,bones_equal=bones_equal,materials_equal=materials_equal,skeleton_equal=saved['skeleton']==before['skeleton'])
 item['normal_error']=normal_error
 report['readback'][key]=item;print('SAVED_MESH_CHECK',key,item,flush=True)
 if not (same_order and weight_error<1e-7 and normal_error<2e-5 and triangles_equal and uvs_equal and bones_equal and materials_equal and item['skeleton_equal']):raise RuntimeError('Candidate altered an unrelated native attribute: '+key)
report['passed']=report['reference_new_flipped_faces']==0 and all(v['max_new_reversed_faces']==0 for v in report['poses'].values())
(O/'geometry_checks.json').write_text(json.dumps(report,indent=2))
if bad_vertices:
 previous=json.loads((O/'fragile_vertices.json').read_text()) if (O/'fragile_vertices.json').exists() else []
 (O/'fragile_vertices.json').write_text(json.dumps(sorted(bad_vertices|set(previous))))
if not report['passed']:raise RuntimeError('Local fairing reversed a triangle; revise before publishing')
print('SUPER90_GEOMETRY_CHECKS_PASSED',flush=True)
