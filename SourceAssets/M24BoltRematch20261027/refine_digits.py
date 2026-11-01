"""Bounded native thumb opposition and terminal flexion at the moving bolt."""
from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'refine_motion.py').read_text().split('# Fit one source stroke')[0],'fit_library','exec'))
input_rows=json.loads((O/'refined_poses.json').read_text())
clips={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in input_rows.items()}
report={}
for role in ('fire','cycle'):
 shift=0 if role=='fire' else 4;report[role]=[];previous=np.zeros(5)
 for f,row in enumerate(clips[role]):
  t=f-shift
  if not 15<=t<=44:continue
  origin=clone(row);H=origin['hand_r'];palm=H.to_3x3()@rest['hand_r'].to_3x3().inverted()@target_frame
  hand_indices=np.where(hm)[0][::2];subW=W[:,hand_indices,:]
  inv=np.array(rest['WPN_BoltHandle']@row['WPN_BoltHandle'].inverted())
  def build(x):
   out=clone(origin)
   for n,axis,deg in [('thumb_01_r',palm.col[2],x[0]),('thumb_01_r',palm.col[0],x[1]),('thumb_02_r',palm.col[1],x[2]),('middle_03_r',palm.col[1],x[3]),('pinky_03_r',palm.col[1],x[4])]:
    p=out[n].translation;D=Matrix.Translation(p)@Quaternion(axis,math.radians(deg)).to_matrix().to_4x4()@Matrix.Translation(-p)
    for child in out:
     if under(child,n):out[child]=D@out[child]
   return out
  def score(x):
   out=build(x);P=np.einsum('kij,kvj->vi',np.array([np.array(out[n]) for n in names]),subW,optimize=True)[:,:3]
   ds=actual(out,P,False,major);B=P@inv[:3,:3].T+inv[:3,3];bd=[np.max(B@N.T-D,axis=1) for N,D in bolt_hulls]
   ds['bolt']=np.minimum(*bd);loss=0
   for n,d in ds.items():
    pen=np.maximum((.0005 if n!='bolt' else .0003)-d,0)*1000;loss+=np.sum(pen*pen)*100
   loss+=np.sum((x/20)**2)*3+np.sum(((x-previous)/20)**2)
   return loss
  x=previous*.7;best=score(x)
  for step in (12,6,3):
   for _ in range(4):
    changed=False
    for i in range(5):
     for sign in (-1,1):
      y=x.copy();y[i]=np.clip(y[i]+step*sign,-38,38);loss=score(y)
      if loss<best:x=y;best=loss;changed=True
    if not changed:break
  previous=x.copy();clips[role][f]=build(x);report[role].append({'frame':f,'degrees':x.tolist(),'cost':best})
  if f%5==0:print('DIGIT',role,f,x.tolist(),round(best,2),flush=True)
for role in ('reload_empty','reload_empty_mag10'):
 for f,row in enumerate(clips[role]):
  i=f-48
  if 0<=i<len(clips['cycle']):
   src=clips['cycle'][i];D=row['WPN_root']@src['WPN_root'].inverted()
   for n in row:
    if under(n,'clavicle_r'):row[n]=D@src[n]
(O/'refined_poses.json').write_text(json.dumps({role:[{n:[list(v) for v in m] for n,m in row.items()} for row in rows] for role,rows in clips.items()}))
(O/'digit_refinement.json').write_text(json.dumps(report,indent=2));print('DIGITS_SAVED',flush=True)
