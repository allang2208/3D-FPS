"""Scoped geometry/pose diagnosis for the reported Body/Traversal defects."""
import json,sys
from pathlib import Path
import numpy as np
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/CharcoalGarmentRepair20260930'
sys.path.insert(0,str(R));from author import normals,bary
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def matrix(t):
 m=np.eye(4);m[:3,:3]=np.array(Quaternion((t['q'][3],*t['q'][:3])).to_matrix())@np.diag(t['s']);m[:3,3]=t['p'];return m
def rest(d):
 if 'rest' in d:return {n:matrix(t) for n,t in d['rest'].items()}
 out={}
 for n,b in d['bones'].items():
  m=np.eye(4);m[:3,:3]=np.array(b['axes']).T;m[:3,3]=b['position'];out[n]=m
 return out
def prepare(d):
 bind=rest(d);p=np.array(d['positions']);groups={}
 for i,w in enumerate(d['weights']):
  for n,v in w.items():groups.setdefault(n,[]).append((i,v))
 return p,[(n,np.array([r[0] for r in rows]),np.array([r[1] for r in rows])[:,None],np.linalg.inv(bind[n])) for n,rows in groups.items()]
def deform(pre,mat):
 p,groups=pre;out=np.zeros_like(p)
 for n,ids,w,inv in groups:
  m=mat[n]@inv;out[ids]+=(p[ids]@m[:3,:3].T+m[:3,3])*w
 return out
report={}
for profile in ['Body','Traversal']:
 skin=read(R/'Before'/profile/'skin.json');sf=np.array(skin['triangles']);sm=np.array(skin['materials']);ps=prepare(skin)
 states={'Before':read(R/'Before'/profile/'shirt.json'),'Authored':read(R/'Authored'/('BodyEquipped.json' if profile=='Body' else profile+'.json'))}
 saved=R/'Saved'/('BodyV4' if profile=='Body' else 'TraversalV2')
 if saved.exists():
  for lod in range(3):
   path=saved/('LOD'+str(lod)+'.json')
   if path.exists():states['SavedLOD'+str(lod)]=read(path)
 if '--saved-only' in sys.argv:states={k:v for k,v in states.items() if k.startswith('SavedLOD')}
 results={}
 poses={'Rest':{n:t for n,t in skin['rest'].items()}}
 poses.update({n:r['bones'] for n,r in read(R/'Before'/profile/'poses.json').items()})
 for label,d in states.items():
  pre=prepare(d);allf=np.array(d['triangles']);materials=np.array(d.get('materials',d.get('triangle_materials')));f=allf[materials<3];p=pre[0];cloth_ids=np.unique(f)
  unique,inv=np.unique(np.round(p,4),axis=0,return_inverse=True);ef=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0)
  e=np.sort(inv[ef],axis=1);eface=np.sort(np.concatenate([inv[f[:,[0,1]]],inv[f[:,[1,2]]],inv[f[:,[2,0]]]]),axis=1);eq,ec=np.unique(eface,axis=0,return_counts=True)
  boundary=eq[ec==1];entry=dict(vertices=len(p),triangles=len(f),boundary_edges=len(boundary),nonmanifold_edges=int(sum(ec>2)),max_rest_edge_cm=float(np.linalg.norm(p[ef[:,1]]-p[ef[:,0]],axis=1).max()),poses={})
  if len(boundary):entry['boundary_bounds']=[unique[boundary].reshape(-1,3).min(0).tolist(),unique[boundary].reshape(-1,3).max(0).tolist()]
  for name,pose in poses.items():
   mat={n:matrix(t) for n,t in pose.items()};dp=deform(pre,mat);sk=deform(ps,mat)
   visible_sf=sf
   if profile=='Body':
    covers=[3] if label=='Before' else [1,3,4]
    visible_sf=sf[~np.isin(sm,covers)]
    if label!='Before':
     visible_sf=np.concatenate([visible_sf,allf[materials>=3]+len(sk)])
     sk=np.concatenate([sk,dp])
   tree=BVHTree.FromPolygons([Vector(x) for x in sk],visible_sf.tolist(),all_triangles=True);sn=normals(sk,visible_sf)
   cloth_tree=BVHTree.FromPolygons([Vector(x) for x in dp],f.tolist(),all_triangles=True)
   intersections=len(cloth_tree.overlap(tree))
   inside=[]
   for i in cloth_ids:
    v=dp[i];near,_,fi,dist=tree.find_nearest(Vector(v));bc=bary(near,sk[visible_sf[fi]]);normal=(sn[visible_sf[fi]]*bc[:,None]).sum(0);normal/=max(np.linalg.norm(normal),1e-9);signed=float((v-near)@normal)
    if signed<-.1:inside.append((i,-signed))
   entry['poses'][name]=dict(vertices_inside_skin=len(inside),max_inside_cm=max((v for i,v in inside),default=0.),surface_intersection_pairs=intersections,max_edge_cm=float(np.linalg.norm(dp[ef[:,1]]-dp[ef[:,0]],axis=1).max()))
   if name=='Rest':entry['rest_inside_ids']=[int(i) for i,v in inside]
  results[label]=entry
  print('CHARCOAL_DIAG',profile,label,'boundary/nonmanifold',len(boundary),int(sum(ec>2)),'edge',entry['max_rest_edge_cm'],'intersection_pairs',max(row['surface_intersection_pairs'] for row in entry['poses'].values()),flush=True)
 report[profile]=results
(R/'diagnosis.json').write_text(json.dumps(report,indent=2))
