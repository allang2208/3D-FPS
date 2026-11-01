from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
base=clone(clips['idle'][0]);seed=clone(base);seed.update(raw_hand(base,1))
hand_names=['hand_r',*digits];idx=np.where(hm)[0][::2]
pn=(rest['index_01_r'].translation-rest['pinky_01_r'].translation).cross(rest['middle_01_r'].translation-rest['hand_r'].translation).normalized()
axes={}
for finger in ('thumb','index','middle','ring','pinky'):
 d=rest[finger+'_02_r'].translation-rest[finger+'_01_r'].translation
 axis=d.cross(pn).normalized()
 for j in (1,2,3):axes[f'{finger}_{j:02d}_r']=rest[f'{finger}_{j:02d}_r'].to_quaternion().inverted()@axis
joint_names=list(axes)
seedlocal={n:seed[parents[n]].inverted()@seed[n] for n in digits}
G=(base['WPN_root']@rest['WPN_root'].inverted()).to_3x3()
def candidate(x):
 row=clone(seed);q=Quaternion(G.col[0],math.radians(x[3]))@Quaternion(G.col[1],math.radians(x[4]))@Quaternion(G.col[2],math.radians(x[5]))
 row['hand_r']=Matrix.LocRotScale(seed['hand_r'].translation+G@Vector(x[:3]),q@seed['hand_r'].to_quaternion(),Vector((1,1,1)))
 for n in digits:
  loc=seedlocal[n];rot=loc.to_quaternion()
  if n in axes:
   j=joint_names.index(n);rot=rot@Quaternion(axes[n],math.radians(x[6+j]))
  if n=='thumb_01_r':rot=rot@Quaternion(rest[n].to_quaternion().inverted()@pn,math.radians(x[-1]))
  row[n]=row[parents[n]]@Matrix.LocRotScale(local_rest[n].translation,rot,Vector((1,1,1)))
 return row
calls=0
def score(x):
 row=candidate(x);P=points(row)[idx];ds=actual(row,P,False,{'M24_base','M24_bolt','M24_boltrear'})
 d=ds['M24_base']*1000
 val=sum(float(np.maximum(.35-v*1000,0)@np.maximum(.35-v*1000,0))*25 for v in ds.values())
 for finger in ('thumb','middle','ring','pinky'):
  fd=d[digit_masks[finger][idx]];near=np.sort(np.abs(fd))[:12]
  val+=float(np.maximum(near-1.8,0)@np.maximum(near-1.8,0))*2
 # Keep a natural donor grip. No joint translation, scale, or unconstrained twist.
 val+=float(np.sum((x[:3]/.01)**2))*15+float(np.sum((x[3:6]/8)**2))*10+float(np.sum((x[6:]/20)**2))*4
 return val
x=np.zeros(22);x[0]=.012
low=np.array([-.012,-.025,-.025,-15,-15,-15,*([-32]*15),-30.]);high=np.array([.030,.025,.025,15,15,15,*([32]*15),30.])
best=score(x)
for scale in (1.,.5,.25,.125):
 strides=np.array([.006,.006,.006,5,5,5,*([8]*15),8])*scale
 for sweep in range(7):
  changed=False
  for i in range(len(x)):
   for sign in (-1,1):
    v=x.copy();v[i]=np.clip(v[i]+strides[i]*sign,low[i],high[i]);loss=score(v)
    if loss<best:best=loss;x=v;changed=True
  print('FIT',scale,sweep,round(best,2),x.tolist(),flush=True)
  if not changed:break
row=candidate(x);phi=min(range(-60,61,3),key=lambda p:cost(row,'r',p));fixed_arm(row,'r',phi)
P=points(row);diag=actual(row,P[hm][::2],True,{'M24_base','M24_bolt','M24_boltrear'})
report={'parameters':x.tolist(),'pole':phi,'bone_lengths_unchanged':True,'hand_contact':{n:{'penetration_mm':float(max(0,-d.min())*1000),'points_over_1mm':int((d<-.001).sum())} for n,d in diag.items()}}
(OUT/'grip_fit.json').write_text(json.dumps(report,indent=2));(OUT/'grip_pose.json').write_text(json.dumps(serial([row])[0]))
print('GRIP',report,flush=True)
