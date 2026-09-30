"""Distinguish BVH candidate pairs from triangle surface crossings."""
import json,sys
from collections import Counter
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.geometry import intersect_ray_tri
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
from author import read,write
from finish import matrix
def prepare(d):
 p=np.array(d['positions']);groups={}
 for i,w in enumerate(d['weights']):
  for n,v in w.items():groups.setdefault(n,[]).append((i,v))
 return p,[(n,np.array([i for i,v in rows]),np.array([v for i,v in rows])[:,None],np.linalg.inv(matrix(d['rest'][n]))) for n,rows in groups.items()]
def deform(pre,mat):
 p,groups=pre;out=np.zeros_like(p)
 for n,ids,w,inv in groups:
  m=mat[n]@inv;out[ids]+=(p[ids]@m[:3,:3].T+m[:3,3])*w
 return out
def crosses(a,b):
 for x,y in [(a,b),(b,a)]:
  for i in range(3):
   start=Vector(x[i]);end=Vector(x[(i+1)%3]);direction=end-start
   hit=intersect_ray_tri(*[Vector(p) for p in y],direction,start,True)
   if hit is not None:
    t=(hit-start).dot(direction)/max(direction.length_squared,1e-12)
    if .00001<t<.99999:return True
 return False
report={}
for profile in ['Body','Traversal']:
 base=read(R/'Before'/profile/'skin.json');sf=np.array(base['triangles']);sm=np.array(base['materials']);bp=prepare(base)
 if '--authored' in sys.argv:
  d=read(R/'Authored'/('BodyEquipped.json' if profile=='Body' else 'Traversal.json'));d['rest']=base['rest']
 else:d=read(R/'Saved'/('BodyV4' if profile=='Body' else 'TraversalV2')/'LOD0.json')
 af=np.array(d['triangles']);am=np.array(d.get('materials',d.get('triangle_materials')));f=af[am<3];cp=prepare(d)
 poses={'Rest':base['rest']};poses.update({n:row['bones'] for n,row in read(R/'Before'/profile/'poses.json').items()})
 rows={}
 for key,pose in poses.items():
  mats={n:matrix(t) for n,t in pose.items()};p=deform(cp,mats);sk=deform(bp,mats);visible=sf
  if profile=='Body':visible=np.concatenate([sf[~np.isin(sm,[1,3,4])],af[am>=3]+len(sk)]);sk=np.concatenate([sk,p])
  a=BVHTree.FromPolygons([Vector(x) for x in p],f.tolist(),all_triangles=True);b=BVHTree.FromPolygons([Vector(x) for x in sk],visible.tolist(),all_triangles=True)
  pairs=a.overlap(b);actual=[(i,j) for i,j in pairs if crosses(p[f[i]],sk[visible[j]])]
  mids=np.array([np.array(d['positions'])[f[i]].mean(0) for i,j in actual])
  categories=Counter()
  for i,j in actual:
   face=visible[j];base_part=base['materials'][j] if profile=='Traversal' else (int(sm[~np.isin(sm,[1,3,4])][j]) if j<len(sf[~np.isin(sm,[1,3,4])]) else 1 if am[am>=3][j-len(sf[~np.isin(sm,[1,3,4])])]==3 else 3)
   aa=p[f[i]];bb=sk[face];na=np.cross(aa[1]-aa[0],aa[2]-aa[0]);nb=np.cross(bb[1]-bb[0],bb[2]-bb[0]);kind='outer' if na@nb>0 else 'inner'
   categories[str(base_part)+'_'+kind]+=1
  rows[key]=dict(bvh_pairs=len(pairs),crossings=len(actual),categories=dict(categories),cloth_faces=sorted(set(i for i,j in actual)))
  if len(mids):rows[key]['rest_region_bounds']=[mids.min(0).tolist(),mids.max(0).tolist()]
 report[profile]=rows;print('CHARCOAL_CONTACT',profile,sorted([(k,v['crossings'],v['categories']) for k,v in rows.items()],key=lambda a:-a[1])[:3], 'REST',rows['Rest']['categories'],flush=True)
write(R/('contact-authored.json' if '--authored' in sys.argv else 'contact-details.json'),report)
