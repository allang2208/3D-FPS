"""Bounded native finger flexion and palm fit to the selected moving knob."""
import bmesh,itertools
from pathlib import Path
exec(Path(__file__).with_name('author_motion.py').read_text().split('# The knob\'s convex')[0])
bolt=bpy.data.objects['M24_bolt'];points=[v.co.copy() for v in bolt.data.vertices if v.co.x>.046]
center=sum(points,Vector())/len(points);bm=bmesh.new()
for p in points:bm.verts.new(p)
bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False);bm.normal_update()
ns=[];cs=[]
for f in bm.faces:
 n=f.normal.copy();p=f.verts[0].co
 if n.dot(f.calc_center_median()-center)<0:n=-n
 ns.append(list(n));cs.append(n.dot(p))
N=np.array(ns);Cs=np.array(cs);bm.free()
knob=[v.co for v in bolt.data.vertices if v.co.x>.046]
center=np.array([(min(p[i] for p in knob)+max(p[i] for p in knob))*.5 for i in range(3)])
H=ref['hand_r'];hi=H.inverted();rn=list(rest);ids={n:i for i,n in enumerate(rn)}
verts=np.array([list(v.co)+[1] for v in skin.data.vertices]);weights=np.zeros((len(verts),len(rn)))
for v in skin.data.vertices:
 for g in v.groups:
  name=skin.vertex_groups[g.group].name
  if name in ids:weights[v.index,ids[name]]=g.weight
mask=weights[:,[ids[n] for n in rn if under(n,'hand_r')]].sum(1)>.98
verts=verts[mask];weights=weights[mask];dominant=weights.argmax(1)
W=np.einsum('vk,kij,vj->kvi',weights,np.array([np.array(rest[n].inverted()) for n in rn]),verts,optimize=True)
M=np.array([np.array(hi@ref[n]) for n in rn]);Q=np.array(rest['WPN_BoltHandle'].to_3x3()@ref['WPN_BoltHandle'].to_3x3().inverted()@H.to_3x3())
finger_masks={f:np.isin(dominant,[ids[n] for n in rn if n.startswith(f+'_') and n.endswith('_r')]) for f in ('thumb','index','middle','ring','pinky')}
initial=np.array([-.115,.035,.025]+[68,92,38]*4+[35,-25,25,25],dtype=float)
lo=np.array([-.14,.015,.005]+[40,55,10]*4+[5,-55,0,0]);hi_bound=np.array([-.09,.065,.045]+[85,105,65]*4+[65,0,60,60])
axes={f:(rest[f+'_02_r'].translation-rest[f+'_01_r'].translation).cross(pn).normalized() for f in ('index','middle','ring','pinky','thumb')}
def makegrip(x):
 g=dict(grip)
 for i,f in enumerate(('index','middle','ring','pinky')):
  for j in (1,2,3):
   n=f'{f}_{j:02d}_r';v=rest[n].to_quaternion().inverted()@axes[f];v.x=0;v.normalize()
   g[n]=local_rest[n]@Quaternion(v,math.radians(x[3+i*3+j-1])).to_matrix().to_4x4()
 for j,d in ((1,x[15]),(2,x[17]),(3,x[18])):
  n=f'thumb_{j:02d}_r';v=rest[n].to_quaternion().inverted()@axes['thumb'];q=Quaternion(v,math.radians(d))
  if j==1:q=Quaternion(rest[n].to_quaternion().inverted()@pn,math.radians(x[16]))@q
  g[n]=local_rest[n]@q.to_matrix().to_4x4()
 return g
def evaluate(x,details=False):
 g=makegrip(x);m=M.copy()
 for n in right_digits:m[ids[n]]=m[ids[parents[n]]]@np.array(g[n])
 P=np.einsum('kij,kvj->vi',m,W,optimize=True)[:,:3]
 P=(P-x[:3])@Q.T+center
 distance=(P@N.T-Cs).max(axis=1)*1000
 penetration=np.maximum(-distance-.15,0)
 loss=(penetration**2).sum()*1000
 proximity={}
 for f,weight in [('thumb',4),('index',4),('middle',.4)]:
  d=np.sort(distance[finger_masks[f]])[:8];proximity[f]=float(d.mean());loss+=weight*np.mean((d-.8)**2)
 loss+=np.sum(((x[3:]-initial[3:])/35)**2)*.3
 loss+=np.sum(((x[:3]-initial[:3])/.015)**2)*.3
 if details:return {'loss':float(loss),'penetration_mm':float(penetration.max()),'surface_gap_mm':proximity,'parameters':x.tolist()}
 return loss
x=initial.copy();best=evaluate(x)
for offset in itertools.product((-.015,0,.015),repeat=3):
 y=initial.copy();y[:3]=np.clip(y[:3]+offset,lo[:3],hi_bound[:3]);v=evaluate(y)
 if v<best:x=y;best=v
for step in (1.,.5,.25,.125):
 strides=np.array([.005,.005,.005]+[12]*16)*step
 for cycle in range(10):
  changed=False
  for i in range(len(x)):
   for sign in (-1,1):
    y=x.copy();y[i]=np.clip(y[i]+sign*strides[i],lo[i],hi_bound[i]);v=evaluate(y)
    if v<best:x=y;best=v;changed=True
  for offset in itertools.product((-1,0,1),repeat=3):
   y=x.copy();y[:3]=np.clip(y[:3]+np.array(offset)*strides[:3],lo[:3],hi_bound[:3]);v=evaluate(y)
   if v<best:x=y;best=v;changed=True
  if not changed:break
 print('FIT',step,evaluate(x,True),flush=True)
result=evaluate(x,True);result['local_grip']={n:[list(row) for row in m] for n,m in makegrip(x).items()}
(O/'bolt_grip_fit.json').write_text(json.dumps(result,indent=2));print('BOLT_GRIP_FIT_SAVED',flush=True)
