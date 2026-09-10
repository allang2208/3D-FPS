import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Matrix,Vector,Euler
O=Path(__file__).parent;source=O.parent/'M4SlapImpact20260910/M4_Hand_MAT_Editable.blend';bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;old=bpy.data.actions['M4_MAT_reload_empty'];r.animation_data.action=old;r.animation_data.action_slot=old.slots[0]
names=[b.name for b in r.pose.bones];parent={b.name:b.parent.name if b.parent else None for b in r.pose.bones};rest={b.name:b.bone.matrix_local.copy() for b in r.pose.bones};lr={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
def sample(f):
 s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
def smooth(v):v=max(0,min(1,v));return v*v*(3-2*v)
def mix(A,B,u):
 return Matrix.LocRotScale(A.translation.lerp(B.translation,u),A.to_quaternion().slerp(B.to_quaternion(),u),A.to_scale().lerp(B.to_scale(),u))
normal=bpy.data.actions['M4_MAT_reload']
def pose(a,f):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];return sample(f)
anchors=[(0,0),(8,8),(28,20),(29,21),(43,35),(61,43),(76,54),(95,80),(98,88)]
def mapped(f):
 for (a,A),(b,B) in zip(anchors,anchors[1:]):
  if a<=f<=b:return A+(B-A)*(f-a)/(b-a)
 return 88
hold=pose(old,88);endnormal=pose(normal,98)
transition={n:( (hold['WPN_root'].inverted()@hold[n]).translation-(endnormal['WPN_root'].inverted()@endnormal[n]).translation).length*1000 for n in ['hand_l','lowerarm_l','index_03_l','thumb_03_l','WPN_SOCKET_Magazine']}
out=[]
for k in range(1009):
 f=k/8;p=pose(normal,f);baseline={n:m.copy() for n,m in p.items()}
 if f<=98:
  q=pose(old,mapped(f));root=q['WPN_root'];delta=root@p['WPN_root'].inverted()
  for n in names:p[n]=delta@p[n]
  for n in names:
   if n.endswith('_l') or n=='WPN_SOCKET_Magazine':p[n]=q[n].copy()
 else:
  root=mix(hold['WPN_root'],p['WPN_root'],smooth((f-98)/12));delta=root@p['WPN_root'].inverted()
  for n in names:p[n]=delta@p[n]
 out.append(p)
normal.name='REFERENCE_wrap_reload';a=bpy.data.actions.new('M4_MAT_reload');a.use_fake_user=True;r.animation_data.action=a;previous={}
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
s.render.fps=60;s.frame_start=0;s.frame_end=126;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'A_M4_MAT_reload.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.125,bake_anim_simplify_factor=0)
s.frame_set(76);bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'))
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source':str(source),'reference':'M4_MAT_reload_empty, accepted visible toss and retrieval','time_map_normal_to_empty':anchors,'transition_relative_error_mm':transition,'duration':2.1,'sample_rate':480,'grasp_frames':[61,98],'mechanical_cues_seconds':[29/60,76/60,95/60],'bolt':'Preserve loaded-chamber normal-reload mechanical poses; no empty slap or bolt release'}
(O/'authoring.json').write_text(json.dumps(report,indent=2));print('TACTICAL_TOSS_AUTHORED',report)
