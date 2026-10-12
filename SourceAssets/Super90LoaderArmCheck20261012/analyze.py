import json, math
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.spatial.transform import Rotation as R
O=Path(__file__).parent; C=O/'Capture'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def matrices(rows):
 a=np.asarray(rows,dtype=float);m=np.broadcast_to(np.eye(4),(len(a),4,4)).copy()
 m[:,:3,:3]=R.from_quat(a[:,3:7]).as_matrix()*a[:,None,7:];m[:,:3,3]=a[:,:3];return m
def matrix(row):return matrices([row])[0]
def init():
 global G,names,verts,rest,points,groups,faces,materials,cap_edges,cap_ids,upper,arm_ids,upper_faces,root_groups
 G=read(C/'geometry.json');names=G['names'];verts=sorted(G['vertices'],key=lambda v:v['index']);rest=matrices(G['rest'])
 points=np.array([v['p'] for v in verts]);faces=np.array(G['triangles'],dtype=int);materials=G['materials'];groups={}
 weights=np.zeros((len(verts),len(names)))
 for i,v in enumerate(verts):
  total=sum(w for b,w in v['w'])
  for b,w in v['w']:weights[i,b]=w/total
 for b in range(len(names)):
  ids=np.flatnonzero(weights[:,b]>0)
  if len(ids):groups[b]=(ids,weights[ids,b],np.c_[points[ids],np.ones(len(ids))]@np.linalg.inv(rest[b]).T)
 upper=np.flatnonzero(weights[:,names.index('upperarm_l')]>.5)
 arm_ids=np.flatnonzero(weights[:,[i for i,n in enumerate(names) if n.endswith('_l')]].sum(1)>.9)
 # Weld render-vertex UV/material splits before classifying true open boundaries.
 _,weld=np.unique(np.round(points,4),axis=0,return_inverse=True)
 edges=Counter(tuple(sorted((weld[a],weld[b]))) for t in faces[:,:3] for a,b in ((t[0],t[1]),(t[1],t[2]),(t[2],t[0])))
 representative={int(w):i for i,w in enumerate(weld)}
 cap_edges=np.array([(representative[a],representative[b]) for (a,b),k in edges.items() if k==1 and weights[representative[a],[names.index('upperarm_l'),names.index('clavicle_l')]].sum()>.95 and weights[representative[b],[names.index('upperarm_l'),names.index('clavicle_l')]].sum()>.95],dtype=int)
 cap_ids=np.unique(cap_edges)
 upper_faces=faces[np.any(np.isin(faces[:,:3],upper),axis=1),:3]
 rids=np.unique(np.r_[cap_ids,upper,upper_faces.flatten()]);root_groups={}
 for b,(ids,ws,local) in groups.items():
  keep=np.isin(ids,rids)
  if keep.any():root_groups[b]=(ids[keep],ws[keep],local[keep])
 if len(cap_ids)<3:raise RuntimeError('No complete left upper-arm opening identified')
 return dict(vertices=len(verts),triangles=len(faces),materials=materials,left_vertices=len(arm_ids),upper_vertices=len(upper),cap_vertices=len(cap_ids),cap_edges=len(cap_edges))
def skin(bones,ids=None,root_only=False):
 m=matrices(bones);out=np.zeros((len(verts),3))
 for b,(vs,ws,local) in (root_groups if root_only else groups).items():out[vs]+=(local@m[b].T)[:,:3]*ws[:,None]
 return out if ids is None else out[ids]
def transform(points,m):return points@m[:3,:3].T+m[:3,3]
def planes(th,tv,near=1.):return np.array([[1,0,0,-near],[th,1,0,0],[th,-1,0,0],[tv,0,1,0],[tv,0,-1,0]])
def clip_poly(poly,ps):
 for p in ps:
  if len(poly)==0:break
  out=[];a=poly[-1];da=np.dot(a,p[:3])+p[3]
  for b in poly:
   db=np.dot(b,p[:3])+p[3]
   if (da>=0)!=(db>=0):out.append(a+(b-a)*(da/(da-db)))
   if db>=0:out.append(b)
   a,da=b,db
  poly=out
 return np.array(poly)
