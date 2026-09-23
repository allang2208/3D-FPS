"""Repair SVD hands without altering weapon mechanics, skin or runtime clocks."""
import bpy,ast,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;D=O/'Animations';D.mkdir(exist_ok=True)
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sample','select','bake','smooth','mix']],type_ignores=[]),'<SVD bake helpers>','exec'))
sys.path.insert(0,str(S/'SVDCompletion20260923'));from tactical_actions import sprint_generator
fits=json.loads((O/'contacts.json').read_text());inputs=json.loads((O/'inputs.json').read_text());sources=json.loads((S/'SVDAttachments20260923/sources.json').read_text())
bpy.context.preferences.filepaths.save_version=0;report={}
def copy(p):return {n:m.copy() for n,m in p.items()}
def shifted(m,v):m=m.copy();m.translation+=Vector(v);return m
def finger_names(side):return [n for n in rest if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))]
def basis(p,side):return {n:(lr[n].inverted()@p[parent[n]].inverted()@p[n]).to_quaternion() for n in finger_names(side)}
def lerp_fingers(a,b,t):return {n:a[n].slerp(b[n],t) for n in a}
def apply_fingers(p,qs,side):
 # Cache local rotations before changing any parent. Only rotate finger joints.
 for n in finger_names(side):p[n]=p[parent[n]]@lr[n]@qs[n].to_matrix().to_4x4()
def arm(p,H,side):
 old=copy(p);cn='clavicle_'+side;un='upperarm_'+side;fn='lowerarm_'+side;hn='hand_'+side
 A=old[un].translation.copy();E0=old[fn].translation;T=H.translation;l1=(E0-A).length;l2=(old[hn].translation-E0).length
 C=old[cn].translation.copy()
 if (T-A).length>l1+l2-.003:
  axis=(T-C).normalized();radius=(A-C).length;distance=(T-C).length;cosine=max(-1,min(1,(radius*radius+distance*distance-(l1+l2-.003)**2)/(2*radius*distance)));v=A-C-axis*(A-C).dot(axis)
  if v.length<1e-6:v=Vector((1,0,0))
  v.normalize();A=C+axis*(radius*cosine)+v*(radius*math.sqrt(max(0,1-cosine*cosine)))
  p[cn]=Matrix.LocRotScale(C,(old[un].translation-C).rotation_difference(A-C)@old[cn].to_quaternion(),old[cn].to_scale())
 axis=(T-A).normalized();distance=(T-A).length;pole=E0-A-axis*(E0-A).dot(axis)
 if pole.length<1e-6:pole=Vector((1,0,0));pole-=axis*pole.dot(axis)
 pole.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*distance);E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
 for n,origin,tip,oldtip in [(un,A,E,E0),(fn,E,T,old[hn].translation)]:p[n]=Matrix.LocRotScale(origin,(oldtip-old[n].translation).rotation_difference(tip-origin)@old[n].to_quaternion(),old[n].to_scale())
 # Align roll through the palm's transverse axis, without putting wrist bend into forearm twist.
 rest_axis=(rest[hn].translation-rest[fn].translation).normalized();normal=rest[hn].to_3x3()@Vector((0,0,1));normal-=rest_axis*normal.dot(rest_axis);normal.normalize()
 hand_delta=H.to_quaternion()@rest[hn].to_quaternion().inverted();target=hand_delta@normal;actual=(T-E).normalized();target-=actual*target.dot(actual)
 carried=p[fn].to_quaternion()@rest[fn].to_quaternion().inverted()@normal;carried-=actual*carried.dot(actual)
 if min(target.length,carried.length)>1e-6:
  target.normalize();carried.normalize();angle=math.atan2(actual.dot(carried.cross(target)),carried.dot(target));q=Quaternion(actual,angle*.65)@p[fn].to_quaternion();p[fn]=Matrix.LocRotScale(E,q,old[fn].to_scale())
 for n in [un,fn]:
  for j in ['01','02']:
   t=n.replace('_'+side,'_twist_'+j+'_'+side)
   if t in p:p[t]=p[n]@rest[n].inverted()@rest[t]
 p[hn]=H
