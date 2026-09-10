import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Matrix,Vector,Euler
O=Path(__file__).parent;source=O.parent/'M4WrapGrip20260910/M4_Hand_MAT_Editable.blend';bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;old=bpy.data.actions['M4_MAT_reload_empty'];r.animation_data.action=old;r.animation_data.action_slot=old.slots[0]
names=[b.name for b in r.pose.bones];parent={b.name:b.parent.name if b.parent else None for b in r.pose.bones};rest={b.name:b.bone.matrix_local.copy() for b in r.pose.bones};lr={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
def sample(f):
 s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
def smooth(v):v=max(0,min(1,v));return v*v*(3-2*v)
def mapped(f):
 start=130-5/1.5
 if 111<f<start:return 111+(f-111)*14/(start-111)
 if start<=f<130:return 130-(130-f)*1.5
 return f
out=[];max_move=0;max_angle=0
for k in range(1297):
 f=k/8;p=sample(f);g=mapped(f)
 if abs(g-f)>1e-8:
  q=sample(g);delta=p['WPN_root']@q['WPN_root'].inverted()
  for n in names:
   if n.endswith('_l'):p[n]=delta@q[n]
 t=(f-130)/60
 if 0<t<.17:
  pulse=math.sin(2*math.pi*14*t)*math.exp(-t/.045)*smooth(t/.008)*(1-smooth((t-.12)/.05));translation=Vector((-.003*pulse,0,-.001*pulse));rotation=Euler((math.radians(.8)*pulse,0,math.radians(.45)*pulse)).to_quaternion();root=p['WPN_root'];delta=root@Matrix.LocRotScale(translation,rotation,Vector((1,1,1)))@root.inverted()
  max_move=max(max_move,translation.length*1000);max_angle=max(max_angle,math.degrees(rotation.angle))
  for n in names:p[n]=delta@p[n]
 out.append(p)
old.name='REFERENCE_wrap_empty';a=bpy.data.actions.new('M4_MAT_reload_empty');a.use_fake_user=True;r.animation_data.action=a;previous={}
for k,p in enumerate(out):
 for n in names:
  local=lr[n].inverted()@(p[parent[n]].inverted()@p[n] if parent[n] else p[n]);loc,q,z=local.decompose()
  if n in previous and previous[n].dot(q)<0:q.negate()
  previous[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=z
  for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=k/8)
for layer in a.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for fc in bag.fcurves:
    for key in fc.keyframe_points:key.interpolation='LINEAR'
s.render.fps=60;s.frame_start=0;s.frame_end=162;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'A_M4_MAT_reload_empty.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.125,bake_anim_simplify_factor=0)
s.frame_set(130);bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source':str(source),'strike_speed_multiplier':1.5,'old_strike_frames':[125,130],'new_strike_frames':[130-5/1.5,130],'impact_seconds':130/60,'duration':2.7,'additional_shake_peak_mm':max_move,'additional_shake_peak_degrees':max_angle,'additional_shake_duration':.17,'sample_rate':480};(O/'authoring.json').write_text(json.dumps(report,indent=2));print('SLAP_IMPACT_AUTHORED',report)
