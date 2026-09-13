"""Author complete hand contacts against the current magazine and handle.

VRE finger rotations are reused as a group. The contact fit changes the whole
hand and common closure only; bone lengths, finger translations and skin stay.
"""
import bpy,json,math,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent
sys.path.insert(0,str(S/'VREGripExtensions20260912/ReferenceWorkflow'))
from front_pose import solve_arm
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(m):return [list(v) for v in m]
def smooth(t):t=max(0.,min(1.,t));return t*t*t*(t*(t*6-15)+10)
def mix(a,b,t):
 al,aq,asc=a.decompose();bl,bq,bsc=b.decompose()
 if aq.dot(bq)<0:bq.negate()
 return Matrix.LocRotScale(al.lerp(bl,t),aq.slerp(bq,t),asc.lerp(bsc,t))
def shift(m,v):m=m.copy();m.translation+=Vector(v);return m
def track(keys,f):
 if f<=keys[0][0]:return keys[0][1].copy()
 for (a,A),(b,B) in zip(keys,keys[1:]):
  if f<=b:return mix(A,B,smooth((f-a)/(b-a)))
 return keys[-1][1].copy()
bpy.context.preferences.filepaths.save_version=0
source=O/'QBZ191_Wear_Editable.blend'
if not source.exists():source=S/'QBZ191Hero20260913/QBZ191_Hero_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
r=bpy.data.objects['SK_M4_Infima'];hands=bpy.data.objects['SK_Manny_Arms_Export'];s=bpy.context.scene
r.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in r.data.bones};names=list(rest)
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
finger={side:[n for n in names if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))] for side in ['l','r']}
def pose(action,f):
 r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
 s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
 return {b.name:b.matrix.copy() for b in r.pose.bones}
def basis(p,n):return lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n])
def setfingers(p,side,values):
 for n in finger[side]:p[n]=p[parents[n]]@lr[n]@values[n]
idle=pose(bpy.data.actions['QBZ191_base_idle'],0);W=idle['WPN_root'];W_inv=W.inverted()
idleB={n:basis(idle,n) for n in names};mag0=W_inv@idle['WPN_SOCKET_Magazine'];handle0=W_inv@idle['WPN_ChargingHandle']
fit=read(S/'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json')
donor={n:Matrix(v) for n,v in fit['basis'].items()}
geometry=read(O/'geometry.json');magverts=np.array(geometry['vertices']['WPN_SOCKET_Magazine'])
donorH=Matrix(fit['grip_in_root']).inverted()@Matrix(fit['hand_in_root'])
# Follow the curved magazine's mid-body axis. The grip origin is 60 mm above
# its grasp centre, exactly as in the accepted donor's physical grip frame.
center=Vector((.000688,-.151,-.058))
G=Matrix.Translation(center)@Matrix.Rotation(-.34,4,'X')@Matrix.Rotation(-math.pi/2,4,'Z')@Matrix.Translation((0,0,.060))
H0=G@donorH
mesh_xf=r.matrix_world.inverted()@hands.matrix_world
coords=np.array([list(mesh_xf@v.co)+[1.] for v in hands.data.vertices])
normals=np.array([list(mesh_xf.to_3x3()@v.normal) for v in hands.data.vertices])
weights={n:[] for n in names};dominant=[]
for i,v in enumerate(hands.data.vertices):
 named=[(hands.vertex_groups[g.group].name,g.weight) for g in v.groups]
 dominant.append(max(named,key=lambda x:x[1])[0] if named else '')
 for n,w in named:
  if n in weights:weights[n].append((i,w))
weights={n:(np.array([x[0] for x in a]),np.array([x[1] for x in a])) for n,a in weights.items() if a}
def skin(p):
 result=np.zeros((len(coords),3));normal=np.zeros_like(result)
 for n,(ids,ws) in weights.items():
  M=np.array(p[n]@rest[n].inverted());result[ids]+=((coords[ids]@M.T)[:,:3])*ws[:,None];normal[ids]+=(normals[ids]@M[:3,:3].T)*ws[:,None]
 return result,normal
def closure_basis(amount):
 result={}
 for n in finger['l']:
  loc,old,scale=idleB[n].decompose();q=donor.get(n,idleB[n]).to_quaternion()
  result[n]=Matrix.LocRotScale(loc,Quaternion().slerp(q,amount/.8),scale)
 return result
