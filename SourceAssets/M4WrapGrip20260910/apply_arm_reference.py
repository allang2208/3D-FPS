import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Quaternion
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;names=[b.name for b in r.pose.bones];parent={b.name:b.parent.name if b.parent else None for b in r.pose.bones};rest={b.name:b.bone.matrix_local.copy() for b in r.pose.bones};lr={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
def activate(a):r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def mix(a,b,w):
 p,q,z=a.decompose();P,Q,Z=b.decompose();return Matrix.LocRotScale(p.lerp(P,w),q.slerp(Q,w),z.lerp(Z,w))
activate(bpy.data.actions['M4_reload']);s.frame_set(146);bpy.context.view_layer.update();ref={b.name:b.matrix.copy() for b in r.pose.bones};report={}
for clip,end in [('reload',126),('reload_empty',162)]:
 a=bpy.data.actions['M4_MAT_'+clip];assert not a.get('natural_arm_reference_applied',False);activate(a);poses=[]
 for k in range(end*8+1):
  f=k/8;s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();p={b.name:b.matrix.copy() for b in r.pose.bones};delta=p['hand_l']@ref['hand_l'].inverted();goal={n:delta@ref[n] if n.endswith('_l') and not n.startswith(('hand','thumb','index','middle','ring','pinky')) else p[n] for n in names};w=smooth((f-6)/29)*(1-smooth((f-101)/10)) if clip=='reload_empty' else smooth(f/12)*(1-smooth((f-110)/9));q={}
  for n in names:
   old=p[parent[n]].inverted()@p[n] if parent[n] else p[n];new=goal[parent[n]].inverted()@goal[n] if parent[n] else goal[n];q[n]=(q[parent[n]] if parent[n] else Matrix.Identity(4))@mix(old,new,w)
  correction=p['hand_l']@q['hand_l'].inverted()
  for n in names:
   if n.endswith('_l'):q[n]=correction@q[n]
  poses.append({n:q[n] for n in names})
 previous={}
 for k,p in enumerate(poses):
  f=k/8
  for n in names:
   if not n.endswith('_l'):continue
   local=lr[n].inverted()@(p[parent[n]].inverted()@p[n]);loc,q,z=local.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=z
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f)
 a['natural_arm_reference_applied']=True;s.render.fps=60;s.frame_start=0;s.frame_end=end;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(O/f'A_M4_MAT_{clip}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.125,bake_anim_simplify_factor=0)
 report[clip]={'arm_reference':'Original M4_reload frame 146','hand_contact':'Preserved complete hand transform and finger local poses','frames':end*8+1}
s.frame_set(80);bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));(O/'arm_reference_applied.json').write_text(json.dumps(report,indent=2));print('NATURAL_ARM_REFERENCE_APPLIED')
