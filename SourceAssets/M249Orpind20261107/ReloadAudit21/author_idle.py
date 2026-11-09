from pathlib import Path
import pickle,json,gzip,numpy as np
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;prev=r.parent/'Repair20';s={'__file__':str(prev/'author.py')};exec(compile((prev/'author.py').read_text().split("outdir=r/'Motion'")[0],str(prev/'author.py'),'exec'),s)
d=pickle.load(open(r/'idle_raw.pkl','rb'));s['d']=d;names=d['names'];ix={n:i for i,n in enumerate(names)};path,c=next(iter(d['clips'].items()));a=np.array(c['frames']);times=np.arange(len(a))/120;selected=[i for i,n in enumerate(names) if n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky')) and n.endswith(('_l','_r'))];report={}
for family in d['profiles']:
 w=s['world'](s['layer'](a,path,family,times));goal=w[60].copy()
 for side in ['l','r']:
  b,bn=s['binding'](side);ids=[ix[n] for n in bn];s['hinge'].CAP=np.radians(110.);solved,info=s['hinge'].solve(goal[None,ids],b)
  for j in range(1,7):goal[ids[j]]=solved[0][j]
 raw=s['world'](a);result=raw.copy();root=ix['WPN_root'];reference=np.linalg.inv(goal[root])
 for k in range(len(times)):
  xf=raw[k,root]@reference
  for i in selected:result[k,i]=xf@goal[i]
 local=s['encode'](result);tracks=[]
 for i in selected:
  v=np.zeros((len(times),10));v[:,:3]=local[:,i,:3]-a[:,i,:3];v[:,3:7]=(R.from_quat(local[:,i,3:7])*R.from_quat(a[:,i,3:7]).inv()).as_quat();v[:,7:]=local[:,i,7:]-a[:,i,7:]
  for k in range(1,len(v)):
   if v[k-1,3:7]@v[k,3:7]<0:v[k,3:7]*=-1
  if np.max(abs(v-[0,0,0,0,0,0,1,0,0,0]))>1.e-6:tracks.append(dict(bone=names[i],times=times.tolist(),values=v.ravel().tolist()))
 with gzip.open(r/('idle_'+family+'.json.gz'),'wt') as f:json.dump(dict(family=family,clips=[dict(base=path.split('.')[0],duration=c['duration'],tracks=tracks)]),f,separators=(',',':'))
 report[family]=dict(loop_position_error_cm=float(np.max(abs(result[-1,selected,:3,3]-result[0,selected,:3,3]))),tracks=len(tracks))
(r/'idle_authoring.json').write_text(json.dumps(report,indent=2));print(report)