def handpoints(amount):
 p={n:m.copy() for n,m in idle.items()};p['hand_l']=W@H0;setfingers(p,'l',closure_basis(amount));pts,ns=skin(p)
 inv=np.array(W_inv);return (np.c_[pts,np.ones(len(pts))]@inv.T)[:,:3],ns@inv[:3,:3].T
reference_pts,reference_ns=handpoints(.8)
left=np.array([i for i,n in enumerate(dominant) if n=='hand_l' or n in finger['l']],dtype=int)
radial=np.array(center)[None,:]-reference_pts
radial[:,2]=0
facing=np.sum(reference_ns*radial,axis=1)>0
contact_groups={}
for group in ['hand','thumb','index','middle','ring','pinky']:
 ids=np.array([i for i in left if dominant[i].startswith(group) and facing[i]],dtype=int)
 if len(ids)>140:ids=ids[np.linspace(0,len(ids)-1,140).astype(int)]
 contact_groups[group]=ids
collision_ids=left[::3]
# Signed box cross-sections are used only to fit this curved shell. Full glove
# palm and finger surfaces participate; no independent fingertip chasing.
zs=np.linspace(float(magverts[:,2].min()),float(magverts[:,2].max()),48)
sections=[]
for z in zs:
 band=magverts[np.abs(magverts[:,2]-z)<.006]
 if len(band)==0:band=magverts[np.argsort(np.abs(magverts[:,2]-z))[:30]]
 sections.append([*band[:,:2].min(axis=0),*band[:,:2].max(axis=0)])
sections=np.array(sections)
def sdf(pts):
 limits=np.stack([np.interp(pts[:,2],zs,sections[:,i]) for i in range(4)],axis=1)
 d=np.stack([limits[:,0]-pts[:,0],pts[:,0]-limits[:,2],limits[:,1]-pts[:,1],pts[:,1]-limits[:,3],zs[0]-pts[:,2],pts[:,2]-zs[-1]],axis=1)
 return np.linalg.norm(np.maximum(d,0),axis=1)+np.minimum(d.max(axis=1),0)