def setup():
 global r,rest,parent,lr,leftnames
 r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rest={b.name:b.matrix_local.copy() for b in r.data.bones};parent={b.name:b.parent.name if b.parent else None for b in r.data.bones};lr={n:rest[parent[n]].inverted()@m if parent[n] else m for n,m in rest.items()};leftnames=[n for n in rest if n.endswith('_l')]
def left_blend(a,b,w):
 result=copy(a)
 for n in leftnames:
  if not parent[n]:continue
  x=a[parent[n]].inverted()@a[n];y=b[parent[n]].inverted()@b[n];result[n]=result[parent[n]]@mix(x,y,w)
 return result
def write(poses,key,family,clip):
 name='A_SVD_'+key
 if name in bpy.data.actions:bpy.data.actions[name].name='REFERENCE_BEFORE_'+name
 bake(r,poses,key,120)
 root='/Game/Weapons/SVDDragunov20260922/'+('Complete20260923' if family=='base' else 'Accessories20260923')+'/Animations/'
 report[family+'/'+clip]={'path':root+name,'name':name,'family':family,'clip':clip,'frames':len(poses)-1,'fps':120,'source':str(D/(name+'.fbx')),'game_tested':False}
 (O/'authoring.json').write_text(json.dumps(report,indent=2));print('SVD_HAND_AUTHORED',family,clip,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDAttachments20260923/SVD_Modular_Editable.blend'));setup()
originals={clip:bpy.data.actions['A_SVD_'+clip] for clip in sources['svd_clips']};idle=sample(r,originals['idle'],0);oldLH=idle['WPN_root'].inverted()@idle['hand_l'];RH=idle['WPN_root'].inverted()@idle['hand_r'];right_idle=basis(idle,'r')
guard=Matrix(fits['guard']['hand']);G={n:Quaternion(q) for n,q in fits['guard']['finger_basis'].items()};mag=Matrix(fits['magazine']['hand']);M={n:Quaternion(q) for n,q in fits['magazine']['finger_basis'].items()};hook=Matrix(fits['hook']['hand']);K={n:Quaternion(q) for n,q in fits['hook']['finger_basis'].items()}
center=Vector([(min(v[i] for v in inputs['targets']['Magazine']['vertices'])+max(v[i] for v in inputs['targets']['Magazine']['vertices']))*.5 for i in range(3)]);outward=mag.translation-center;outward.z=0;outward.normalize()
for clip in ['idle','aim','fire','aim_fire','equip','reload','reload_empty','inspect','quick_melee']:
 poses=[];count=round(sources['svd_clips'][clip]['seconds']*120)
 for f in range(count+1):
  p=sample(r,originals[clip],f);W=p['WPN_root'];qL=basis(p,'l');qR=basis(p,'r');H=W@guard
  if clip.startswith('reload'):
   entry=smooth((f-18)/28);hold=p['WPN_SOCKET_Magazine']@mag
   H=mix(W@guard,hold,entry)
   qL=lerp_fingers(G,M,smooth((f-20)/26))
   if f>240:
    opened={}
    for n,q in M.items():
     delay={'thumb':0,'index':1,'middle':2,'ring':3,'pinky':4}[n.split('_')[0]]
     amount=smooth((f-240-delay)/10)*(.12 if 'metacarpal' in n or '_01_' in n else .48)
     # Metacarpals retain the donor orientation; opening is in phalange joints.
     opened[n]=q.copy() if 'metacarpal' in n else q.slerp(Quaternion(),amount)
    clear=hold.copy();clear.translation+=p['WPN_SOCKET_Magazine'].to_3x3()@(outward*(.040*smooth((f-250)/18)))
    back=smooth((f-268)/34);H=mix(clear,W@guard,back);H.translation+=W.to_3x3()@Vector((.025*math.sin(math.pi*back),0,-.015*math.sin(math.pi*back)))
    qL=lerp_fingers(opened,G,smooth((f-277)/25))
  elif clip=='inspect':
   delta=(W.inverted()@p['hand_l']).translation-oldLH.translation;held=1-smooth((delta.length-.012)/.045)
   H=mix(p['hand_l'],W@guard,held);qL=lerp_fingers(qL,G,held)
  else:qL=G
  arm(p,H,'l');apply_fingers(p,qL,'l')
  if clip in ['equip','reload_empty']:
   start,contact,pulled,close,finish=(20,64,94,100,176) if clip=='equip' else (268,310,344,350,432)
   if start<f<finish:
    closed=sample(r,originals[clip],contact)['WPN_bolt'];origin=sample(r,originals[clip],contact)['WPN_root'];bolt0=(origin.inverted()@closed).translation
    current=(W.inverted()@p['WPN_bolt']).translation-bolt0
    if f<=contact:
     approach=shifted(hook,(-.025,.008,.015));split=contact-12
     local=mix(RH,approach,smooth((f-start)/(split-start))) if f<split else mix(approach,hook,smooth((f-split)/(contact-split)))
    elif f<=pulled:local=shifted(hook,current)
    elif f<=close+16:
     rear=shifted(hook,(0,.075,0));local=shifted(rear,(-.055*smooth((f-pulled)/(close+16-pulled)),.01*smooth((f-pulled)/(close+16-pulled)),.025*smooth((f-pulled)/(close+16-pulled))))
    else:local=mix(shifted(hook,(-.055,.085,.025)),RH,smooth((f-close-16)/(finish-close-16)))
    close_weight=smooth((f-start)/(contact-start));return_weight=smooth((f-close-12)/(finish-close-12));target={}
    for n,q in K.items():target[n]=q if 'metacarpal' in n else q.slerp(Quaternion(),.35*smooth((f-pulled)/10))
    qR=lerp_fingers(right_idle,target,close_weight*(1-return_weight));arm(p,W@local,'r')
   else:qR=right_idle
  apply_fingers(p,qR,'r');poses.append(p)
 write(poses,clip,'base',clip)
 if clip=='idle':fixed_idle=poses[0]
def sprints(idle,family):
 make,_=sprint_generator(r,idle)
 for clip,count in [('sprint_enter',48),('sprint_loop',120),('sprint_exit',48)]:
  poses=[]
  for f in range(count+1):
   t=f/count;progress=1 if clip=='sprint_loop' else 1-t if clip=='sprint_exit' else t
   row=make(progress,2*math.pi*t if clip=='sprint_loop' else None)
   row=left_blend(row,idle,1-smooth(progress/.22));poses.append(row)
  write(poses,('' if family=='base' else family+'_')+clip,family,clip)
sprints(fixed_idle,'base');sample(r,bpy.data.actions['A_SVD_idle'],0);bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVD_base_Editable.blend'))
for family in ['vertical','canted','prism','angled']:
 bpy.ops.wm.open_mainfile(filepath=str(S/f'SVDAttachments20260923/SVD_{family}_Editable.blend'));setup();don=sample(r,bpy.data.actions[f'A_SVD_{family}_idle'],0);H0=don['WPN_root'].inverted()@don['hand_l'];F=basis(don,'l')
 bpy.ops.wm.open_mainfile(filepath=str(O/'SVD_base_Editable.blend'));setup();idle=sample(r,bpy.data.actions['A_SVD_idle'],0)
 def family_pose(row):
  p=copy(row);arm(p,p['WPN_root']@H0,'l');apply_fingers(p,F,'l');return p
 family_idle=family_pose(idle)
 for clip in ['idle','aim','fire','aim_fire','equip','reload','reload_empty','inspect','quick_melee']:
  a=bpy.data.actions['A_SVD_'+clip];count=round(sources['svd_clips'][clip]['seconds']*120);poses=[]
  for f in range(count+1):
   p=sample(r,a,f);w=1.
   if clip.startswith('reload'):w=1-smooth(f/18)+smooth((f-280)/22)
   elif clip=='inspect':w=1-smooth(((p['WPN_root'].inverted()@p['hand_l']).translation-guard.translation).length/.045)
   poses.append(left_blend(p,family_pose(p),w))
  write(poses,family+'_'+clip,family,clip)
 sprints(family_idle,family);sample(r,bpy.data.actions[f'A_SVD_{family}_idle'],0);bpy.ops.wm.save_as_mainfile(filepath=str(O/f'SVD_{family}_Editable.blend'))
print('SVD_HAND_AUTHORING_COMPLETE',len(report),flush=True)
