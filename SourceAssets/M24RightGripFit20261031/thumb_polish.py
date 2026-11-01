"""Millimetre-scale thumb-pad clearance for the thicker registered glove."""
from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'outfit_contact.py').read_text().split('\nfor variant,v in sol')[0],'contact_setup','exec'))
original=np.array(sol['variants']['Default']['parameters']);best=None
gi=np.flatnonzero(gh);si=np.flatnonzero(hand)
for a in (0.,-2.,2.):
 for b in (0.,-2.,-4.):
  for c in (0.,-2.,-4.):
   x=original.copy();x[18:21]+=[a,b,c];row=pose(x);sx=source_skin(row,si)
   p=skin(row,P=gp[gi],W=gw[gi]);gx=(np.c_[p,np.ones(len(p))]@np.array(inv).T)[:,:3]
   allp=np.r_[sx,gx];g=np.array([signed(grip_hulls['Default'],p)*1000 for p in allp]);r=np.array([signed(trees['receiver'],p)*1000 for p in allp])
   cost=float(np.sum(np.minimum(g-.15,0)**2)+2*np.sum(np.minimum(r-.15,0)**2)+.04*(a*a+b*b+c*c))
   if best is None or cost<best[0]:best=(cost,x.copy(),[-float(g.min()),-float(r.min())])
cost,x,m=best;row=pose(x);v=sol['variants']['Default'];v['parameters']=x.tolist();v['finger_local_quaternions']={n:list((row[parents[n]].inverted()@row[n]).to_quaternion()) for n in finger_bones};v['glove_thumb_polish']={'delta_degrees':(x-original)[18:21].tolist(),'skin_glove_envelope_max_mm':m}
sx=source_skin(row);valid=np.array([i for i in si if signed(grip_hulls['Default'],sx[i])<0],dtype=int);v['measurements']={'Default':metric(sx,'Default',ids=valid),'receiver':metric(sx,'receiver')}
(FIX/'fit_parameters.json').write_text(json.dumps(sol,indent=2));np.save(FIX/'Default_fit_skin.npy',sx)
O=FIX;render(sx,'Default_back',variant='Default',view='back');render(sx,'Default_trigger',variant='Default',view='trigger')
print('THUMB_POLISHED',json.dumps(v['glove_thumb_polish']),flush=True)
