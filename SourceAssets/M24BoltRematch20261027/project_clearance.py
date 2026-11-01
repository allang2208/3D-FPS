"""Small whole-hand clearance correction after preserving the original finger gesture."""
from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'refine_motion.py').read_text().split('# Fit one source stroke')[0],'fit_library','exec'))
data=json.loads((O/'refined_poses.json').read_text());clips={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in data.items()}
report={}
for role in ('fire','cycle'):
 shift=0 if role=='fire' else 4;report[role]=[]
 for f,row in enumerate(clips[role]):
  t=f-shift
  if not 11<=t<=46:continue
  P=points(row)[np.where(hm)[0][::2]];G=np.array((row['WPN_root']@rest['WPN_root'].inverted()).to_3x3());inv=np.array(rest['WPN_BoltHandle']@row['WPN_BoltHandle'].inverted())
  def score(x):
   Q=P+G@x;ds=actual(row,Q,False,major);B=Q@inv[:3,:3].T+inv[:3,3];ds['bolt']=np.minimum(*[np.max(B@N.T-D,axis=1) for N,D in bolt_hulls])
   pen=np.concatenate([np.maximum(.0005-d,0)*1000 for d in ds.values()]);return np.sum(pen*pen)*30+np.sum((x/.003)**2)
  x=np.zeros(3);best=score(x)
  for step in (.004,.002,.001):
   for _ in range(5):
    changed=False
    for i in range(3):
     for sign in (-1,1):
      y=x.copy();y[i]=np.clip(y[i]+sign*step,-.014,.018);loss=score(y)
      if loss<best:x=y;best=loss;changed=True
    if not changed:break
  for n in ['hand_r',*digits]:row[n].translation+=Vector(G@x)
  apply_arm(row,'r',0.)
  report[role].append({'frame':f,'translation_m':x.tolist(),'cost':best})
for role in ('reload_empty','reload_empty_mag10'):
 for f,row in enumerate(clips[role]):
  i=f-48
  if 0<=i<len(clips['cycle']):
   src=clips['cycle'][i];D=row['WPN_root']@src['WPN_root'].inverted()
   for n in row:
    if under(n,'clavicle_r'):row[n]=D@src[n]
(O/'refined_poses.json').write_text(json.dumps({role:[{n:[list(v) for v in m] for n,m in row.items()} for row in rows] for role,rows in clips.items()}))
(O/'clearance_projection.json').write_text(json.dumps(report,indent=2));print('CLEARANCE_SAVED',flush=True)
