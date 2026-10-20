"""Local shoulder support, with invariant palm/elbow paths and bone lengths.
No source animation or V9 geometry/weights are rewritten.
"""
from scan_forearm_roll import *
import copy
from scipy.ndimage import maximum_filter1d,gaussian_filter1d
from scipy.interpolate import PchipInterpolator
ref=matrices(arms['reference']);fore_ref=R.from_matrix(rigid(ref[li])[:3,:3]);axis_local=fore_ref.inv().apply(unit(ref[hi,:3,3]-ref[li,:3,3]))
def axial(p,j):
 a=R.from_matrix(rigid(p[li])[:3,:3]);b=R.from_matrix(rigid(p[j])[:3,:3]);rest_rel=fore_ref.inv()*R.from_matrix(rigid(ref[j])[:3,:3]);q=(a.inv()*b*rest_rel.inv()).as_quat()
 if q[3]<0:q=-q
 return 2*np.arctan2(q[:3]@axis_local,q[3])
def fix_wrist(p,frame,last):
 # Only remove the axial mismatch at the native near-wrist helper. Flexion,
 # deviation, hand position/orientation, finger locals and all scales stay intact.
 out=p.copy();axis=unit(p[hi,:3,3]-p[li,:3,3]);near=ids['lowerarm_twist_01_l'];mid=ids['lowerarm_twist_02_l']
 diff=np.arctan2(np.sin(axial(p,hi)-axial(p,near)),np.cos(axial(p,hi)-axial(p,near)))
 w=ease(0,18,frame)*(1-ease(last-30,last,frame))
 for j,share in [(near,1.),(mid,.5)]:out[j,:3,:3]=R.from_rotvec(axis*diff*w*share).as_matrix()@p[j,:3,:3]
 return out,float(np.rad2deg(diff*w))
