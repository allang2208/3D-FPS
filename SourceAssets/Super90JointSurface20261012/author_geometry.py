"""Bounded local surface fairing. Topology, weights and grip vertices stay fixed."""
import json,gzip
import numpy as np
from scipy.sparse import coo_matrix,diags
from scipy.spatial import cKDTree
from geometry import O,load,skin,vertex_normals
def smoothstep(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
d=load('arms_before.json.gz');p=np.array(d['positions']);t=np.array(d['triangles'])
# Coincident section/UV splits share the same fairing displacement. No weld is
# written into the mesh, so source indices, UVs and skin weights remain intact.
rounded=np.round(p,4);_,first,inv=np.unique(rounded,axis=0,return_index=True,return_inverse=True)
v=p[first];ft=inv[t];edges=np.unique(np.sort(np.concatenate([ft[:,[0,1]],ft[:,[1,2]],ft[:,[2,0]]]),axis=1),axis=0)
edges=edges[edges[:,0]!=edges[:,1]];edges=np.concatenate([edges,edges[:,::-1]])
dist=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1)
adj=coo_matrix((1/np.maximum(dist,.08),(edges[:,0],edges[:,1])),shape=(len(v),len(v))).tocsr()
adj=diags(1/np.maximum(np.asarray(adj.sum(1)).ravel(),1e-8))@adj
mask=np.zeros(len(v));cap=np.zeros(len(v));regions={}
for side in ('l','r'):
 e=np.array(d['bones']['lowerarm_'+side]['position']);w=np.array(d['bones']['hand_'+side]['position'])
 direction=(w-e)/np.linalg.norm(w-e);a=(v-w)@direction
 radius=np.linalg.norm(v-w-a[:,None]*direction,axis=1)
 wrist=smoothstep(-5.0,-2.7,a)*(1-smoothstep(.3,2.4,a))*(1-smoothstep(4,5.5,radius))
 elbow=(1-smoothstep(3.2,7.5,np.linalg.norm(v-e,axis=1)))
 palm=smoothstep(.3,1.8,a)*(1-smoothstep(2.6,4.1,a))*(1-smoothstep(3.5,4.5,radius))
 # Distal fingers and vertices influenced by finger bones are never moved.
 finger=np.array([sum(x for n,x in d['weights'][i].items() if n.startswith(('thumb_','index_','middle_','ring_','pinky_')) and '_metacarpal_' not in n) for i in first])
 palm*=1-smoothstep(.02,.10,finger)
 mask=np.maximum(mask,np.maximum.reduce([wrist*.85,elbow*.8,palm*.25]))
 cap=np.maximum(cap,np.maximum.reduce([wrist*.16,elbow*.22,palm*.055]))
 regions[side]={'wrist':wrist,'elbow':elbow,'palm':palm}
if (O/'fragile_vertices.json').exists():
 frozen=np.zeros(len(v));frozen[inv[json.loads((O/'fragile_vertices.json').read_text())]]=1
 # Two ring falloff around actual motion-sensitive triangles; coincident UV
 # splits receive the same restriction. This is measured from saved animations.
 halo=frozen.copy()
 for strength in (1.,.95,.80,.60,.30):
  reach=np.asarray((adj@frozen)>0,dtype=float);halo=np.maximum(halo,reach*strength);frozen=np.maximum(frozen,reach)
 mask*=1-halo;cap*=1-halo
# Windowed Taubin fairing removes narrow inherited folds without narrowing the
# complete forearm. The displacement cap is in centimetres.
q=v.copy()
for iteration in range(36):
 for step in (.50,-.40):q+=step*(adj@q-q)*mask[:,None]
delta=q-v;mag=np.linalg.norm(delta,axis=1)
delta*=np.minimum(1,cap/np.maximum(mag,1e-12))[:,None]
q=v+delta;out=p+delta[inv]
# UE's saved triangle winding is clockwise. The exported normal overlay is
# opposite the right-handed cross product used by NumPy.
normals=-vertex_normals(q,ft)[inv]
original_n=np.zeros_like(p);counts=np.zeros(len(p))
for j in range(3):np.add.at(original_n,t[:,j],np.array(d['normals'])[:,j]);np.add.at(counts,t[:,j],1)
original_n/=np.maximum(np.linalg.norm(original_n,axis=1,keepdims=True),1e-12)
# The old arm overlays retain hard clothing-era shading. Rebuild smooth arm
# normals across coincident section splits; finger/palm normals remain local.
nm=smoothstep(0,.12,mask)[inv]
arm_vertices=np.unique(t[np.array(d['materials'])!=2])
nm[arm_vertices]=1.
new_n=original_n*(1-nm[:,None])+normals*nm[:,None];new_n/=np.maximum(np.linalg.norm(new_n,axis=1,keepdims=True),1e-12)
changed=np.flatnonzero(np.linalg.norm(out-p,axis=1)>1e-7);normalids=np.flatnonzero(nm>0)
np.savez_compressed(O/'geometry_patch.npz',before=p,after=out,normals=new_n,changed=changed,normalids=normalids,mask=mask[inv])
report={'changed_vertices':len(changed),'normal_vertices':len(normalids),'max_displacement_mm':float(np.max(np.linalg.norm(out-p,axis=1))*10),'regions':{}}
for side,rs in regions.items():
 for name,m in rs.items():
  ids=m[inv]>.1;report['regions'][side+'_'+name]={'vertices':int(sum(ids)),'max_mm':float(np.max(np.linalg.norm(out-p,axis=1)[ids],initial=0)*10)}
report.update(weights_changed=False,topology_changed=False,uv_changed=False,animations_changed=False)
(O/'geometry_authored.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
full=load('full_before.json.gz');fp=np.array(full['positions']);ds,ix=cKDTree(p).query(fp)
skinm={i for i,s in enumerate(full['slots']) if s['name'].startswith('Manny_S90_Skin_')}
skinids=np.unique(np.array(full['triangles'])[np.isin(full['materials'],list(skinm))])
assert ds[skinids].max()<1e-5
after=fp.copy();after[skinids]+=out[ix[skinids]]-p[ix[skinids]]
patches={}
for key,data,op,idx in [('arms',d,out,np.arange(len(p))),('full',full,after,ix)]:
 ids=changed if key=='arms' else skinids[np.isin(ix[skinids],changed)]
 ns=normalids if key=='arms' else skinids[np.isin(ix[skinids],normalids)]
 patches[key]={'path':data['path'],'source_sha256':data['sha256'],'positions':[[int(i),op[i].tolist()] for i in ids], 'normals':[[int(i),new_n[idx[i]].tolist()] for i in ns]}
(O/'patches.json').write_text(json.dumps(patches,separators=(',',':')))
poses=load('poses.json.gz');shots=[('idle',0),('reload_full',45),('reload_full',115)]
np.savez_compressed(O/'review_after.npz',triangles=full['triangles'],materials=full['materials'],**{f'p{i}':skin(full,poses[n]['rows'][i0],after) for i,(n,i0) in enumerate(shots)})
