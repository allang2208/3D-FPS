"""Native flexion axes, donor contact sectors; no donor terminal-axis twist."""
from pathlib import Path
code=(Path(__file__).parent/'fit_grip_contact.py').read_text();setup=code.split('def score(x):')[0]
exec(compile(setup,'contact_setup','exec'))
fingers=['thumb','index','middle','ring','pinky']
def candidate(x):
 row=clone(seed);q=Quaternion(G.col[0],math.radians(x[3]))@Quaternion(G.col[1],math.radians(x[4]))@Quaternion(G.col[2],math.radians(x[5]))
 row['hand_r']=Matrix.LocRotScale(seed['hand_r'].translation+G@Vector(x[:3]),q@seed['hand_r'].to_quaternion(),Vector((1,1,1)))
 for n in digits:
  loc=local_rest[n];rot=loc.to_quaternion()
  if n in axes:
   j=joint_names.index(n);rot=rot@Quaternion(-axes[n],math.radians(x[6+j]))
   if '_01_' in n:
    k=fingers.index(n.split('_')[0]);rot=rot@Quaternion(rest[n].to_quaternion().inverted()@pn,math.radians(x[21+k]))
  row[n]=row[parents[n]]@Matrix.LocRotScale(loc.translation,rot,Vector((1,1,1)))
 return row
def score(x):
 row=candidate(x);P=points(row)[idx];d=actual(row,P,False,{'M24_base'})['M24_base']*1000
 pen=np.maximum(.8-d,0);val=float(pen@pen)*100
 for finger in ('hand','thumb','middle','ring','pinky'):
  mask=(dominant[idx]==ids['hand_r']) if finger=='hand' else digit_masks[finger][idx]
  near=np.sort(np.abs(d[mask]))[:8];gap=np.maximum(near-1.,0);val+=float(gap@gap)*100
 for n,target,native in targets:
  dsq=np.sum((P[native]-target)**2,axis=1)*1.e6;val+=float(np.sort(dsq)[:6].mean())*(90 if n in ('hand_r','index_03_r') else 35)
 val+=float(np.sum((x[:3]/.008)**2))*18+float(np.sum((x[3:6]/10)**2))*10
 val+=float(np.sum(((x[6:21]-preferred)/30)**2))*15+float(np.sum((x[21:]/15)**2))*8
 return val
preferred=np.array([-10,-5,0,10,30,0,*([-10,-10,0]*3)])
x=np.array(json.loads((OUT/'grip_fit.json').read_text())['parameters'])
low=np.array([-.006,-.016,-.016,-15,-15,-15,*([-65,-70,-50]*5),-55,-20,-20,-20,-20.]);high=np.array([.024,.016,.018,15,15,15,*([60,65,55]*5),55,20,20,20,20.])
best=score(x)
for scale in (.5,.25,.125):
 strides=np.array([.004,.004,.004,5,5,5,*([10]*15),10,5,5,5,5])*scale
 for sweep in range(12):
  changed=False
  for i in range(len(x)):
   for sign in (-1,1):
    v=x.copy();v[i]=np.clip(v[i]+strides[i]*sign,low[i],high[i]);loss=score(v)
    if loss<best:best=loss;x=v;changed=True
  print('NATIVE',scale,sweep,round(best,1),x.tolist(),flush=True)
  if not changed:break
row=candidate(x);phi=min(range(-45,46,3),key=lambda p:cost(row,'r',p));fixed_arm(row,'r',phi)
ds=actual(row,points(row)[hm][::2],True,{'M24_base','M24_bolt','M24_boltrear'})
report={'parameters':x.tolist(),'pole':phi,'native_flexion_axes':True,'hand_contact':{n:{'penetration_mm':float(max(0,-d.min())*1000),'points_over_1mm':int((d<-.001).sum())} for n,d in ds.items()}}
(OUT/'grip_fit.json').write_text(json.dumps(report,indent=2));(OUT/'grip_pose.json').write_text(json.dumps(serial([row])[0]));print('NATIVE_SAVED',report['hand_contact'],flush=True)