clouds={}
def evaluate(x):
 c=round(float(x[0]),5)
 if c not in clouds:clouds[c]=handpoints(c)[0]
 pts=clouds[c]+x[1:4]
 distances=sdf(pts)
 score=0.
 for group,ids in contact_groups.items():
  vals=np.sort(np.abs(distances[ids]-.0007));count=max(1,len(vals)//5)
  score+=(2 if group=='hand' else 1)*float(np.mean(vals[:count]**2))
 penetration=np.maximum(-distances[collision_ids]-.001,0)
 score+=35*float(np.mean(penetration**2))
 # Keep the magazine's central grasp section inside the curled-hand envelope.
 touch=pts[np.concatenate(list(contact_groups.values()))]
 gap=np.maximum(touch[:,:2].min(axis=0)-np.array(center)[:2],0)+np.maximum(np.array(center)[:2]-touch[:,:2].max(axis=0),0)
 score+=15*float(np.sum(gap**2))
 score+=.025*float(np.sum(x[1:4]**2))+.000025*(c-.62)**2
 return score
best=None
for initial in [.55,.62,.69]:
 x=np.array([initial,0.,0.,0.]);value=evaluate(x)
 for steps in [( .07,.012,.012,.008),(.03,.004,.004,.003),(.012,.0015,.0015,.001)]:
  for iteration in range(12):
   changed=False
   for axis,step in enumerate(steps):
    for sign in [-1,1]:
     cand=x.copy();cand[axis]+=step*sign
     if not .52<=cand[0]<=.70 or np.any(np.abs(cand[1:4])>np.array([.045,.045,.025])):continue
     loss=evaluate(cand)
     if loss<value:x,value,changed=cand,loss,True
   if not changed:break
 if best is None or value<best[0]:best=(value,x.copy())
params=best[1];magH=shift(H0,params[1:4]);magG=mag0.inverted()@magH;graspB=closure_basis(float(params[0]))
# Pull with the actual index glove pad on the rear face of the small side knob.
# Other fingers retain the donor hook pose; this knob is too small for a fist.
charge_source=pose(bpy.data.actions['QBZ191_base_equip_charge'],12)
chargeB={n:basis(charge_source,n) for n in finger['r']}
chargeW=charge_source['WPN_root'];chargeInv=chargeW.inverted();chargeH=chargeInv@charge_source['hand_r']
actual,actual_ns=skin(charge_source);A=np.array(chargeInv)
actual=(np.c_[actual,np.ones(len(actual))]@A.T)[:,:3];actual_ns=actual_ns@A[:3,:3].T
ids=np.array([i for i,n in enumerate(dominant) if n=='index_03_r'])
# The glove's distal half, facing forward, hooks the handle's rear face.
bone=chargeInv@charge_source['index_03_r'];tail=bone@rest['index_03_r'].inverted()@r.data.bones['index_03_r'].tail_local
axis=np.array((tail-bone.translation).normalized());along=(actual[ids]-np.array(bone.translation))@axis
pad=ids[(along>np.quantile(along,.50))&(actual_ns[ids,1]<0)]
if len(pad)<8:pad=ids[along>np.quantile(along,.65)]
pad_center=np.median(actual[pad],axis=0)
knob=geometry['parts']['handle_knob'];target=Vector(((knob['min'][0]+knob['max'][0])*.5,knob['max'][1]+.0006,(knob['min'][2]+knob['max'][2])*.5))
chargeH.translation+=target-Vector(pad_center);chargeG=handle0.inverted()@chargeH
author={'magazine_closure':float(params[0]),'magazine_hand_in_root':rows(magH),'magazine_hand_in_bone':rows(magG),'magazine_fit_translation_m':list(params[1:4]),'magazine_basis':{n:rows(v) for n,v in graspB.items()},'handle_target_m':list(target),'charge_hand_in_root':rows(chargeH),'charge_hand_in_bone':rows(chargeG),'charge_pad_vertices':len(pad),'preserved_clocks':{'mouth':76,'seat':95,'release':98,'reload_end':126,'charge_contact':12,'pull_end':16,'release_handle':23,'charge_end':38},'status':'authored contact parameters; not an acceptance report'}
(O/'contact_parameters.json').write_text(json.dumps(author,indent=2));print('QBZ_CONTACT_FIT_AUTHORED',params.tolist(),list(target),flush=True)

def solve_right(p,H,w):
 old={n:m.copy() for n,m in p.items()};un,fn,hn='upperarm_r','lowerarm_r','hand_r'
 a=old[un].translation.copy();b=old[fn].translation;c=old[hn].translation;target=H.translation
 l1=(b-a).length;l2=(c-b).length
 desired=(H.to_3x3()@rest[hn].to_3x3().inverted()@(rest[hn].translation-rest[fn].translation)).normalized()
 ideal=target-desired*l2;a=a.lerp(ideal+(a-ideal).normalized()*l1,.35*w)
 axis=(target-a).normalized();dist=(target-a).length
 if dist>l1+l2-.004:a+=axis*(dist-(l1+l2-.004));dist=(target-a).length
 pole=b-a;pole-=axis*pole.dot(axis);pole.normalize()
 along=(l1*l1-l2*l2+dist*dist)/(2*dist);e=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
 p['clavicle_r'].translation+=a-old[un].translation
 for n,pos,direction,original in [(un,a,e-a,b-old[un].translation),(fn,e,target-e,c-b)]:
  p[n]=Matrix.LocRotScale(pos,original.rotation_difference(direction)@old[n].to_quaternion(),old[n].to_scale())
 for n in names:
  if n.startswith(('upperarm_twist','lowerarm_twist')) and n.endswith('_r'):
   par=un if n.startswith('upperarm') else fn;p[n]=p[par]@old[par].inverted()@old[n]
 p[hn]=H

meta={}
for family in ['base','vertical','canted','prism','angled']:
 for kind,end in [('reload',126),('reload_empty',164),('equip_charge',38)]:
  original=bpy.data.actions['QBZ191_'+('Seated_' if kind.startswith('reload') else '')+family+'_'+kind]
  start=pose(original,0);held=start['WPN_root'].inverted()@start['hand_l'];rightheld=start['WPN_root'].inverted()@start['hand_r']
  heldB={n:basis(start,n) for n in finger['l']};rightB={n:basis(start,n) for n in finger['r']}
  if kind.startswith('reload'):
   p30=pose(original,30);depart=p30['WPN_root'].inverted()@p30['hand_l'];p49=pose(original,49);pickup=p49['WPN_root'].inverted()@p49['WPN_SOCKET_Magazine']@magG
  samples=[];previous={}
  for k in range(end*4+1):
   f=k*.25;p=pose(original,f);root=p['WPN_root']
   if kind.startswith('reload') and 28<f<126:
    if f<49:targetH=root@track([(28,depart),(40,shift(pickup,(.025,.005,-.020))),(49,pickup)],f)
    elif f<=98:targetH=p['WPN_SOCKET_Magazine']@magG
    else:targetH=root@track([(98,magH),(102,shift(magH,(.012,.005,-.003))),(108,shift(magH,(.08,.012,-.004))),(118,shift(held,(.045,.006,-.01))),(126,held)],f)
    if f<49:
     w=smooth((f-28)/21);targetH=mix(p['hand_l'],targetH,w)
     fb={n:mix(basis(p,n),graspB[n],w) for n in finger['l']}
    elif f<=98:fb=graspB
    elif f<109:
     w=smooth((f-98)/8);fb={}
     for n in finger['l']:
      loc,q,scale=graspB[n].decompose();opened=Matrix.LocRotScale(loc,Quaternion().slerp(q,.42),scale);fb[n]=mix(graspB[n],opened,w)
    else:
     w=smooth((f-109)/17);fb={}
     for n in finger['l']:
      loc,q,scale=graspB[n].decompose();fb[n]=mix(Matrix.LocRotScale(loc,Quaternion().slerp(q,.42),scale),heldB[n],w)
    activity=smooth((f-28)/18)*(1-smooth((f-110)/16));solve_arm(p,rest,targetH,root,.65*activity);setfingers(p,'l',fb)
   charging=kind=='equip_charge' or (kind=='reload_empty' and f>=126)
   if charging:
    cf=f if kind=='equip_charge' else f-126
    pull=.045*smooth((cf-12)/4)*(1-smooth((cf-23)/2))
    p['WPN_ChargingHandle']=root@shift(handle0,(0,pull,0))
    if 12<=cf<=23:targetH=p['WPN_ChargingHandle']@chargeG
    else:targetH=root@track([(0,rightheld),(5,shift(rightheld,(-.035,-.01,.045))),(10,shift(chargeH,(-.012,.012,.014))),(12,chargeH),(23,shift(chargeH,(0,.045,0))),(27,shift(chargeH,(-.045,.060,.022))),(32,shift(rightheld,(-.025,-.012,.040))),(38,rightheld)],cf)
    w=smooth(cf/12)*(1-smooth((cf-23)/15));solve_right(p,targetH,w)
    setfingers(p,'r',{n:mix(rightB[n],chargeB[n],w) for n in finger['r']})
   row={}
   for n in names:
    loc,q,scale=basis(p,n).decompose()
    if n in previous and previous[n].dot(q)<0:q.negate()
    previous[n]=q.copy();row[n]=(loc,q,scale)
   samples.append(row)
  a=bpy.data.actions.new('QBZ191_Contact_'+family+'_'+kind);a.use_fake_user=True;r.animation_data.action=a
  for n in names:
   b=r.pose.bones[n];b.rotation_mode='QUATERNION'
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
  curves={(c.data_path,c.array_index):c for c in a.layers[0].strips[0].channelbag(a.slots[0]).fcurves}
  for n in names:
   for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
    for axis in range(count):
     curve=curves[(f'pose.bones["{n}"].{prop}',axis)];curve.keyframe_points.clear();curve.keyframe_points.add(len(samples))
     curve.keyframe_points.foreach_set('co',[v for k,row in enumerate(samples) for v in (k*.25,row[n][field][axis])])
     for key in curve.keyframe_points:key.interpolation='LINEAR'
     curve.update()
  r.animation_data.action_slot=a.slots[0];s.frame_start=0;s.frame_end=end;s.render.fps=60;s.frame_set(0)
  bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
  name='A_QBZ191_'+('' if family=='base' else family+'_')+kind;dest=O/'Animations'/family;dest.mkdir(parents=True,exist_ok=True)
  file=dest/(name+'.fbx')
  bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.25,bake_anim_simplify_factor=0)
  meta[family+':'+kind]={'name':name,'family':family,'file':str(file),'sample_rate':240,'duration':end/60,'action':a.name}
  (O/'build.json').write_text(json.dumps(meta,indent=2));print('QBZ_CONTACT_EXPORTED',family,kind,flush=True)
pose(bpy.data.actions['QBZ191_base_idle'],0);s.frame_end=180
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_Contact_Editable.blend'))
print('QBZ_CONTACT_AUTHORING_COMPLETE',flush=True)
