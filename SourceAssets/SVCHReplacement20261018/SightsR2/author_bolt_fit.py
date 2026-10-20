"""Correct the measured bolt bind offset; keep source clips and local hand poses."""
import copy,json,gzip
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
O=Path(__file__).parent;P=O.parents[2]
env={'__file__':str(O/'compare_mechanics_offline.py')}
exec(compile((O/'compare_mechanics_offline.py').read_text().split('report={}')[0],'mechanics_inputs','exec'),env)
motion,rest,ids,parents,matrices=[env[k] for k in ('motion','rest','ids','parents','matrices')]
profile=env['profile'];out=copy.deepcopy(profile)
capture=P/'Saved/SVCHPoseAudit/svch-sights-r2-20261019-a2/posed_geometry.json'
vertices=[v for v in json.loads(capture.read_text())['moved_gun_vertices'] if v['bone']=='WPN_bolt']
deltas=np.asarray([v['rest'] for v in vertices])-np.asarray([v['posed_bind'] for v in vertices])
delta=deltas.mean(0);scatter=float(np.linalg.norm(deltas-delta,axis=1).max())
assert len(vertices)==857 and scatter<.0001
def old_pose(base,clip,t):
 row=base.copy()
 for track in clip['tracks']:
  i=ids[track['bone']];ts=np.asarray(track['times']);vs=np.asarray(track['values']).reshape(-1,10)
  if len(ts)==1:v=vs[0]
  else:
   j=int(np.clip(np.searchsorted(ts,t)-1,0,len(ts)-2));w=np.clip((t-ts[j])/(ts[j+1]-ts[j]),0,1)
   v=vs[j]*(1-w)+vs[j+1]*w;v[3:7]=Slerp([0,1],R.from_quat(vs[j:j+2,3:7]))([w]).as_quat()[0]
  row[i,:3]+=v[:3];row[i,3:7]=(R.from_quat(v[3:7])*R.from_quat(base[i,3:7])).as_quat();row[i,7:]+=v[7:]
 return row
def ease(a,b,t):
 x=np.clip((t-a)/(b-a),0,1);return x*x*x*(10-15*x+6*x*x)
c=motion['clips']['reload_empty'];before=next(x for x in profile['clips'] if x['base']==c['path']);after=next(x for x in out['clips'] if x['base']==c['path'])
track=next(x for x in after['tracks'] if x['bone']=='clavicle_r');values=np.asarray(track['values']).reshape(-1,10).copy();old=values.copy()
assert np.allclose(track['times'],c['times'])
ci=ids['clavicle_r'];bi=ids['WPN_bolt'];contact_errors=[];affected=0
for frame_index,t in enumerate(c['times']):
 w=float(ease(260,286,t*120)*(1-ease(350,400,t*120)))
 if w==0:continue
 world=matrices(old_pose(np.asarray(c['frames'][frame_index]),before,t))
 for i,p in enumerate(parents):
  if p>=0:world[i]=world[p]@world[i]
 shift=(world[bi]@np.linalg.inv(rest[bi]))[:3,:3]@delta
 local=np.linalg.solve(world[parents[ci]][:3,:3],shift)*w
 values[frame_index,:3]+=local;affected+=1
 if w>.999999:contact_errors.append(float(np.linalg.norm(world[parents[ci]][:3,:3]@local-shift)))
track['values']=values.ravel().tolist()
assert np.array_equal(values[:,3:],old[:,3:])
for a,b in zip(profile['clips'],out['clips']):
 if a['base']!=c['path']:assert a==b
 else:
  assert all(x==y for x,y in zip(a['tracks'],b['tracks']) if x['bone']!='clavicle_r')
(O/'profile_bolt_fit.json').write_text(json.dumps(out,separators=(',',':')))
receipt={'delta_component_cm':delta.tolist(),'runtime_vertex_pairs':len(vertices),'translation_fit_max_error_cm':scatter,'changed_source_bone':'WPN_bolt','changed_vertices':857,'source_animation_assets_changed':False,'V9_mesh_changed':False,'wrist_finger_local_tracks_changed':False,'profile_change':'reload_empty clavicle_r translation only, same contact blend window 260-286 / 350-400','changed_profile_samples':affected,'full_contact_relative_offset_error_cm':max(contact_errors),'other_clips_unchanged':True,'magazine_and_trigger_binding_unchanged':True}
(O/'bolt_fit_recipe.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
