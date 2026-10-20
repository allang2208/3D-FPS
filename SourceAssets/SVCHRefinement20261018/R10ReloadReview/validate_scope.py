"""Scope, native-joint preservation and magazine-contact stability for the requested review."""
import hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip';P=O.parents[2]
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
final=json.loads((O/'profile_native_registration.json').read_text());before=json.loads((R9/'profile_reload_grip.json').read_text())
native=json.loads((R9/'Inputs/profile_before.json').read_text());manifest=json.loads((R9/'Inputs/manifest.json').read_text())
report={'source_hashes':{},'clips':{},'preserved_other_clips':0}
planes=np.unique(np.round(ConvexHull(mag['svch'][0]).equations,8),axis=0)
for key,spec in manifest.items():
 if key=='profile':continue
 disk=P/'Content'/(spec['path'].removeprefix('/Game/')+'.uasset')
 report['source_hashes'][key]=hashlib.sha256(disk.read_bytes()).hexdigest()==spec['sha256']
 assert report['source_hashes'][key], 'Changed source '+key
roles={v['path']:k for k,v in motion['clips'].items() if k!='idle'}
for a,b in zip(before['clips'],final['clips']):
 if a['base'] not in roles:
  assert a==b;report['preserved_other_clips']+=1;continue
 role=roles[a['base']];clip=motion['clips'][role];n=next(c for c in native['clips'] if c['base']==a['base'])
 keep=lambda c:[t for t in c['tracks'] if t['bone'] not in left_chain]
 assert keep(a)==keep(b) and a['duration']==b['duration']
 max_rotation=0.;max_position=0.;relative=[];hand_points=[];envelope=[]
 for i,time in enumerate(clip['times']):
  base=np.asarray(clip['frames'][i]);old=old_pose(base,n,time);new=old_pose(base,b,time)
  for name in left_chain:
   if name=='clavicle_l':continue
   j=NI[name]
   max_rotation=max(max_rotation,float(np.rad2deg((R.from_quat(new[j,3:7])*R.from_quat(old[j,3:7]).inv()).magnitude())))
   max_position=max(max_position,float(np.linalg.norm(new[j,:3]-old[j,:3])))
  world=comp(matrices(new));hand_points.append(world[HAND,:3,3])
  if 12<=i<=302:
   contact=points(np.linalg.inv(rigid(world[MAG])),skin(world,HANDIDS))
   signed=np.max(contact@planes[:,:3].T+planes[:,3],axis=1)
   envelope.append({'frame':i,'min_signed_mm':float(signed.min()*10)})
  if 49<=i<=244:relative.append(np.linalg.inv(rigid(world[MAG]))@rigid(world[HAND]))
 center=relative[0];drift=max(np.linalg.norm(m[:3,3]-center[:3,3])*10 for m in relative)
 rot=max(np.rad2deg((R.from_matrix(m[:3,:3])*R.from_matrix(center[:3,:3]).inv()).magnitude()) for m in relative)
 report['clips'][role]={'frames':len(clip['times']),'native_local_rotation_error_deg':max_rotation,
  'native_local_translation_error':max_position,'held_wrist_magazine_position_drift_mm':float(drift),
  'held_wrist_magazine_rotation_drift_deg':float(rot),'maximum_wrist_frame_step_cm':float(np.max(np.linalg.norm(np.diff(hand_points,axis=0),axis=1))),
  'magazine_envelope':envelope}
 assert max_rotation<.001 and max_position<.000001
(O/'scope_and_stability.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:{a:b for a,b in v.items() if a!='magazine_envelope'} for k,v in report['clips'].items()}),flush=True)
print('ENVELOPE_WORST',json.dumps({k:min(v['magazine_envelope'],key=lambda x:x['min_signed_mm']) for k,v in report['clips'].items()}),flush=True)
