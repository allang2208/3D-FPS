import bpy, math, json, sys
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

O=Path(__file__).parent; baseline='--baseline' in sys.argv;D=O/('NativeBaseline' if baseline else 'Native');D.mkdir(exist_ok=True)
def rigid(m):
 p,q,_=m.decompose(); return Matrix.LocRotScale(p,q,Vector((1,1,1)))
def action(r,a):
 r.animation_data_create(); r.animation_data.action=a
 if a.slots:r.animation_data.action_slot=a.slots[0]
def sample(r,f):
 bpy.context.scene.frame_set(math.floor(f),subframe=f-math.floor(f));bpy.context.view_layer.update()
 return {b.name:rigid(r.matrix_world@b.matrix) for b in r.pose.bones}
def frame(p):
 y=(p['WPN_FrontSight'].translation-p['WPN_RearSight'].translation).normalized()
 x=y.cross(Vector((0,0,1))).normalized(); z=x.cross(y).normalized()
 return Matrix((x,y,z)).transposed().to_4x4()

bpy.ops.wm.open_mainfile(filepath=str(O.parent/'ArmsRepair20260909/Integrated/SK_AKM_HandsRepair_Source.blend'))
r=bpy.data.objects['SK_AKM_Viewmodel'];action(r,bpy.data.actions['AKM_idle']);srcidle=sample(r,1)
parts=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not o.name.startswith('AKMR_'):continue
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
 bone='WPN_bolt' if o.name=='AKMR_Bolt' else 'WPN_Trigger' if o.name=='AKMR_Trigger' else 'WPN_SOCKET_Magazine' if o.name=='AKMR_Magazine' else 'WPN_root'
 parts.append(dict(name=o.name,bone=bone,vertices=[tuple(o.matrix_world@v.co) for v in me.vertices],faces=[tuple(p.vertices) for p in me.polygons],slots=[m.name for m in me.materials],mi=[p.material_index for p in me.polygons],uv=[tuple(x.uv) for x in me.uv_layers.active.data] if me.uv_layers.active else []))
 ev.to_mesh_clear()
clips={}
for name in ['idle','aim','fire','aim_fire','reload','reload_empty','draw','holster','inspect','equip']:
 a=bpy.data.actions[('AKMR_' if name in ['fire','aim_fire','equip'] else 'AKM_')+name];action(r,a)
 start,end=a.frame_range;hz=120 if name in ['fire','aim_fire','equip'] else 24;duration=(end-start)/hz
 clips[name]=[sample(r,start+k/120*hz) for k in range(round(duration*120)+1)]

bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;arms=bpy.data.objects['SK_Manny_Arms_Export']
action(r,bpy.data.actions['M4_idle']);base=sample(r,0)
magobj=next(o for o in r.children if o.type=='MESH' and 'Magazine' in o.name and o.name.endswith('_Export'))
ev=magobj.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();m4magverts=[ev.matrix_world@v.co for v in me.vertices];ev.to_mesh_clear()
action(r,bpy.data.actions['M4_MAT_reload']);grip=sample(r,76)
finger_names=[n for n in base if n.endswith('_l') and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))]
grip_rel={n:grip['hand_l'].inverted()@grip[n] for n in finger_names}
C=frame(base)@frame(srcidle).inverted();C.translation=base['hand_r'].translation-C.to_3x3()@srcidle['hand_r'].translation
def magframe(vs,reference=None):
 vs=np.array([tuple(v) for v in vs]);center=vs.mean(axis=0);values,axes=np.linalg.eigh(np.cov((vs-center).T))
 if reference is not None:
  for i in range(3):
   if Vector(axes[:,i]).dot(reference.col[i].to_3d())<0:axes[:,i]*=-1
 if np.linalg.det(axes)<0:axes[:,0]*=-1
 m=Matrix(axes.tolist()).to_4x4();m.translation=Vector(center);return m
