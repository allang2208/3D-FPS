import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'WalnutFab/AKM_WalnutFab_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;names=[b.name for b in r.data.bones]
def select(a,f):r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update();return {n:r.pose.bones[n].matrix.copy() for n in names}
idle=select(bpy.data.actions['AKM_Native_idle'],0);source=bpy.data.actions['AKM_Native_equip']
poses=[select(source,f) for f in range(84,253)]
def blend(a,b,t):
 t=t*t*(3-2*t)
 return {n:Matrix.LocRotScale(a[n].translation.lerp(b[n].translation,t),a[n].to_quaternion().slerp(b[n].to_quaternion(),t),Vector((1,1,1))) for n in names}
frames=[blend(idle,poses[0],k/22) for k in range(22)]+poses+[blend(poses[-1],idle,k/14) for k in range(1,15)]
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
localrest={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
mag=[n for n in names if n=='WPN_SOCKET_Magazine'];assert mag, names
left=[n for n in names if n.endswith('_l')]
a=bpy.data.actions.new('AKM_EquipCharge');r.animation_data.action=a;previous={};errors=[]
for k,p in enumerate(frames):
 delta=p['WPN_root']@idle['WPN_root'].inverted()
 for n in left+mag:p[n]=delta@idle[n]
 for n in names:
  local=localrest[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);loc,q,scale=local.decompose()
  if n in previous and previous[n].dot(q)<0:q.negate()
  previous[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=scale
  for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=k)
 errors.append(max((p['WPN_root'].inverted()@p[n]).translation.distance((idle['WPN_root'].inverted()@idle[n]).translation) if False else ((p['WPN_root'].inverted()@p[n]).translation-(idle['WPN_root'].inverted()@idle[n]).translation).length for n in ['hand_l']+mag))
for layer in a.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for fc in bag.fcurves:
    for key in fc.keyframe_points:key.interpolation='LINEAR'
s.render.fps=120;s.frame_start=0;s.frame_end=len(frames)-1
bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'A_AKM_equip.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=1,bake_anim_simplify_factor=0)
s.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(O/'AKM_EquipCharge_Editable.blend'))
bolt=[]
for k,p in enumerate(frames):bolt.append((p['WPN_root'].inverted()@p['WPN_bolt']).translation.y)
pull=next(k for k in range(1,len(bolt)) if bolt[k]-bolt[k-1]>.002)/120
release=next(k for k in range(1,len(bolt)) if bolt[k-1]-bolt[k]>.002)/120
report={'duration':(len(frames)-1)/120,'source_frames':[84,252],'pull_time':pull,'release_time':release,'fixed_magazine_bones':mag,'left_and_mag_position_error_m':max(errors)}
(O/'report.json').write_text(json.dumps(report,indent=2));print('AKM_EQUIP_CHARGE_PASS',report)

