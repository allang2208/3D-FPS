from arm_math import *
from collections import Counter,defaultdict
ui,li,hi,ci=[ids[n] for n in ('upperarm_l','lowerarm_l','hand_l','clavicle_l')]
ref=matrices(arms['reference']);axis0=unit(ref[li,:3,3]-ref[ui,:3,3]);l1=np.linalg.norm(ref[li,:3,3]-ref[ui,:3,3]);s=(V-ref[ui,:3,3])@axis0/l1
# Proximal root and its adjacent skin, not the whole upper-arm muscle belly.
# Weld only for boundary identification: UE source vertices are split at UV and
# material seams, which must not be mistaken for holes in the accepted V9 mesh.
_,weld=np.unique(np.round(V,5),axis=0,return_inverse=True)
tris=weld[np.asarray(arms['triangles'])]
edges=Counter(tuple(sorted((int(t[i]),int(t[(i+1)%3])))) for t in tris for i in range(3) if t[i]!=t[(i+1)%3])
boundary=np.unique([v for e,count in edges.items() if count==1 for v in e])
boundary_original=np.flatnonzero(np.isin(weld,boundary))
left_open_boundary=np.intersect1d(boundary_original,upper)
rootband=np.unique(np.r_[upper[s[upper]<.20],left_open_boundary])
capture=O.parents[2]/'Saved/SVCHPoseAudit/svch-left-reload-20261019-before'
handoff=[json.loads(x) for x in (capture/'handoff.jsonl').read_text().splitlines()]
frames=[json.loads(x) for x in (capture/'frames.jsonl').read_text().splitlines()]
fov=frames[0]['fov'];tx=np.tan(np.deg2rad(fov/2));ty=tx*9/16
def cam_at(role,frame):
 stage='normal' if role=='reload' else 'empty';rows=[r for r in handoff if r['stage']==stage and r['reloading'] and r['action_alpha']>.99]
 row=min(rows,key=lambda r:abs(r['source_time']*120-frame));return camera_transform(row['component_location'],row['component_rotation'])
def rotate_arm(p,angle):
 out=p.copy();E,H=p[li,:3,3],p[hi,:3,3];axis=unit(H-E);q=R.from_rotvec(axis*np.deg2rad(angle));T=np.eye(4);T[:3,:3]=q.as_matrix();T[:3,3]=E-q.apply(E)
 for i,n in enumerate(names):
  if n=='clavicle_l' or (n.endswith('_l') and n.startswith('upperarm')) or n=='lowerarm_l':out[i]=T@p[i]
 # Keep the wrist-end helper and palm fixed. Split only the axial change across
 # the forearm; no scaling, no joint translation, no new hand/finger motion.
 j=ids['lowerarm_twist_02_l'];out[j,:3,:3]=R.from_rotvec(axis*np.deg2rad(angle*.5)).as_matrix()@p[j,:3,:3]
 return out
def visible_margin(p,cam,selected=rootband):
 pts=transform(cam,skin(p,selected));dep=np.maximum(pts[:,0],.001);xy=pts[:,1:]/dep[:,None]/[tx,ty]
 margin=np.maximum(abs(xy[:,0]),abs(xy[:,1]))-1
 margin[pts[:,0]<1.]=2
 return margin,pts
if __name__=='__main__':
 report=[]
 for role in ['reload','reload_empty']:
  for f in [0,24,60,144,172,200,240,264,280,300,320,340,360]:
   p=pose(role,f);cam=cam_at(role,f);choices=[]
   for angle in np.arange(-90,91,5):
    q=rotate_arm(p,angle);margin,pts=visible_margin(q,cam);choices.append((float(np.maximum(.08-margin,0).max()),int(angle),int((margin<0).sum())))
   good=[a for a in choices if a[0]<=0];best=min(good,key=lambda a:abs(a[1])) if good else min(choices)
   zero=next(a for a in choices if a[1]==0);row={'role':role,'frame':f,'before':zero,'best':best,'positive_60':next(a for a in choices if a[1]==60)};report.append(row);print(row,flush=True)
 (O/'roll_scan.json').write_text(json.dumps({'rootband_vertices':len(rootband),'fov':fov,'rows':report},indent=2))
