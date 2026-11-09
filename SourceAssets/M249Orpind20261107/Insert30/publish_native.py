"""Author from the actual animation-graph pose, preserving the exact wrist."""
from common import *
import json,gzip,copy
from scipy.interpolate import PchipInterpolator
scope={'__file__':str(r/'candidate.py')}
exec(compile((r/'candidate.py').read_text().split("for path,c in d['clips'].items():")[0],str(r/'candidate.py'),'exec'),scope)
solve=scope['solve'];report={}
moving=[ix[n]for n in ['upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l']]
for family,p in d['profiles'].items():
 clips=[]
 for empty in [False,True]:
  folder=r/'before'/f'{"30" if family=="base" else "45"}_{"empty" if empty else "normal"}_{family}'
  j=json.loads((folder/'review.json').read_text());path=j['clip'];c=d['clips'][path]
  a=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+j['bone_count']*7);t=a[:,1].astype(float);bone=a[:,4:].reshape(-1,j['bone_count'],7)
  # The native pose stream omits scale. This imported skeleton has a 100x
  # component scale; recover it before converting component centimetres
  # back into local translations for additive profile tracks.
  component_scale=np.array([np.linalg.norm(matrix(v)[:3,:3],axis=0)for v in d['bind']])
  w=np.zeros((len(a),len(names),4,4));w[:,:,:3,:3]=R.from_quat(bone[:,:,3:7].reshape(-1,4)).as_matrix().reshape(len(a),len(names),3,3)*component_scale[None,:,None,:];w[:,:,:3,3]=bone[:,:,:3];w[:,:,3,3]=1
  after,gain=solve(w.copy(),t,empty);before_local=encode(w);after_local=encode(after)
  begin=1.8;end=3.14 if empty else 3.5;mask=(t>begin)&(t<end)
  # Native float source clocks are used directly; no raw/compressed clock mix.
  ts=np.r_[begin,t[mask],end]
  old=next(row for row in p['clips']if row['base']==path);clip=copy.deepcopy(old);clip.pop('retained',None)
  for i in moving:
   rv=(R.from_quat(after_local[:,i,3:7])*R.from_quat(before_local[:,i,3:7]).inv()).as_rotvec();dp=after_local[:,i,:3]-before_local[:,i,:3]
   vr=np.concatenate((np.zeros((1,3)),rv[mask],np.zeros((1,3))));vp=np.concatenate((np.zeros((1,3)),dp[mask],np.zeros((1,3))))
   track=next((q for q in clip['tracks']if q['bone']==names[i]),None)
   if track is None:track=dict(bone=names[i],times=[0.,c['duration']],values=[0,0,0,0,0,0,1,0,0,0]*2);clip['tracks'].append(track)
   alltimes=np.unique(np.asarray([*track['times'],*ts],np.float32)).astype(float);v=sample(track,alltimes);inside=(alltimes>begin)&(alltimes<end)
   spin=np.zeros((len(alltimes),3));shift=spin.copy();spin[inside]=PchipInterpolator(ts,vr,axis=0)(alltimes[inside]);shift[inside]=PchipInterpolator(ts,vp,axis=0)(alltimes[inside])
   v[:,:3]+=shift;v[:,3:7]=(R.from_rotvec(spin)*R.from_quat(v[:,3:7])).as_quat()
   for k in range(1,len(v)):
    if v[k-1,3:7]@v[k,3:7]<0:v[k,3:7]*=-1
   track['times']=alltimes.tolist();track['values']=v.ravel().tolist()
  clips.append(clip)
  protected=[i for i in range(len(names))if i not in arm_ids[1:7]]
  err=max(float(np.abs(np.linalg.norm(after[:,ix[x],:3,3]-after[:,ix[y],:3,3],axis=1)-np.linalg.norm(w[:,ix[x],:3,3]-w[:,ix[y],:3,3],axis=1)).max())for x,y in [('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')])
  metrics={}
  for n in ['upperarm_l','lowerarm_l']:
   vals=[]
   for pose in [w,after]:
    q=R.from_matrix(pose[:,ix[n],:3,:3]);step=np.degrees((q[:-1].inv()*q[1:]).magnitude());vals.append(float(step[(t[:-1]>=2.3)&(t[:-1]<=3.14)].max()))
   metrics[n]=vals
  key=family+'/'+path.split('.')[-1];report[key]=dict(arm_length_error_cm=err,protected_world_error=float(np.abs(w[:,protected]-after[:,protected]).max()),hand_world_error=float(np.abs(w[:,ix['hand_l']]-after[:,ix['hand_l']]).max()),source_begin=begin,source_end=end,native_keys=int(mask.sum()),rotation_step_deg=metrics)
  print(key,metrics,flush=True)
 with gzip.open(r/(family+'.json.gz'),'wt')as f:json.dump(dict(family=family,clips=clips),f,separators=(',',':'))
(r/'publication.json').write_text(json.dumps(report,indent=2))
assert len(report)==10 and all(v['arm_length_error_cm']<1e-6 and v['protected_world_error']<1e-9 for v in report.values())
