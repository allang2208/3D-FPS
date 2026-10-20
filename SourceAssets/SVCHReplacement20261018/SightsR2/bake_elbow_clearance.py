"""Bake a local avoidance profile with unchanged cylindrical-handle contact."""
import runpy,json,copy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import maximum_filter1d,gaussian_filter1d
O=Path(__file__).parent;e=runpy.run_path(str(O/'author_elbow_clearance.py'))
globals().update({k:v for k,v in e.items() if k not in ('O','__name__','__file__','__builtins__')})
keyframes=np.arange(260,401,4);angles=[];unresolved=[]
for frame in keyframes:
 old,_=world_at(frame);support,_=world_at(frame,source_clip);target=grip_target(old,0.,frame);found=[]
 for angle in np.arange(0.,36.1,1.):
  p=solve(old,angle,target=target,support=support);dist=np.concatenate([clearance(p,fore),clearance(p,hand_ids)])
  found.append((float(dist.min()),float(angle)))
  if dist.min()>=.25:break
 if found[-1][0]<.25:
  unresolved.append({'frame':int(frame),'best_clearance_cm':max(found)[0]});chosen=max(found)[1]
 else:chosen=found[-1][1]
 angles.append(chosen)
if unresolved:print('UNCLEARED',json.dumps(unresolved),flush=True)
wide=maximum_filter1d(np.asarray(angles),size=3,mode='nearest');smooth=gaussian_filter1d(wide,sigma=.65,mode='nearest');smooth[0]=smooth[-1]=0
curve=PchipInterpolator(keyframes,smooth,extrapolate=False)
out=copy.deepcopy(profile);dst=next(x for x in out['clips'] if x['base']==c['path'])
changed=[names[ci]]+[n for n in names if n.endswith('_r') and n.startswith(('upperarm','lowerarm'))]+['hand_r'];values={n:[] for n in changed};max_hand_error=0.;max_rotation_error=0.;max_elbow_offset=0.;max_bone_error=0.;sample_clearance=[]
for index,t in enumerate(c['times']):
 frame=float(t*120);old,_=world_at(frame);support,_=world_at(frame,source_clip);target=grip_target(old,0.,frame)
 angle=float(curve(np.clip(frame,260,400))) if 260<frame<400 else 0.
 p=solve(old,angle,target=target,support=support)
 max_elbow_offset=max(max_elbow_offset,float(np.linalg.norm(p[li,:3,3]-support[li,:3,3])))
 max_rotation_error=max(max_rotation_error,float((R.from_matrix(rigid(p[hi])[:3,:3])*R.from_matrix(rigid(old[hi])[:3,:3]).inv()).magnitude()))
 if 304<=frame<=344:max_hand_error=max(max_hand_error,float(np.linalg.norm(p[hi,:3,3]-old[hi,:3,3])))
 for start,end in [(ui,li),(li,hi)]:max_bone_error=max(max_bone_error,abs(float(np.linalg.norm(p[end,:3,3]-p[start,:3,3])-np.linalg.norm(old[end,:3,3]-old[start,:3,3]))))
 if 274<=frame<=375 and index%2==0:sample_clearance.append(float(np.concatenate([clearance(p,fore),clearance(p,hand_ids)]).min()))
 base=np.asarray(c['frames'][index])
 for name in changed:
  i=ids[name];local=np.linalg.solve(p[parents[i]],p[i]);scale=np.linalg.norm(local[:3,:3],axis=0);q=(R.from_matrix(local[:3,:3]/scale)*R.from_quat(base[i,3:7]).inv()).as_quat()
  v=np.r_[local[:3,3]-base[i,:3],q,scale-base[i,7:10]]
  if values[name] and np.dot(values[name][-1][3:7],v[3:7])<0:v[3:7]*=-1
  values[name].append(v.tolist())
dst['tracks']=[x for x in dst['tracks'] if x['bone'] not in changed]+[{'bone':n,'times':c['times'],'values':np.round(values[n],10).ravel().tolist()} for n in changed]
assert all(a==b for a,b in zip(profile['clips'],out['clips']) if a['base']!=c['path'])
assert max_hand_error<1e-6 and max_rotation_error<1e-6 and max_bone_error<1e-5
receipt={'rear_shift_component_cm':[0.,6.5,0.],'changed_clip':'reload_empty','changed_tracks':changed,'source_animation_assets_changed':False,'V9_changed':False,'finger_local_tracks_changed':False,'palm_rotation_error_deg':float(np.rad2deg(max_rotation_error)),'full_contact_position_error_cm':max_hand_error,'bone_length_error_cm':max_bone_error,'max_elbow_offset_from_source_cm':max_elbow_offset,'max_pole_angle_deg':float(smooth.max()),'approach_offset_cm':6.,'release_offset_cm':3.,'approach_window_frames':[268,280,304],'release_window_frames':[344,346,375],'proxy_min_clearance_cm':min(sample_clearance),'unresolved_proxy_keys':unresolved,'keyframes':keyframes.tolist(),'angles':smooth.tolist(),'clocks_preserved':True}
(O/'profile_elbow_clearance.json').write_text(json.dumps(out,separators=(',',':')));(O/'elbow_clearance_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k not in ('keyframes','angles')},indent=2))
