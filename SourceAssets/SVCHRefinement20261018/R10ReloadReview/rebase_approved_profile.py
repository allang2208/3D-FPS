"""Preserve the approved final poses when a parallel task changes shared source helpers."""
import copy,gzip,json
from pathlib import Path
import numpy as np
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
old=json.loads((O.parent/'R7NativeV9/compressed_inputs.json').read_text())
new=json.load(gzip.open(O/'CurrentSource/motion.json.gz','rt'))
approved=json.loads((O/'profile_native_registration.json').read_text());result=copy.deepcopy(approved)
report={'method':'Rebase SVCH-only deltas to preserve approved final local poses; shared source assets remain untouched','clips':{}}
for entry in result['clips']:
 role=next(k for k,c in new['clips'].items() if c['path']==entry['base']);a=np.asarray((motion['clips'][role] if role in ('reload','reload_empty') else old['clips'][role])['frames']);b=np.asarray(new['clips'][role]['frames'])
 assert a.shape==b.shape and abs(entry['duration']-new['clips'][role]['duration'])<.00001
 delta=(R.from_quat(a[:,:,3:7].reshape(-1,4))*R.from_quat(b[:,:,3:7].reshape(-1,4)).inv()).magnitude().reshape(a.shape[:2])
 changed=np.flatnonzero((np.max(delta,axis=0)>np.deg2rad(.0001))| (np.max(abs(a[:,:,:3]-b[:,:,:3]),axis=(0,2))>.000001)| (np.max(abs(a[:,:,7:]-b[:,:,7:]),axis=(0,2))>.000001))
 desired=np.asarray([old_pose(row,entry,t) for row,t in zip(a,new['clips'][role]['times'])])
 tracks=[];max_error=0.
 for j in changed:
  q=R.from_quat(desired[:,j,3:7])*R.from_quat(b[:,j,3:7]).inv();values=np.c_[desired[:,j,:3]-b[:,j,:3],q.as_quat(),desired[:,j,7:]-b[:,j,7:]]
  for i in range(1,len(values)):
   if values[i-1,3:7]@values[i,3:7]<0:values[i,3:7]*=-1
  tracks.append({'bone':N[j],'times':new['clips'][role]['times'],'values':np.round(values,10).ravel().tolist()})
 changed_names={N[j] for j in changed};entry['tracks']=[t for t in entry['tracks'] if t['bone'] not in changed_names]+tracks
 for i,t in enumerate(new['clips'][role]['times']):
  reconstructed=old_pose(b[i],entry,t)
  error=np.rad2deg((R.from_quat(reconstructed[:,3:7])*R.from_quat(desired[i,:,3:7]).inv()).magnitude()).max();max_error=max(max_error,float(error))
  assert np.max(abs(reconstructed[:,:3]-desired[i,:,:3]))<.00001
 assert max_error<.001
 report['clips'][role]={'rebased_bones':sorted(changed_names),'max_final_local_rotation_error_deg':max_error,'source_sha256':new['clips'][role]['sha256']}
 print('SVCH_PROFILE_REBASED',role,len(changed_names),max_error,flush=True)
(O/'profile_runtime_rebased.json').write_text(json.dumps(result,separators=(',',':')))
(O/'source_rebase_receipt.json').write_text(json.dumps(report,indent=2))
