from pathlib import Path
exec(compile((Path(__file__).parent/'audit.py').read_text().split("\nif __name__=='__main__':")[0],'audit','exec'))
from mathutils.kdtree import KDTree
import itertools
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'kaitlin_skin_with_morphs.fbx'),use_anim=False)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');ob=max((o for o in bpy.data.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
bn=[n for n in ('hand_r','lowerarm_r','middle_01_r','thumb_01_r','hand_l','upperarm_r') if n in rig.data.bones]
a=np.array([(rig.matrix_world@rig.data.bones[n].matrix_local).translation[:] for n in bn]);b=np.array([rest[n].translation[:] for n in bn])
ac=a.mean(0);bc=b.mean(0);aa=a-ac;bb=b-bc;U,s,V=np.linalg.svd(aa.T@bb);R=V.T@U.T;scale=np.sum(s)/np.sum(aa*aa);T=bc-scale*R@ac
transform_mat=scale*R
pos=np.array([(ob.matrix_world@v.co)[:] for v in ob.data.vertices]);mapped=pos@transform_mat.T+T
kd=KDTree(len(pos))
for i,p in enumerate(mapped):kd.insert(p,i)
kd.balance();matched=[];errors=[]
for p in P:
 co,i,d=kd.find(p);matched.append(i);errors.append(d)
if max(errors)>.0001:raise RuntimeError('Morph geometry registration mismatch '+str(max(errors)))
matched=np.array(matched);shapes={}
for key in ob.data.shape_keys.key_blocks:
 if 'JC_' not in key.name:continue
 name='JC_'+key.name.split('JC_',1)[1]
 q=np.array([(ob.matrix_world@v.co)[:] for v in key.data]);delta=(q-pos)@transform_mat.T;shapes[name]=delta[matched]
print('MORPH_READ',len(shapes),'registration_mm',max(errors)*1000,flush=True)
K=Matrix.Diagonal((1,-1,1,1));ru={n:K@m@K for n,m in rest.items()}
def angle(a,b):return math.degrees(a.angle(b))
def clamp(x):return max(0.,min(1.,x))
def sw(a,b,x):t=clamp((x-a)/(b-a));return t*t*(3-2*t)
def tent(x,a,b,c):return clamp((x-a)/(b-a)) if x<=b else clamp((c-x)/(c-b))
def value(s):return -float(s[1:]) if s.startswith('m') else float(s)
def weights(row):
 pose={n:K@m@K for n,m in row.items()};out={}
 for side in ('l','r'):
  def ref(n):return ru[n+'_'+side]
  def p(n):return pose[n+'_'+side]
  rE=angle(ref('lowerarm').translation-ref('upperarm').translation,ref('hand').translation-ref('lowerarm').translation)
  E=angle(p('lowerarm').translation-p('upperarm').translation,p('hand').translation-p('lowerarm').translation)
  f=(ref('middle_01').translation-ref('hand').translation).normalized();r=ref('index_metacarpal').translation-ref('pinky_metacarpal').translation;r=(r-f*r.dot(f)).normalized();z=f.cross(r)
  tq=ref('lowerarm_twist_01').to_quaternion().inverted();f,r,z=tq@f,tq@r,tq@z
  h=p('lowerarm_twist_01').to_quaternion().inverted()@(p('middle_01').translation-p('hand').translation).normalized()
  flex=math.degrees(math.atan2(-h.dot(z),h.dot(f)));dev=math.degrees(math.atan2(h.dot(r),h.dot(f)));sane=1-sw(95,135,max(abs(flex),abs(dev)))
  for name,w in [('ElbowFlex20',clamp((rE-E)/(rE-20)) if rE>21 else 0),('ElbowFlex75',tent(E,rE,75,110)),('ElbowFlex110',tent(E,75,110,135)),('ElbowFlex135',clamp((E-110)/25)),('WristFlexA',clamp(flex/40)*sane),('WristFlexB',clamp(-flex/40)*sane),('WristRadial',clamp(dev/20)*sane),('WristUlnar',clamp(-dev/35)*sane)]:out['JC_'+name+'_'+side.upper()]=w
  extra=[]
  for finger in ('index','middle','ring','pinky'):
   def m(q):return q(finger+'_01').translation-q(finger+'_metacarpal').translation
   def n(q):return q(finger+'_02').translation-q(finger+'_01').translation
   extra.append(max(0,angle(m(p),n(p))-angle(m(ref),n(ref))))
  rel=p('lowerarm').to_quaternion().inverted()@p('hand').to_quaternion()@(ref('lowerarm').to_quaternion().inverted()@ref('hand').to_quaternion()).inverted()
  if rel.w<0:rel=-rel
  ax=ref('lowerarm').to_quaternion().inverted()@(ref('hand').translation-ref('lowerarm').translation).normalized();roll=math.degrees(2*math.atan2(Vector((rel.x,rel.y,rel.z)).dot(ax),rel.w));sig=np.array([E,flex,dev,roll,*extra])
  for name in shapes:
   if name.startswith('JC_Grip_'+side.upper()+'_'):
    ds=(np.array(extra)-np.array([value(s) for s in name.split('_')[3:7]]))/12;w=math.exp(-.5*float(ds@ds));out[name]=w if w>=.001 else 0
   elif name.startswith('JC_Pose_'+side.upper()+'_'):
    ds=sig-np.array([value(s) for s in name.split('_')[3:11]]);ds[3]=(ds[3]+180)%360-180;ds/=np.array([12,12,10,20,15,15,15,15]);w=math.exp(-.5*float(ds@ds));out[name]=w if w>=.001 else 0
 return out
report={'morph_count':len(shapes),'registration_max_mm':max(errors)*1000,'frames':{}}
for role,fraction in [('idle',0),('aim',0),('sprint_loop',.5),('reload',.5),('inspect',.5)]:
 row,_=compose(entry('skeleton_base',role),entry('skeleton_base',role)['duration']*fraction);w=weights(row);delta=np.zeros_like(P)
 for name,weight in w.items():
  if name in shapes:delta+=shapes[name]*weight
 X=skin(row,P=P+delta);inv=np.linalg.inv(np.array(row['WPN_root']@rest['WPN_root'].inverted()));X=(np.c_[X,np.ones(len(X))]@inv.T)[:,:3]
 checks={key:metric(X,key) for key in ('Default','receiver')}
 if role=='idle':
  checks.update({key:metric(X,key) for key in ('balanced','phantom','stable')});np.save(O/'idle_corrected.npy',X)
  render(X,'corrected_idle_palm',view='palm');render(X,'corrected_idle_back',view='back');render(X,'corrected_idle_trigger',view='trigger')
 if role=='sprint_loop':render(X,'corrected_sprint_back',view='back')
 report['frames'][role]={'checks':checks,'active_morphs':{n:v for n,v in w.items() if n in shapes and v>0},'max_rest_correction_mm':float(np.linalg.norm(delta[hand],axis=1).max())*1000}
 print('CORRECTED',role,json.dumps({k:round(v['max_penetration_mm'],3) for k,v in checks.items()}),flush=True)
(O/'corrected_review.json').write_text(json.dumps(report,indent=2));print('CORRECTED_REVIEW_DONE',flush=True)
