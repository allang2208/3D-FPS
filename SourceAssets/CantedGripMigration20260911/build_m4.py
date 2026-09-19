import bpy,json,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;sys.path.insert(0,str(O))
from audit_m4 import OLD,support,weight
D=O/'m4/canted';D.mkdir(parents=True,exist_ok=True);report={}
for clip,info in json.loads((OLD/'animation_build.json').read_text()).items():
 bpy.ops.wm.open_mainfile(filepath=str(OLD/f'A_M4_Canted_{clip}.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;hz=info['sample_rate'];end=info['frames']
 names=[b.name for b in r.pose.bones];parents={b.name:b.parent.name if b.parent else None for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
 output=[];oldposes=[]
 for k in range(round(end*hz/60)+1):
  f=k*60/hz;s.frame_set(int(f),subframe=f%1);p={b.name:b.matrix.copy() for b in r.pose.bones};oldposes.append({n:m.copy() for n,m in p.items()});w=weight(clip,f,end)
  if w>0:support(p,rest,w)
  output.append({n:lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]) for n in names})
 a=bpy.data.actions.new(f'A_M4_Canted_{clip}_Ergonomic');a.use_fake_user=True;r.animation_data.action=a;previous={}
 for k,pose in enumerate(output):
  for n,m in pose.items():
   loc,q,z=m.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=z
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=k*60/hz)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
 maximum=0
 for k,old in enumerate(oldposes):
  f=k*60/hz;s.frame_set(int(f),subframe=f%1)
  for n in names:
   if n in ['upperarm_l','lowerarm_l'] or 'twist' in n and n.endswith('_l'):continue
   maximum=max(maximum,(r.pose.bones[n].matrix.translation-old[n].translation).length)
 assert maximum<.00003,(clip,maximum)
 s.frame_set(0);name=f'A_M4_Canted_{clip}';bpy.ops.wm.save_as_mainfile(filepath=str(D/(name+'.blend')))
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(D/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=60/hz,bake_anim_simplify_factor=0)
 report[clip]={**info,'source':str(OLD/f'A_M4_Canted_{clip}.blend'),'preserved_bone_position_error_m':maximum}
 (D/'build.json').write_text(json.dumps(report,indent=2));print('CANTED_M4_BUILD_PASS',clip,maximum,flush=True)
