"""Scoped geometry/contact comparison for the requested embedded-grip repair."""
import json,gzip,sys
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as Rot
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KResonance20261019'
sys.path.insert(0,str(P/'Tools/Saiga12KInspect'))
from pose_math import matrix,rotation,world,apply
rig=json.loads((P/'SourceAssets/Saiga12KInspectClearance20261018/Inputs/runtime-source.json').read_text());names=[b['name'] for b in rig['bones']];parents={b['name']:names[b['parent']] if b['parent']>=0 else None for b in rig['bones']}
old=json.loads((O/'Inputs/profile.json').read_text());new=json.loads((O/'Profiles/DA_angled.json').read_text());frames=json.load(gzip.open(O/'Inputs/poses.json.gz','rt',encoding='utf8'))['clips'];fit=json.loads((O/'Authoring/fit.json').read_text());delta=np.array(fit['offset_root_cm'])
mesh=json.loads((O/'Inputs/grip.json').read_text());v=np.array(mesh['positions']);f=np.array(mesh['triangles']);ids=np.unique(f[np.array(mesh['materials'])==0]);v=v[ids]
g=json.loads((P/'SourceAssets/Saiga12KClosure20261018/Authoring/gun.json').read_text());p=np.array(g['positions']);t=np.array(g['triangles']);h=trimesh.Trimesh(p,t[np.array(g['parts'])=='Handguard'],process=False)
# A vertical ray at each grip vertex measures the actual lower surface. The
# grip body must clear it; the saddle intentionally seats 0.45 mm into it.
unique,inverse=np.unique(np.round(v[:,:2],4),axis=0,return_inverse=True);origins=np.column_stack((unique,np.full(len(unique),-30.)))
hits,ray,_=h.ray.intersects_location(origins,np.tile([0.,0.,1.],(len(origins),1)),multiple_hits=True)
bottom=np.full(len(origins),np.inf);np.minimum.at(bottom,ray,hits[:,2]);depth=v[:,2]-bottom[inverse];valid=np.isfinite(depth)
result={'runtime_tested':False,'old_grip_body_vertices_above_handguard_underside':int((depth[valid]>0).sum()),'old_max_overlap_cm':max(0.,float(depth[valid].max())),'new_min_vertical_clearance_cm':float((-depth[valid]-delta[2]).min()),'clips':[]}
fingers=[n for n in names if n.endswith('_l') and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))]
changed=set(['clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l','ik_hand_l'])
for a,b in zip(old['clips'],new['clips']):
 if a['base']!=b['base'] or a['duration']!=b['duration']:raise RuntimeError('Action routing changed')
 if [t for t in a['tracks'] if t['bone'] not in changed]!=[t for t in b['tracks'] if t['bone'] not in changed]:raise RuntimeError('Unrelated/finger track changed')
 fs=frames[a['base']]['frames'];maxrot=maxerror=maxfinger=0.
 # Inspect full turn at 12 Hz plus all boundaries; production was authored at 120 Hz.
 indices=sorted(set(range(0,len(fs),10))|{len(fs)-1})
 for i in indices:
  f=fs[i];source={n:matrix(v) for n,v in f['local'].items()};wa=world(apply(source,a,f['time']),parents);wb=world(apply(source,b,f['time']),parents)
  ga=np.linalg.inv(wa['WPN_root'])@wa['hand_l'];gb=np.linalg.inv(wb['WPN_root'])@wb['hand_l'];diff=(gb[:3,3]-ga[:3,3])*100
  maxrot=max(maxrot,float(np.degrees((Rot.from_matrix(rotation(ga)).inv()*Rot.from_matrix(rotation(gb))).magnitude())))
  maxerror=max(maxerror,float(np.linalg.norm(diff[:2])))
  for n in fingers:
   ra=np.linalg.inv(wa['hand_l'])@wa[n];rb=np.linalg.inv(wb['hand_l'])@wb[n];maxfinger=max(maxfinger,float(np.max(np.abs(ra-rb))))
 result['clips'].append({'asset':a['base'],'checked_frames':len(indices),'max_palm_orientation_change_degrees':maxrot,'max_lateral_contact_error_cm':maxerror,'max_finger_relative_matrix_error':maxfinger,'unrelated_tracks_identical':True})
result['complete']=True
(O/'Receipts/scoped-check.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='clips'}));print('Max palm orientation drift',max(c['max_palm_orientation_change_degrees'] for c in result['clips']))
