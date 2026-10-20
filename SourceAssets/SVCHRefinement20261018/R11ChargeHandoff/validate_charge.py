import gzip,json
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
import trimesh
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip';R10=O.parent/'R10ReloadReview'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
motion=json.load(gzip.open(O/'CurrentSource/motion.json.gz','rt'));old=json.loads((R10/'profile_native_registration.json').read_text());new=json.loads((O/'profile_charge.json').read_text())
unchanged=0
for a,b in zip(old['clips'],new['clips']):
 assert a['base']==b['base'] and a['duration']==b['duration']
 if a['base'].endswith('_reload_empty'):
  keep=lambda c:[t for t in c['tracks'] if t['bone']!='clavicle_r'];assert keep(a)==keep(b)
 else:assert a==b;unchanged+=1
clip=motion['clips']['reload_empty'];a=next(c for c in old['clips'] if c['base']==clip['path']);b=next(c for c in new['clips'] if c['base']==clip['path'])
bolt=NI['WPN_bolt'];hand=NI['hand_r'];positions=[];positions_before=[];max_local=0.;window_error=0.;relations=[];samples=[];transition_samples=[]
v,t=geom('svch',lambda n:'BoltCarrier' in n);parts=trimesh.Trimesh(vertices=v,faces=t,process=True).split(only_watertight=False)
knob=max((m for m in parts if len(m.faces)>50),key=lambda m:m.centroid[0]);kv=points(np.linalg.inv(rigid(rest['svch'][bolt])),knob.vertices)
mesh=trimesh.Trimesh(vertices=kv,faces=knob.faces,process=True);planes=np.unique(np.round(ConvexHull(kv).equations,8),axis=0)
ids=np.flatnonzero(np.array([N[d].endswith('_r') and N[d].startswith(('hand_','thumb','index','middle','ring','pinky')) for d in DOM]))
for i,time in enumerate(clip['times']):
 base=np.asarray(clip['frames'][i]);la=old_pose(base,a,time);lb=old_pose(base,b,time)
 keep=[j for j,n in enumerate(N) if n!='clavicle_r'];max_local=max(max_local,float(np.max(abs(la[keep]-lb[keep]))))
 wa,wb=comp(matrices(la)),comp(matrices(lb));positions.append(wb[hand,:3,3]);positions_before.append(wa[hand,:3,3])
 if i<=260 or i>=400:window_error=max(window_error,float(np.linalg.norm(wb[hand,:3,3]-wa[hand,:3,3])))
 if 310<=i<=344:
  relation=np.linalg.inv(rigid(wb[bolt]))@rigid(wb[hand]);relations.append(relation)
 if 260<=i<=400:
  p=points(np.linalg.inv(rigid(wb[bolt])),skin(wb,ids));_,d,_=trimesh.proximity.closest_point(mesh,p)
  signed=np.max(p@planes[:,:3].T+planes[:,3],axis=1)
  sample={'frame':i,'min_distance_mm':float(d.min()*10),'closed_handle_envelope_penetration_mm':float(max(0.,-signed.min())*10)}
  transition_samples.append(sample)
  if 310<=i<=344:samples.append(sample)
ref=relations[0];drift=max(float(np.linalg.norm(x[:3,3]-ref[:3,3])*10) for x in relations)
report={'unchanged_other_clips':unchanged,'evaluated_samples':len(clip['times']),
 'max_non_clavicle_local_difference':max_local,'outside_charge_window_wrist_difference_cm':window_error,
 'hand_bolt_held_position_drift_mm':drift,'charge_samples':samples,'approach_release_samples':transition_samples,
 'max_wrist_step_cm':float(np.linalg.norm(np.diff(positions,axis=0),axis=1).max()),
 'max_previous_wrist_step_cm':float(np.linalg.norm(np.diff(positions_before,axis=0),axis=1).max())}
(O/'charge_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('charge_samples','approach_release_samples')}),flush=True)
print('MAX_ENVELOPE_PENETRATION_MM',max(r['closed_handle_envelope_penetration_mm'] for r in samples),flush=True)
print('MAX_APPROACH_RELEASE_ENVELOPE',max(transition_samples,key=lambda r:r['closed_handle_envelope_penetration_mm']),flush=True)
assert max_local<1e-9 and window_error<.00001 and drift<.1
assert max(r['closed_handle_envelope_penetration_mm'] for r in samples)<.1
