"""Preserve source gesture while fitting the full right hand and arm around M24."""
from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'surface_contact.py').read_text().split("if __name__=='__main__':")[0],'surface_library','exec'))
# Full hand weighting, sampled deterministically for the fitting objective.
hand_ix=np.where(hm)[0][::3];arm_ix=np.where(~hm)[0][::10]
bolt_part=next(p for p in surfaces if p['name']=='M24_bolt')
major={'M24_base','M24_cheekrest','M24_MainScope_Lowpoly','M24_ScopeGlass_Lowpoly','M24_boltrear'}
knob_points=[v.co for v in bpy.data.objects['M24_bolt'].data.vertices if v.co.x>.046]
knob_center=sum(knob_points,Vector())/len(knob_points)
bolt_hulls=[]
for region in (knob_points,[v.co for v in bpy.data.objects['M24_bolt'].data.vertices if v.co.x<=.046]):
 bm=bmesh.new()
 for p in region:bm.verts.new(p)
 bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False);bm.normal_update();center=sum(region,Vector())/len(region);N=[];D=[]
 for face in bm.faces:
  n=face.normal.copy()
  if n.dot(face.calc_center_median()-center)<0:n=-n
  N.append(list(n));D.append(n.dot(face.verts[0].co))
 bolt_hulls.append((np.array(N),np.array(D)));bm.free()

def fit_hand(row,t):
 P=points(row)[hand_ix];pivot=np.array(row['hand_r'].translation)
 B=np.array((row['WPN_BoltHandle']@rest['WPN_BoltHandle'].inverted()).to_3x3())
 # In this source mesh X points to the operating/right side of the rifle.
 G=np.array((row['WPN_root']@rest['WPN_root'].inverted()).to_3x3())
 contacts=(t>=18 and t<=36)
 def deform(x):
  q=Quaternion(Vector(G[:,1]),math.radians(x[3]));R=np.array(q.to_matrix())
  return (P-pivot)@R.T+pivot+G@x[:3],R
 def score(x):
  Q,R=deform(x);ds=actual(row,Q,False,major)
  inv=np.array(rest['WPN_BoltHandle']@row['WPN_BoltHandle'].inverted());B=Q@inv[:3,:3].T+inv[:3,3]
  bd=[np.max(B@N.T-D,axis=1) for N,D in bolt_hulls];ds['M24_bolt']=np.minimum(*bd)
  loss=0
  for n,d in ds.items():
   margin=.0008 if n!='M24_bolt' else -.00025
   pen=np.maximum(margin-d,0)*1000
   loss+=np.sum(pen*pen)*8
  if contacts:
   d=bd[0]
   for finger in ('index','thumb'):
    mask=digit_masks[finger][hand_ix]
    near=np.sort(np.abs(d[mask]))[:5]*1000
    loss+=np.mean(np.maximum(near-2.,0)**2)*5
  loss+=np.sum((x[:3]/.012)**2)*3+(x[3]/15)**2*4
  return loss
 x=np.array([.012,0.,0.,0.]);best=score(x)
 for step in (1.,.5,.25):
  strides=np.array([.008,.006,.006,8.])*step
  for repeat in range(7):
   changed=False
   for i in range(4):
    for sign in (-1,1):
     v=x.copy();v[i]+=strides[i]*sign
     v=np.clip(v,[-.005,-.035,-.04,-30],[.06,.035,.035,30]);loss=score(v)
     if loss<best:best=loss;x=v;changed=True
   if not changed:break
 Q,R=deform(x);D=Matrix.Translation(Vector(pivot+G@x[:3]))@Matrix(R.tolist()).to_4x4()@Matrix.Translation(Vector(-pivot))
 return x,D,float(best)

# Fit one source stroke per role, then smooth its low-dimensional offsets.
output={};report={'hand_fits':{},'arm_fits':{},'fps':30}
for role in ('fire','cycle'):
 rows=clips[role]
 shift={'fire':0,'cycle':4,'reload_empty':52,'reload_empty_mag10':52}[role]
 keys=list(range(8,51));fits=[]
 for t in keys:
  if t+shift>=len(rows):break
  x,D,loss=fit_hand(rows[t+shift],t);fits.append(x);print('HAND',role,t,x.tolist(),round(loss,2),flush=True)
 fits=np.array(fits)
 fits[1:-1]=(fits[:-2]+6*fits[1:-1]+fits[2:])/8
 report['hand_fits'][role]={'times':keys[:len(fits)],'parameters':fits.tolist()}
 for f,row in enumerate(rows):
  t=f-shift
  if not 7<t<52:continue
  x=np.array([np.interp(t,keys[:len(fits)],fits[:,i]) for i in range(4)])
  w=ease((t-7)/5)*(1-ease((t-43)/9));x*=w
  G=(row['WPN_root']@rest['WPN_root'].inverted()).to_3x3();p=row['hand_r'].translation
  D=Matrix.Translation(p+G@Vector(x[:3]))@Quaternion(G.col[1],math.radians(x[3])).to_matrix().to_4x4()@Matrix.Translation(-p)
  for n in ['hand_r',*digits]:row[n]=D@row[n]
 # Search elbow directions against actual stock/receiver geometry as well as
 # wrist comfort. Continuous path selection avoids per-frame branch changes.
 phis=np.arange(-180,181,6,dtype=float);costs=[]
 for f,row in enumerate(rows):
  t=f-shift;costrow=[]
  if not 7<t<52:costs.append(np.full(len(phis),0.));continue
  for phi in phis:
   candidate=clone(row);apply_arm(candidate,'r',float(phi));P=points(candidate)[arm_ix]
   ds=actual(candidate,P,False,{'M24_base','M24_cheekrest'})
   pen=np.concatenate([np.maximum(.002-v,0)*1000 for v in ds.values()])
   loss=np.sum(pen*pen)*.15+cost(candidate,'r',0.)*.25+(phi/180)**2
   costrow.append(loss)
  costs.append(costrow)
  if f%10==0:print('ARM',role,f,round(min(costrow),2),flush=True)
 costs=np.array(costs);total=costs[0].copy();back=[];trans=((phis[:,None]-phis[None,:])/12)**2*3.
 for k in range(1,len(rows)):
  d=total[:,None]+trans;idx=d.argmin(0);back.append(idx);total=costs[k]+d[idx,np.arange(len(phis))]
 index=int(total.argmin());path=[index]
 for b in reversed(back):index=int(b[index]);path.append(index)
 chosen=phis[np.array(path[::-1])]
 for _ in range(2):chosen[1:-1]=(chosen[:-2]+2*chosen[1:-1]+chosen[2:])/4
 report['arm_fits'][role]=chosen.tolist()
 for f,row in enumerate(rows):
  t=f-shift
  if 7<t<52:
   w=ease((t-7)/5)*(1-ease((t-44)/8));apply_arm(row,'r',float(chosen[f]*w))
 output[role]=[{n:[list(v) for v in m] for n,m in row.items()} for row in rows]
for role in ('reload_empty','reload_empty_mag10'):
 rows=clips[role]
 for f,row in enumerate(rows):
  i=f-48
  if 0<=i<len(output['cycle']):
   src={n:Matrix(m) for n,m in output['cycle'][i].items()};D=row['WPN_root']@src['WPN_root'].inverted()
   for n in row:
    if under(n,'clavicle_r'):row[n]=D@src[n]
 output[role]=[{n:[list(v) for v in m] for n,m in row.items()} for row in rows]
(O/'refined_poses.json').write_text(json.dumps(output));(O/'refinement.json').write_text(json.dumps(report,indent=2))
print('REFINED_MOTION_SAVED',flush=True)
