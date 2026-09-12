"""Bind supplied QBZ geometry to the accepted Manny rig; author dedicated clips."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'SourceInspect.blend'))
src=bpy.data.objects['QBZ'];me=src.data
verts=[src.matrix_world@v.co for v in me.vertices];faces=[list(p.vertices) for p in me.polygons]
uv=[tuple(x.uv) for x in me.uv_layers.active.data];mi=[p.material_index for p in me.polygons]
materials=[m.copy() for m in me.materials]
for i,m in enumerate(materials):m.name='QBZSourceBody' if i==0 else 'QBZSourceMagazine';m.use_fake_user=True
bpy.data.libraries.write(str(O/'SourceMaterials.blend'),set(materials),fake_user=True)
comps=json.loads((O/'components.json').read_text())[0]['components']
bone_for={i:'WPN_root' for i in range(len(verts))}
for c,b in [(93,'WPN_SOCKET_Magazine'),(85,'WPN_Trigger'),(89,'WPN_ChargingHandle')]:
 for i in comps[c]['ids']:bone_for[i]=b
ironids={i for c in [80,81,82,94] for i in comps[c]['ids']}
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];hands=bpy.data.objects['SK_Manny_Arms_Export']
def setaction(a):r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def sample(a,f):
 setaction(a);s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
idle=bpy.data.actions['M4_idle'];base=sample(idle,0);root=base['WPN_root'];oldrest={b.name:b.matrix_local.copy() for b in r.data.bones}
for o in list(s.objects):
 if o.type=='MESH' and o!=hands:bpy.data.objects.remove(o,do_unlink=True)
with bpy.data.libraries.load(str(O/'SourceMaterials.blend'),link=False) as (a,b):b.materials=a.materials
mats=b.materials;bodymat=next(m for m in mats if 'QBZSourceBody' in m.name);magmat=next(m for m in mats if 'QBZSourceMagazine' in m.name)
bodymat.name='M_QBZ191_Body';magmat.name='M_QBZ191_Magazine';ironmat=bodymat.copy();ironmat.name='M_QBZ191_Irons'
xf=Matrix.Translation((-.005,-.11,.065))
# Keep the common arm rest skeleton. Weapon sight/muzzle marker rest positions
# are specific to this model, so the exported skeleton is private to QBZ-191.
markers={'WPN_RearSight':(.000688,.009231,.122149),'WPN_FrontSight':(.000689,-.343514,.120490),'WPN_SOCKET_Muzzle':(.001,-.562,.057),'WPN_SOCKET_Eject':(.025,-.09,.077)}
setaction(idle);r.animation_data_clear();bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r;bpy.ops.object.mode_set(mode='EDIT')
for n,v in markers.items():
 bone=r.data.edit_bones[n];delta=(oldrest['WPN_root']@Vector(v))-bone.head;bone.head+=delta;bone.tail+=delta
bpy.ops.object.mode_set(mode='OBJECT');r.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in r.data.bones};names=list(rest);parents={b.name:b.parent.name if b.parent else None for b in r.data.bones};lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
newverts=[rest[bone_for[i]]@base[bone_for[i]].inverted()@root@xf@v for i,v in enumerate(verts)]
mesh=bpy.data.meshes.new('QBZ191_Bound');mesh.from_pydata(newverts,[],faces);mesh.update()
for m in [bodymat,magmat,ironmat]:mesh.materials.append(m)
layer=mesh.uv_layers.new(name='UVMap')
for a,b in zip(layer.data,uv):a.uv=b
for p,index in zip(mesh.polygons,mi):p.material_index=2 if all(v in ironids for v in p.vertices) else index;p.use_smooth=True
gun=bpy.data.objects.new('QBZ191_Export',mesh);s.collection.objects.link(gun);gun.parent=r;gun.matrix_parent_inverse=Matrix.Identity(4);gun.matrix_basis=Matrix.Identity(4)
for bone in set(bone_for.values()):gun.vertex_groups.new(name=bone).add([i for i,b in bone_for.items() if b==bone],1,'REPLACE')
gun.modifiers.new('QBZ191_Rig','ARMATURE').object=r
normal=bpy.data.actions['M4_MAT_reload'];equip=bpy.data.actions['M4_MAT_equip_charge']
sources={'idle':(idle,180),'aim':(bpy.data.actions['M4_aim'],2),'fire':(bpy.data.actions['M4_fire'],46),'aim_fire':(bpy.data.actions['M4_aim_fire'],46),'reload':(normal,126),'equip_charge':(equip,38),'reload_empty':(normal,164)}
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def shift_arm(p,side,shift):
 # Native bone lengths and accepted finger curls remain intact.
 un,ln,hn='upperarm_'+side,'lowerarm_'+side,'hand_'+side
 a,b,c=[p[n].translation.copy() for n in (un,ln,hn)];goal=c+shift;l1=(b-a).length;l2=(c-b).length
 axis=(goal-a).normalized();d=(goal-a).length
 if d>=l1+l2:a+=axis*(d-l1-l2+.0001);d=(goal-a).length
 pole=b-a;pole-=axis*pole.dot(axis);pole.normalize();along=(l1*l1-l2*l2+d*d)/(2*d);elbow=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
 p[un]=Matrix.LocRotScale(a,(b-p[un].translation).rotation_difference(elbow-a)@p[un].to_quaternion(),p[un].to_scale())
 p[ln]=Matrix.LocRotScale(elbow,(c-b).rotation_difference(goal-elbow)@p[ln].to_quaternion(),p[ln].to_scale())
 for n in names:
  if n==hn or n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):p[n].translation+=shift
  elif n.endswith('_'+side) and n.startswith(('upperarm_twist','lowerarm_twist')):p[n]=p[parents[n]]@lr[n]
actions={};report={}
for kind,(source,end) in sources.items():
 poses=[]
 for k in range(end*2+1):
  f=k/2
  p=sample(equip,f-126) if kind=='reload_empty' and f>126 else sample(source,min(f,126) if kind=='reload_empty' else f)
  q=p['WPN_root'].to_quaternion()
  # Handguard sits 12 mm lower than the reference. Magazine contact uses the
  # fitted QBZ envelope; only the complete left arm is repositioned.
  grab=0
  if kind in ['reload','reload_empty'] and f<=126:grab=smooth((f-43)/18)*(1-smooth((f-98)/12))
  shift=Vector((0,0,.018)).lerp(Vector((-.007,-.02,-.027)),grab)
  ef=f if kind=='equip_charge' else f-126 if kind=='reload_empty' and f>126 else -1
  charge=smooth(ef/8)*(1-smooth((ef-28)/10)) if ef>=0 else 0
  shift_arm(p,'r',q@Vector((-.03*charge,-.05-.04*charge,.025-.05*charge)))
  shift_arm(p,'l',q@shift)
  for n,v in markers.items():
   p[n]=p['WPN_root']@rest['WPN_root'].inverted()@rest[n]
  poses.append(p)
 a=bpy.data.actions.new('QBZ191_'+kind);a.use_fake_user=True;r.animation_data.action=a;previous={}
 for k,p in enumerate(poses):
  for n in names:
   local=lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);loc,rot,scale=local.decompose()
   if n in previous and previous[n].dot(rot)<0:rot.negate()
   previous[n]=rot.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=rot;b.scale=scale
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=k/2)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for key in fc.keyframe_points:key.interpolation='LINEAR'
 s.render.fps=60;s.frame_start=0;s.frame_end=end;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(O/f'A_QBZ191_{kind}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
 actions[kind]=a;report[kind]={'source':source.name,'duration':end/60,'frames':end,'fps':60,'sample_rate':120}
setaction(actions['idle']);s.frame_set(0);s.frame_end=180
bpy.ops.object.select_all(action='DESELECT')
for o in [r,hands,gun]:o.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'SK_QBZ191_Manny.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False)
for o in s.objects:o.hide_render=o.name not in ['SK_M4_Infima','SK_Manny_Arms_Export','QBZ191_Export']
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_Editable.blend'))
(O/'build.json').write_text(json.dumps({'clips':report,'mesh_vertices':len(verts),'source_transform':list(xf.translation),'markers':markers,'parts':{'magazine':93,'trigger':85,'charging_handle':89},'hands_source':'M4TacticalToss20260910/SK_Manny_Arms_Export'},indent=2))
print('QBZ191_BUILD_COMPLETE')
