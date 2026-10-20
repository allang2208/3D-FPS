from arm_math import *
from collections import Counter
tri=np.asarray(arms['triangles']);edges=Counter(tuple(sorted((int(t[i]),int(t[(i+1)%3])))) for t in tri for i in range(3))
boundary=np.unique([v for e,c in edges.items() if c==1 for v in e]);root_ids=np.intersect1d(boundary,upper)
print('Left root boundary vertices',len(root_ids),{names[b]:int((dom[root_ids]==b).sum()) for b in np.unique(dom[root_ids])},flush=True)
# This initial camera estimate comes from the earlier actual SVCh empty-reload
# capture. Final authoring uses this task's fresh runtime camera records.
cam=camera_transform([5.5579209855,4.37249,-7.56],[.0047568,9.882342,89.992188])
ci,ui,li,hi,tw=[ids[n] for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l','lowerarm_twist_01_l')]
ref=matrices(arms['reference']);rel0=R.from_matrix(rigid(ref[li])[:3,:3]).inv()*R.from_matrix(rigid(ref[hi])[:3,:3])
axis0=R.from_matrix(rigid(ref[li])[:3,:3]).inv().apply(unit(ref[hi,:3,3]-ref[li,:3,3]))
rows=[]
for role in ('reload','reload_empty'):
 for f in range(0,len(motion['clips'][role]['times']),12):
  p=pose(role,f);u,e,h=[p[j,:3,3] for j in (ui,li,hi)];campts=transform(cam,skin(p,upper));roots=transform(cam,skin(p,root_ids))
  q=(R.from_matrix(rigid(p[li])[:3,:3]).inv()*R.from_matrix(rigid(p[hi])[:3,:3])*rel0.inv()).as_quat()
  if q[3]<0:q=-q
  roll=2*np.rad2deg(np.arctan2(q[:3]@axis0,q[3]));screen=(campts[:,0]>.01)&(abs(campts[:,1])<campts[:,0])&(abs(campts[:,2])<campts[:,0]*.5625)
  root_screen=(roots[:,0]>.01)&(abs(roots[:,1])<roots[:,0])&(abs(roots[:,2])<roots[:,0]*.5625)
  row={'role':role,'frame':f,'elbow_deg':float(np.rad2deg(np.arccos(np.clip(unit(e-u)@unit(h-e),-1,1)))),'wrist_axial_deg':float(roll),'shoulder_camera_cm':transform(cam,u).tolist(),'elbow_camera_cm':transform(cam,e).tolist(),'root_in_screen':int(root_screen.sum()),'upper_nearest_visible_cm':float(np.linalg.norm(campts[screen],axis=1).min()) if screen.any() else None}
  rows.append(row)
(O/'diagnosis_initial.json').write_text(json.dumps({'camera':'earlier runtime estimate; not final fresh capture','root_ids':root_ids.tolist(),'rows':rows},indent=2))
for role in ('reload','reload_empty'):
 subset=[r for r in rows if r['role']==role]
 print(role,'max root onscreen',max(r['root_in_screen'] for r in subset),'wrist roll range',[min(r['wrist_axial_deg'] for r in subset),max(r['wrist_axial_deg'] for r in subset)])
 print(json.dumps([r for r in subset if r['frame'] in (24,60,120,180,240,300,360)],indent=2))