out=copy.deepcopy(profile);report={'method':'Rotate proximal arm around fixed elbow-wrist axis; preserve elbow angle, lengths and world palm. Native V9 unchanged.','clips':{},'runtime_tested':False}
changed=[n for n in names if n=='clavicle_l' or (n.endswith('_l') and n.startswith(('upperarm','lowerarm')))]+['hand_l']
for role in ('reload','reload_empty'):
 c=motion['clips'][role];last=len(c['times'])-1;entry=next(x for x in out['clips'] if x['base']==c['path'])
 keyframes=np.unique(np.r_[np.arange(0,33),np.arange(36,last+1,4),last]);need=[];unresolved=[]
 for frame in keyframes:
  p=pose(role,int(frame));cam=cam_at(role,int(frame));found=[]
  for angle in np.arange(0,-70.1,-2):
   margin,_=visible_margin(rotate_arm(p,angle),cam);pen=float(np.maximum(.03-margin,0).max());found.append((pen,-float(angle)))
   if pen<1e-9:break
  choice=min(found) if found[-1][0]>1e-9 else found[-1]
  need.append(choice[1])
  if choice[0]>.001:unresolved.append({'frame':int(frame),'best_penalty':choice[0]})
 # Smooth a conservative envelope to avoid independently optimized shoulder keys.
 expanded=maximum_filter1d(np.asarray(need),size=7,mode='nearest')
 smooth=gaussian_filter1d(expanded,sigma=1.2,mode='nearest')
 smooth=np.maximum(smooth,np.asarray(need))+2*(np.asarray(need)>0)
 smooth*=ease(0,12,keyframes)*(1-ease(last-30,last,keyframes));smooth[0]=smooth[-1]=0
 curve=PchipInterpolator(keyframes,-smooth)
 values={n:[] for n in changed};stats=[];max_hand=0;max_bone=0;max_elbow=0;max_root_shift=0;max_mismatch=0
 for index,t in enumerate(c['times']):
  p=pose(role,index);angle=float(curve(index));q=rotate_arm(p,angle);q,mismatch=fix_wrist(q,index,last);max_mismatch=max(max_mismatch,abs(mismatch))
  max_hand=max(max_hand,float(np.max(abs(q[hi]-p[hi]))));max_elbow=max(max_elbow,float(np.linalg.norm(q[li,:3,3]-p[li,:3,3])))
  for a,b in [(ui,li),(li,hi),(ci,ui)]:max_bone=max(max_bone,abs(float(np.linalg.norm(q[b,:3,3]-q[a,:3,3])-np.linalg.norm(p[b,:3,3]-p[a,:3,3]))))
  max_root_shift=max(max_root_shift,float(np.linalg.norm(q[ui,:3,3]-p[ui,:3,3])))
  cam=cam_at(role,index);margin,_=visible_margin(q,cam);bm,_=visible_margin(p,cam)
  stats.append({'frame':index,'angle_deg':angle,'root_pixels_before':int((bm<0).sum()),'root_pixels_after':int((margin<0).sum()),'root_margin_after':float(margin.min()),'wrist_axial_correction_deg':mismatch})
  raw=np.asarray(c['frames'][index])
  for n in changed:
   j=ids[n];loc=relative(q[parents[j]],q[j]);scale=np.linalg.norm(loc[:3,:3],axis=0);rot=(R.from_matrix(loc[:3,:3]/scale)*R.from_quat(raw[j,3:7]).inv()).as_quat();v=np.r_[loc[:3,3]-raw[j,:3],rot,scale-raw[j,7:10]]
   if values[n] and values[n][-1][3:7]@v[3:7]<0:v[3:7]*=-1
   values[n].append(v)
 entry['tracks']=[x for x in entry['tracks'] if x['bone'] not in changed]+[{'bone':n,'times':c['times'],'values':np.round(values[n],10).ravel().tolist()} for n in changed]
 assert max_hand<1e-8 and max_bone<1e-5 and max_elbow<1e-8
 endpoint_error=max(float(np.max(abs(pose(role,i,out)-pose(role,i)))) for i in (0,last))
 assert endpoint_error<1e-5
 protected=[j for j,n in enumerate(names) if n.endswith('_r') or n.startswith('WPN_') or (n.endswith('_l') and n.startswith(('hand','thumb','index','middle','ring','pinky')))]
 reconstruction=max(float(np.max(abs(pose(role,i,out)[protected]-pose(role,i)[protected]))) for i in range(last+1))
 print('BAKE_PRESERVATION',role,reconstruction,endpoint_error,flush=True)
 if reconstruction>=1e-5:
  (O/'debug_draft.json').write_text(json.dumps(out,separators=(',',':')))
  errors=[]
  for i in range(last+1):
   delta=np.max(abs(pose(role,i,out)[protected]-pose(role,i)[protected]),axis=(1,2));j=int(delta.argmax());errors.append((float(delta[j]),i,names[protected[j]]))
  print('WORST',max(errors),flush=True)
 assert reconstruction<1e-5
 report['clips'][role]={'max_palm_matrix_error':max_hand,'baked_protected_pose_error':reconstruction,'endpoint_pose_error':endpoint_error,'max_bone_length_error_cm':max_bone,'max_elbow_position_error_cm':max_elbow,'max_shoulder_shift_cm':max_root_shift,'max_shoulder_support_rotation_deg':float(smooth.max()),'max_near_wrist_axial_correction_deg':max_mismatch,'rootband_visible_samples_before':sum(x['root_pixels_before']>0 for x in stats),'rootband_visible_samples_after':sum(x['root_pixels_after']>0 for x in stats),'unresolved_scan':unresolved,'keyframes':keyframes.tolist(),'angles':(-smooth).tolist()}
 (O/(role+'_samples.json')).write_text(json.dumps(stats,indent=2));print(role,json.dumps({k:v for k,v in report['clips'][role].items() if k not in ('keyframes','angles')}),flush=True)
assert all(a==b for a,b in zip(profile['clips'],out['clips']) if a['base'] not in (motion['clips']['reload']['path'],motion['clips']['reload_empty']['path']))
(O/'profile_left_reload.json').write_text(json.dumps(out,separators=(',',':')))
(O/'authoring_receipt.json').write_text(json.dumps(report,indent=2))
print('SVCH_LEFT_RELOAD_PROFILE_AUTHORED',flush=True)