m4mf=magframe(m4magverts)
akmf=magframe([C@Vector(v) for part in parts if part['bone']=='WPN_SOCKET_Magazine' for v in part['vertices']],m4mf)
m4gripframe=grip['WPN_SOCKET_Magazine']@base['WPN_SOCKET_Magazine'].inverted()@m4mf
grip_hand_relative=m4gripframe.inverted()@grip['hand_l']
pinch_local=grip['hand_l'].inverted()@((grip['thumb_03_l'].translation+grip['index_03_l'].translation)*.5)
boltverts=[C@Vector(v) for part in parts if part['bone']=='WPN_bolt' for v in part['vertices']]
right=frame(base).col[0].to_3d();edge=max(v.dot(right) for v in boltverts);tip=[v for v in boltverts if v.dot(right)>edge-.008]
knob_local=(C@srcidle['WPN_bolt']).inverted()@(sum(tip,Vector())/len(tip))
idle_hand=Matrix.LocRotScale((C@srcidle['hand_l']).translation,base['hand_l'].to_quaternion(),Vector((1,1,1)))
names=[b.name for b in r.pose.bones];parent={b.name:b.parent.name if b.parent else None for b in r.pose.bones}
rest={b.name:b.matrix_local.copy() for b in r.data.bones};lr={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
with bpy.data.libraries.load(str(O.parent/'ArmsRepair20260909/Integrated/SK_AKM_HandsRepair_Source.blend'),link=False) as (a,b):b.materials=list({m for p in parts for m in p['slots']})
mats={m.name:m for m in b.materials};export=[arms]
for part in parts:
 n=part['bone'];xf=r.matrix_world@rest[n]@(C@srcidle[n]).inverted()@C
 me=bpy.data.meshes.new(part['name']+'_Native');me.from_pydata([r.matrix_world.inverted()@xf@Vector(v) for v in part['vertices']],[],part['faces']);me.update()
 for mat in part['slots']:me.materials.append(mats[mat])
 for p,i in zip(me.polygons,part['mi']):p.material_index=i;p.use_smooth=True
 if part['uv']:
  uv=me.uv_layers.new(name='UVMap')
  for a,b in zip(uv.data,part['uv']):a.uv=b
 o=bpy.data.objects.new(part['name']+'_Native',me);s.collection.objects.link(o);o.parent=r;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=Matrix.Identity(4)
 vg=o.vertex_groups.new(name=n);vg.add(list(range(len(me.vertices))),1,'REPLACE');mod=o.modifiers.new('NativeRig','ARMATURE');mod.object=r;export.append(o)
for o in s.objects:
 if o.type=='MESH':o.hide_render=o not in export
r.animation_data.action=None
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT')
for o in export+[r]:o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(D/'SK_AKM_MannyNative.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False)

def arm_maps(src,side,hand_override=None):
 u,l,h=['upperarm_'+side,'lowerarm_'+side,'hand_'+side]
 shoulder0=base[u].translation;shoulder=shoulder0.copy();wrist=hand_override.translation if hand_override is not None else (C@src[h]).translation
 e0=base[l].translation;w0=base[h].translation
 a=(e0-shoulder).length;b=(w0-e0).length;delta=wrist-shoulder
 # Preserve the hand contact and segment lengths; allow the off-camera shoulder
 # to follow the action when the old rig's reach exceeds Manny's shorter arms.
 if delta.length>a+b-.025:shoulder+=delta.normalized()*(delta.length-(a+b-.025))
 delta=wrist-shoulder;dist=min(max(delta.length,abs(a-b)+1e-5),a+b-1e-5);direction=delta.normalized()
 pole=(C@src[l]).translation-shoulder;perp=(pole-direction*pole.dot(direction)).normalized()
 along=(a*a+dist*dist-b*b)/(2*dist);elbow=shoulder+direction*along+perp*math.sqrt(max(0,a*a-along*along));end=shoulder+direction*dist
 def align(oldhead,oldtail,newhead,newtail):
  q=(oldtail-oldhead).rotation_difference(newtail-newhead);m=q.to_matrix().to_4x4();m.translation=newhead-m.to_3x3()@oldhead;return m
 hm=hand_override.to_quaternion()@base[h].to_quaternion().inverted() if hand_override is not None else C.to_quaternion()@(src[h].to_quaternion()@srcidle[h].to_quaternion().inverted())@C.to_quaternion().inverted()
 H=hm.to_matrix().to_4x4();H.translation=end-H.to_3x3()@w0
 return {u:align(shoulder0,e0,shoulder,elbow),l:align(e0,w0,elbow,end),h:H},(wrist-end).length

report={'arms_vertices':len(arms.data.vertices),'arms_geometry':'Unchanged native M4 Manny mesh and weights','clips':{}}
for name,frames in clips.items():
 a=bpy.data.actions.new('AKM_Native_'+name);a.use_fake_user=True;action(r,a);prev={};err=0
 for k,src in enumerate(frames):
  t=k/120
  def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
  amount=smooth((t-.25)/.16)*(1-smooth((t-1.50)/.25)) if name in ['reload','reload_empty'] else 0
  hand_override=None
  if amount:
   target=C@src['WPN_SOCKET_Magazine']@srcidle['WPN_SOCKET_Magazine'].inverted()@C.inverted()@akmf@grip_hand_relative
   native_q=C.to_quaternion()@(src['hand_l'].to_quaternion()@srcidle['hand_l'].to_quaternion().inverted())@C.to_quaternion().inverted()@base['hand_l'].to_quaternion()
   hand_override=Matrix.LocRotScale((C@src['hand_l']).translation.lerp(target.translation,amount),native_q.slerp(target.to_quaternion(),amount),Vector((1,1,1)))
  semantic=1.75+max(0,t-.18) if name=='equip' else t
  if name in ['reload','reload_empty','equip'] and semantic>=1.5:
   magpose=C@src['WPN_SOCKET_Magazine']@srcidle['WPN_SOCKET_Magazine'].inverted()@C.inverted()@akmf
   start=magpose@grip_hand_relative
   end=C@src['WPN_root']@srcidle['WPN_root'].inverted()@C.inverted()@idle_hand
   outward=(start.translation-magpose.translation).normalized()
   def blend_hand(a,b,u):
    u=max(0,min(1,u));v=smooth(u)
    return Matrix.LocRotScale(a.translation.lerp(b.translation,v)+outward*(.065*math.sin(math.pi*u)),a.to_quaternion().slerp(b.to_quaternion(),v),Vector((1,1,1)))
   if name=='reload':
    u=(semantic-1.5)/1.1;hand_override=blend_hand(start,end,u);amount=1-smooth(u)
   else:
    q=C.to_quaternion()@(src['hand_l'].to_quaternion()@srcidle['hand_l'].to_quaternion().inverted())@C.to_quaternion().inverted()@base['hand_l'].to_quaternion()
    bolt=Matrix.LocRotScale((C@src['WPN_bolt']@knob_local)-q@pinch_local,q,Vector((1,1,1)))
    if semantic<2.08:hand_override=blend_hand(start,bolt,(semantic-1.5)/.58);amount=1
    elif semantic<2.38:hand_override=bolt;amount=1
    else:
     u=(semantic-2.38)/.77;hand_override=blend_hand(bolt,end,u);amount=1-smooth(u)
    if name=='equip' and t<.18:
     hand_override=blend_hand(idle_hand,hand_override,t/.18);amount*=smooth(t/.18)
  if baseline:hand_override=None;amount=0
  maps={}
  for side in ['l','r']:
   m,e=arm_maps(src,side,hand_override if side=='l' else None);maps.update(m);err=max(err,e)
  p={}
  for n in names:
   if n.startswith('WPN_') and n in src:p[n]=C@src[n]
   else:
    ancestor=n
    while ancestor and ancestor not in maps:ancestor=parent[ancestor]
    p[n]=maps[ancestor]@base[n] if ancestor else base[n].copy()
   p[n]=r.matrix_world.inverted()@p[n]
  # Reuse the accepted M4 wrap grasp during AKM magazine contact instead of
  # leaving the support-hand idle fingers open while the wrist moves.
  if amount:
   for n in finger_names:
    desired=p['hand_l']@grip_rel[n];old=p[n]
    p[n]=Matrix.LocRotScale(old.translation.lerp(desired.translation,amount),old.to_quaternion().slerp(desired.to_quaternion(),amount),Vector((1,1,1)))
  for n in names:
   local=lr[n].inverted()@(p[parent[n]].inverted()@p[n] if parent[n] else p[n]);loc,q,z=local.decompose()
   if n in prev and prev[n].dot(q)<0:q.negate()
   prev[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=z
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=k)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for key in fc.keyframe_points:key.interpolation='LINEAR'
 s.render.fps=120;s.frame_start=0;s.frame_end=len(frames)-1;bpy.ops.object.select_all(action='DESELECT');r.select_set(True)
 bpy.ops.export_scene.fbx(filepath=str(D/('A_AKM_'+name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=1,bake_anim_simplify_factor=0)
 report['clips'][name]={'duration':(len(frames)-1)/120,'max_reach_error_m':err};print('NATIVE_CLIP',name,report['clips'][name],flush=True)
action(r,bpy.data.actions['AKM_Native_idle']);s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(D/'AKM_MannyNative_Editable.blend'))
(D/'retarget.json').write_text(json.dumps(report,indent=2));print('AKM_NATIVE_BUILD_COMPLETE',flush=True)
