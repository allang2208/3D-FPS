from pathlib import Path
exec(compile((Path(__file__).parent/'fit_grip.py').read_text().split('calls=0')[0],'grip_setup','exec'))
exec(compile((OUT/'field_contact.py').read_text(),'field_contact','exec'))
donor=json.loads((OUT/'donor_grip_surface.json').read_text());v,q,sc=Matrix(donor.pop('bolt_matrix')).decompose();mapping=base['WPN_BoltHandle']@Matrix.LocRotScale(v,q,Vector((1,1,1))).inverted()
body=next(p for p in surfaces if p['name']=='M24_base');targets=[]
bm=base[body['bone']]@rest[body['bone']].inverted();inv=bm.inverted()
for dn,pts in donor.items():
 if not pts:continue
 n='hand_r' if dn=='R_wrist' else dn.removeprefix('R_').replace('point','index').replace('pink','pinky')
 if dn!='R_wrist':n=n[:-1]+'_'+n[-1].zfill(2)+'_r'
 if n not in ids:continue
 source_points=[mapping@Vector(p) for p in pts];near=[]
 for p in source_points:
  hit,no,_,distance=body['bvh'].find_nearest(inv@p);near.append((distance,bm@(hit+no*.0008),p))
 near.sort(key=lambda a:a[0]);count=max(3,len(near)//5)
 if near[0][0]>.012 and dn!='R_point3':continue
 # Fingertips and palm contact sectors come from actual donor skin, not bone heads.
 target=sum((item[1] for item in near[:count]),Vector())/count
 if dn=='R_point3':target=sum(source_points,Vector())/len(source_points)
 mask=(dominant[idx]==ids[n]);native=np.where(mask)[0]
 if len(native):targets.append((n,np.array(target),native))
def score(x):
 row=candidate(x);P=points(row)[idx];ds=actual(row,P,False,{'M24_base'})
 val=sum(float(np.maximum(.25-v*1000,0)@np.maximum(.25-v*1000,0))*25 for v in ds.values())
 for n,target,native in targets:
  dsq=np.sum((P[native]-target)**2,axis=1)*1.e6
  val+=float(np.sort(dsq)[:6].mean())*(100 if n in ('hand_r','index_03_r') else 55)
 val+=float(np.sum((x[:3]/.006)**2))*20+float(np.sum((x[3:6]/8)**2))*15+float(np.sum((x[6:]/20)**2))*5
 return val
x=np.zeros(22);low=np.array([-.01,-.008,-.008,-12,-12,-12,*([-40]*15),-35.]);high=np.array([.018,.008,.008,12,12,12,*([40]*15),35.])
best=score(x)
for scale in (1.,.5,.25,.125):
 strides=np.array([.004,.004,.004,4,4,4,*([8]*15),8])*scale
 for sweep in range(8):
  changed=False
  for i in range(len(x)):
   for sign in (-1,1):
    v=x.copy();v[i]=np.clip(v[i]+strides[i]*sign,low[i],high[i]);loss=score(v)
    if loss<best:best=loss;x=v;changed=True
  print('CONTACT',scale,sweep,round(best,1),x.tolist(),flush=True)
  if not changed:break
row=candidate(x);phi=min(range(-60,61,3),key=lambda p:cost(row,'r',p));fixed_arm(row,'r',phi)
ds=actual(row,points(row)[hm][::2],True,{'M24_base','M24_bolt','M24_boltrear'})
report={'parameters':x.tolist(),'pole':phi,'contact_targets':[(n,t.tolist()) for n,t,i in targets],'hand_contact':{n:{'penetration_mm':float(max(0,-d.min())*1000),'points_over_1mm':int((d<-.001).sum())} for n,d in ds.items()}}
(OUT/'grip_fit.json').write_text(json.dumps(report,indent=2));(OUT/'grip_pose.json').write_text(json.dumps(serial([row])[0]));print('CONTACT_SAVED',report['hand_contact'],flush=True)