def measure(points,th,tv):
 ps=planes(th,tv);p=points[cap_ids];d=p@ps[:,:3].T+ps[:,3]
 # Cap is a convex opening; a triangle fan covers its disk as well as its rim.
 exposed=0
 if np.all(np.max(d,axis=0)>=0):
  centre=p.mean(0)
  for a,b in cap_edges:
   if len(clip_poly([centre,points[a],points[b]],ps))>=3:exposed+=1
 v=points[upper];distance=np.linalg.norm(v,axis=1);visible=np.all(v@ps[:,:3].T+ps[:,3]>=0,axis=1)
 # Intersect each upper-arm surface triangle with the near plane; reject offscreen crossings.
 tris=points[upper_faces];x=tris[:,:,0];candidates=tris[(x.min(1)<=1)&(x.max(1)>=1)]
 crossed=0
 for tri in candidates:
  if len(clip_poly(list(tri),planes(th,tv)))>=3:crossed+=1
 return dict(cap_intersections=exposed,near_plane_triangles=crossed,
  cap_bottom_clearance_cm=float(-(p[:,2]+tv*p[:,0]).max()/math.sqrt(1+tv*tv)),
  nearest_visible_upper_vertex_cm=float(distance[visible].min()) if visible.any() else None,
  nearest_upper_vertex_cm=float(distance.min()),visible_upper_vertices=int(visible.sum()))
def main():
 geo=init();manifest=read(C/'capture_manifest.json');results=[];native_error=0.;pose_count=0
 views=[('default_75vfov_16x9',16/9,manifest['horizontal_fovs'][0]),('wide_112hfov_1276x837',1276/837,112)]
 for key in manifest['cases']:
  case=read(C/(key+'.json'));mf=matrix(case['mesh_frame']);worst=[]
  for label,aspect,hfov in views:
   worst.append(dict(view=label,cap_failures=[],near_failures=[],minimum_distance_cm=1e9,minimum_clearance_cm=1e9,closest_frame=None,clearance_frame=None))
  for s in case['samples']:
   posed=skin(s['bones'],root_only='native_skinned' not in s);pose_count+=1
   if 'native_skinned' in s:native_error=max(native_error,float(np.linalg.norm(posed-np.asarray(s['native_skinned']),axis=1).max()))
   for j,(label,aspect,hfov) in enumerate(views):
    cp=transform(posed,np.linalg.inv(matrix(s['cameras'][j]))@mf);th=math.tan(math.radians(hfov/2));tv=th/aspect
    m=measure(cp,th,tv);w=worst[j]
    if m['cap_intersections']:w['cap_failures'].append(s['frame'])
    if m['near_plane_triangles']:w['near_failures'].append(s['frame'])
    if m['nearest_visible_upper_vertex_cm'] is not None and m['nearest_visible_upper_vertex_cm']<w['minimum_distance_cm']:
     w['minimum_distance_cm']=m['nearest_visible_upper_vertex_cm'];w['closest_frame']=s['frame']
    if m['cap_bottom_clearance_cm']<w['minimum_clearance_cm']:
     w['minimum_clearance_cm']=m['cap_bottom_clearance_cm'];w['clearance_frame']=s['frame']
  row=dict(key=key,samples=len(case['samples']),views=worst);results.append(row)
  print(key,[(w['view'],len(w['cap_failures']),len(w['near_failures']),round(w['minimum_distance_cm'],3),round(w['minimum_clearance_cm'],3)) for w in worst],flush=True)
 report=dict(geometry=geo,poses=pose_count,views=views,native_skin_max_error_cm=native_error,cases=results,scope='Saved LOD0 bare mesh, production native animation graph and action-camera layer; standing hip reload. No PIE.',assets_modified=False)
 (O/'analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('ANALYSIS',pose_count,'native_error_cm',native_error,geo,flush=True)
if __name__=='__main__':main()
