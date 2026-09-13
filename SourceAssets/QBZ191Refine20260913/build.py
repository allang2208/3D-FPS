"""QBZ-specific continuous reload, side charging and accepted grip families.

Authoring inputs are existing project motions/hand poses. No gameplay tests.
All dimensions below are metres in the existing WPN_root authoring frame.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion,Euler
O=Path(__file__).parent;S=O.parent
sys.path.insert(0,str(S/'VREGripExtensions20260912/ReferenceWorkflow'))
from front_pose import solve_arm
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(m):return [list(x) for x in m]
def smooth(t):t=max(0.,min(1.,t));return t*t*t*(t*(t*6-15)+10)
def mix(a,b,w):
 al,aq,asc=a.decompose();bl,bq,bsc=b.decompose()
 if aq.dot(bq)<0:bq.negate()
 return Matrix.LocRotScale(al.lerp(bl,w),aq.slerp(bq,w),asc.lerp(bsc,w))
def track(keys,f):
 if f<=keys[0][0]:return keys[0][1].copy()
 for (a,A),(b,B) in zip(keys,keys[1:]):
  if f<=b:return mix(A,B,smooth((f-a)/(b-a)))
 return keys[-1][1].copy()
def shifted(m,v):o=m.copy();o.translation+=Vector(v);return o
def pose(a,f):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
 return {b.name:b.matrix.copy() for b in r.pose.bones}
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ19120260912/SurfacePolish/QBZ191_SurfacePolish.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];gun=bpy.data.objects['QBZ191_Export'];hands=bpy.data.objects['SK_Manny_Arms_Export']
rest={b.name:b.matrix_local.copy() for b in r.data.bones};names=list(rest)
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
old={k:bpy.data.actions['QBZ191_'+k] for k in ['idle','aim','fire','aim_fire','reload','reload_empty','equip_charge']}
base=pose(old['idle'],0);root0=base['WPN_root'];rootinv=root0.inverted();local0={n:rootinv@m for n,m in base.items()}
base_basis={n:lr[n].inverted()@(base[parents[n]].inverted()@base[n] if parents[n] else base[n]) for n in names}
contact=pose(old['reload'],95);maggrasp=contact['WPN_SOCKET_Magazine'].inverted()@contact['hand_l']
contact_basis={n:lr[n].inverted()@contact[parents[n]].inverted()@contact[n] for n in names if parents[n]}
charge_ref=pose(old['equip_charge'],16);charge_root=charge_ref['WPN_root'];charge_hand=charge_root.inverted()@charge_ref['hand_r']
charge_basis={n:lr[n].inverted()@charge_ref[parents[n]].inverted()@charge_ref[n] for n in names if parents[n]}
# Source charge hand supplies a grouped finger pose; relocate its actual finger
# pad neighbourhood to this rifle's left-side handle, not the AR rear handle.
finger_contact=sum((charge_root.inverted()@charge_ref[n]@(rest[n].inverted()@r.data.bones[n].tail_local) for n in ['index_03_r','middle_03_r','thumb_03_r']),Vector())/3
comps=read(S/'QBZ19120260912/components.json')[0]['components']
with bpy.data.libraries.load(str(S/'QBZ19120260912/SourceInspect.blend'),link=False) as (a,b):b.objects=['QBZ']
src=b.objects[0];xf=Matrix.Translation((-.005,-.11,.065))
handle=[xf@src.matrix_world@src.data.vertices[i].co for i in comps[89]['ids']]
knob=[p for p in handle if p.x<-.029]
knobcenter=sum(knob,Vector())/len(knob)
charge_hand.translation+=knobcenter-finger_contact+Vector((-.003,0,0))
bpy.data.objects.remove(src,do_unlink=True)
left_fingers=[n for n in names if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
right_fingers=[n for n in names if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))]
mount_rotation=Matrix.Rotation(-math.pi/2,4,'Z')
grip_mount=Matrix.Translation((.000688,-.295,.040546))@mount_rotation
fits={'vertical':read(S/'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json')}
extensions=read(S/'VREGripExtensions20260912/fits.json')
fits.update(canted=extensions['m4:canted'],prism=extensions['m4:prism'])
fits['angled']=read(S/'AngledForegrip20260910/WristNatural/fit_final.json')
profiles={};mounts={}
for family,fit in fits.items():
 G=Matrix(fit['grip_in_root']);H=Matrix(fit['hand_in_root'])
 if family=='angled':
  # This older mesh is baked into M4 bind space. Its recorded saddle frame
  # cancels that space exactly once; preserve the compact mesh's physical size.
  old_mount=rest['WPN_root'].inverted()@Matrix(fit['mount_matrix'])
  delta=grip_mount@old_mount.inverted();target=delta@H
  mounts[family]={'root_matrix':rows(grip_mount),'bind_delta':rows(grip_mount@old_mount.inverted()@rest['WPN_root'].inverted())}
 else:
  target=grip_mount@G.inverted()@H;mounts[family]={'root_matrix':rows(grip_mount)}
 profiles[family]={'hand':target,'basis':{n:Matrix(m) for n,m in fit['basis'].items()},'source':str(S/('AngledForegrip20260910/WristNatural' if family=='angled' else 'MannyGraspDonor20260912' if family=='vertical' else 'VREGripExtensions20260912'))}
profiles['base']={'hand':local0['hand_l'],'basis':base_basis,'source':'QBZ19120260912/QBZ191_Editable.blend'}
(O/'mounts.json').write_text(json.dumps({'underbarrel':mounts,'top_rail_z':.096473,'rail_center_x':.000688,'charging_handle_center':list(knobcenter)},indent=2))
# Remove unused controller shapes from the new editable file only.
for ob in list(s.objects):
 if ob not in [r,gun,hands]:bpy.data.objects.remove(ob,do_unlink=True)
r.animation_data.action=None
def arm(p,side,H):
 if side=='l':solve_arm(p,rest,H,p['WPN_root']@grip_mount,.7);return
 # Two-bone solve with a fixed source elbow plane and distributed wrist twist.
 un,fn,hn='upperarm_r','lowerarm_r','hand_r';a=base[un].translation.copy();b=base[fn].translation;c=base[hn].translation
 l1=(b-a).length;l2=(c-b).length;goal=H.translation;axis=(goal-a).normalized();d=(goal-a).length
 if d>l1+l2-.003:a+=axis*(d-l1-l2+.003);d=(goal-a).length
 pole=b-a;pole-=axis*pole.dot(axis);pole.normalize();along=(l1*l1-l2*l2+d*d)/(2*d)
 e=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
 p['clavicle_r'].translation+=a-base[un].translation
 for n,pos,direction,orig in [(un,a,e-a,b-base[un].translation),(fn,e,goal-e,c-b)]:
  p[n]=Matrix.LocRotScale(pos,orig.rotation_difference(direction)@base[n].to_quaternion(),base[n].to_scale())
 for n in names:
  if n.startswith(('upperarm_twist','lowerarm_twist')) and n.endswith('_r'):
   parent=un if n.startswith('upperarm') else fn;p[n]=p[parent]@base[parent].inverted()@base[n]
 p[hn]=H
def apply_fingers(p,side,source,target,weight):
 for n in left_fingers if side=='l' else right_fingers:
  B=mix(source.get(n,base_basis[n]),target.get(n,base_basis[n]),weight)
  # Finger locations and scale remain the common hand's original bind values.
  loc,unused,scale=base_basis[n].decompose();B=Matrix.LocRotScale(loc,B.to_quaternion(),scale)
  p[n]=p[parents[n]]@lr[n]@B
def root_motion(f,end,charging=False):
 if charging:
  w=smooth(f/8)*(1-smooth((f-27)/11));return root0@Matrix.Translation((0,.008*w,-.002*w))@Euler((math.radians(-2*w),math.radians(4*w),0)).to_matrix().to_4x4()
 def R(v,angles):return root0@Matrix.Translation(v)@Euler(tuple(math.radians(x) for x in angles)).to_matrix().to_4x4()
 return track([(0,root0),(16,R((-.004,.01,.006),(-6,12,0))),(24,R((-.003,.014,.012),(-8,17,0))),(32,R((.003,.006,0),(-4,-7,0))),(45,R((-.006,.01,.002),(-6,8,0))),(92,R((-.006,.01,.002),(-6,8,0))),(95,R((-.006,.01,.004),(-6,8.6,0))),(101,R((-.006,.01,.002),(-6,8,0))),(126,root0)],f)
mag0=local0['WPN_SOCKET_Magazine'];attach_charge=local0['WPN_ChargingHandle']
def magazine(f):
 keys=[(0,mag0),(21,mag0),(29,shifted(mag0,(-.004,0,-.048))),(43,shifted(mag0,(.38,.08,-.50))@Matrix.Rotation(1.3,4,'X')),(48,shifted(mag0,(.60,.14,-.85))@Matrix.Rotation(2.2,4,'X'))]
 # Both endpoints of this hidden reset are below the viewmodel, with unit scale.
 if f<49:return track(keys,f)
 return track([(49,shifted(mag0,(.22,.12,-.70))),(56,shifted(mag0,(.10,.07,-.32))),(68,shifted(mag0,(.025,.02,-.15))),(76,shifted(mag0,(0,0,-.07))),(91,shifted(mag0,(0,0,-.009))),(95,mag0)],f)
def charge(f,held):
 right=local0['hand_r'];C=charge_hand
 pull=.045*smooth((f-12)/4)*(1-smooth((f-23)/2))
 H=track([(0,right),(5,shifted(right,(-.035,-.01,.055))),(12,C),(16,shifted(C,(0,.045,0))),(23,shifted(C,(0,.045,0))),(25,shifted(C,(0,.0,0))),(29,shifted(C,(-.055,.015,.035))),(38,right)],f)
 return H,pull,smooth(f/11)*(1-smooth((f-27)/11))
meta={};actions={}
for family,profile in profiles.items():
 D=O/'Animations'/family;D.mkdir(parents=True,exist_ok=True)
 held=profile['hand'];holdbasis=profile['basis'];family_actions=[]
 for kind,end in [('idle',180),('aim',2),('fire',46),('aim_fire',46),('reload',126),('reload_empty',164),('equip_charge',38)]:
  rate=240 if kind in ['reload','reload_empty','equip_charge'] else 120;step=60/rate
  frames=[k*step for k in range(round(end/step)+1)];samples=[];previous={}
  for f in frames:
   isreload=kind in ['reload','reload_empty'];equip=kind=='equip_charge';ischarge=equip or (kind=='reload_empty' and f>=126);ef=f if equip else f-126
   root=root_motion(ef,38,True) if ischarge else root_motion(f,end) if isreload else root0
   if kind=='idle':root=root0@Matrix.Translation((0,0,math.sin(f/180*math.tau)*.0004))
   if kind in ['fire','aim_fire']:
    w=math.sin(min(f/10,1)*math.pi)*math.exp(-f/9) if f<10 else 0
    root=root0@Matrix.Translation((0,.008*w,0))@Matrix.Rotation(math.radians(-1.2*w),4,'X')
   p={n:m.copy() for n,m in base.items()};p['WPN_root']=root
   for n in names:
    if n.startswith('WPN_') and n!='WPN_root':p[n]=root@local0[n]
   left=held;right=local0['hand_r'];fingers=holdbasis;fingerw=0;rightw=0
   if isreload and f<126:
    M=magazine(f);p['WPN_SOCKET_Magazine']=root@M;maghand=M@maggrasp
    off=shifted(mag0@maggrasp,(.20,.11,-.46));out=shifted(held,(.060,0,-.010))
    if f<49:left=track([(0,held),(7,held),(16,out),(30,off),(49,magazine(49)@maggrasp)],f)
    elif f<=98:left=maghand
    else:left=track([(98,mag0@maggrasp),(107,shifted(mag0@maggrasp,(.065,0,-.006))),(115,shifted(held,(.050,.006,-.010))),(126,held)],f)
    fingerw=smooth((f-7)/14)*(1-smooth((f-106)/20));fingers=contact_basis
   if ischarge:
    right,pull,rightw=charge(ef,held);p['WPN_ChargingHandle']=root@shifted(attach_charge,(0,pull,0))
    # The magazine is seated for every charge/equip sample.
    p['WPN_SOCKET_Magazine']=root@mag0
   arm(p,'l',root@left);arm(p,'r',root@right)
   apply_fingers(p,'l',holdbasis,fingers,fingerw);apply_fingers(p,'r',base_basis,charge_basis,rightw)
   row={}
   for n in names:
    B=lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);loc,q,scale=B.decompose()
    if n in previous and previous[n].dot(q)<0:q.negate()
    previous[n]=q.copy();row[n]=(loc,q,scale)
   samples.append(row)
  a=bpy.data.actions.new('QBZ191_'+family+'_'+kind);a.use_fake_user=True;r.animation_data.action=a
  for n in names:
   b=r.pose.bones[n];b.rotation_mode='QUATERNION'
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
  bag=a.layers[0].strips[0].channelbag(a.slots[0]);curves={(fc.data_path,fc.array_index):fc for fc in bag.fcurves}
  for n in names:
   for prop,ix,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
    for axis in range(count):
     fc=curves[(f'pose.bones["{n}"].{prop}',axis)];fc.keyframe_points.clear();fc.keyframe_points.add(len(frames));fc.keyframe_points.foreach_set('co',[value for i,f in enumerate(frames) for value in (f,samples[i][n][ix][axis])])
     for key in fc.keyframe_points:key.interpolation='LINEAR'
     fc.update()
  r.animation_data.action_slot=a.slots[0];s.render.fps=60;s.frame_start=0;s.frame_end=end;s.frame_set(0)
  bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
  name='A_QBZ191_'+('' if family=='base' else family+'_')+kind
  bpy.ops.export_scene.fbx(filepath=str(D/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=step,bake_anim_simplify_factor=0)
  meta[family+':'+kind]={'file':str(D/(name+'.fbx')),'name':name,'family':family,'duration':end/60,'sample_rate':rate,'action':a.name};actions[(family,kind)]=a;family_actions.append(a)
  (O/'build.json').write_text(json.dumps(meta,indent=2));print('QBZ_AUTHORED',family,kind,flush=True)
 # One editable file per family includes all clips authored so far.
 r.animation_data.action=family_actions[0];r.animation_data.action_slot=family_actions[0].slots[0];s.frame_set(0);s.frame_end=180
 bpy.ops.wm.save_as_mainfile(filepath=str(O/('QBZ191_'+family+'_Editable.blend')))
r.animation_data.action=actions[('base','idle')];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
for ob in [r,gun,hands]:ob.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'SK_QBZ191_Manny.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_Editable.blend'))
print('QBZ_AUTHORING_COMPLETE',flush=True)
