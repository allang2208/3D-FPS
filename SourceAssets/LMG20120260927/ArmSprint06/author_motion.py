"""Repair 201 forearm deformation and restore native one-hand sprint phases."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;sys.path.insert(0,str(O));from arm_recipe import support_arm,sprint_namespace
P=O.parent/'Support05';C=O.parent/'Charging04';S=O.parent.parent;E=O/'Exports';M=O/'Motions'
E.mkdir(exist_ok=True);M.mkdir(exist_ok=True);bpy.context.preferences.filepaths.save_version=0
metadata=json.loads((P/'motion_authoring.json').read_text());settings=json.loads((S/'RifleTacticalSprint20260915/sources.json').read_text())['AKM']
old_idle=Matrix(json.loads((P/'support_inputs.json').read_text())['root_bones']['hand_l'])
report={'revision':'ArmSprint06','source_revision':'Support05','animations':{},'runtime_tested':False,'visual_tested':False,'source_checks':'see focused_source_checks.json',
 'recipes':{'arm':'DanWesson71520260913/author_weapon.py::hand_at; FPSCastingMeshComponent.cpp palm-width roll; preserve native AKM helper-segment relationships',
 'sprint':'RifleTacticalSprint20260915/author_sprint.py::make_pose, AKM V4 settings; left arm only'}}
def assign(r,a):
 r.animation_data_create();r.animation_data.action=a
 if a.slots:r.animation_data.action_slot=a.slots[0]
def smooth(x):
 x=max(0,min(1,x));return x*x*x*(x*(x*6-15)+10)
def support_weight(key,frame,pose):
 if key.startswith('reload'):return 1-smooth((frame-12)/26)*(1-smooth((frame-238)/26))
 if key=='inspect':
  distance=((pose['WPN_root'].inverted()@pose['hand_l']).translation-old_idle.translation).length
  return 1-smooth((distance-.025)/.065)
 return 1.0
def left(n):return n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand_','thumb_','index_','middle_','ring_','pinky_','ik_hand_'))
def current(r):return {b.name:b.matrix.copy() for b in r.pose.bones}
def at(sc,frame):sc.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
fixed_idle=None
for key,meta in metadata['animations'].items():
 sprint=key.startswith('sprint_');source_path=P/'Motions'/f'A_LMG201_{key}.blend'
 bpy.ops.wm.open_mainfile(filepath=str(source_path),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];sc=bpy.context.scene;src=r.animation_data.action
 srcfps=sc.render.fps/sc.render.fps_base;start,end=map(float,src.frame_range);fps=120 if sprint else round(srcfps);count=round((end-start)/srcfps*fps)+1
 frames=[start+i*srcfps/fps for i in range(count)];names=[b.name for b in r.pose.bones];changed={n for n in names if left(n)}
 parents={b.name:b.parent.name if b.parent else None for b in r.data.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones}
 localrest={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
 source=[]
 for f in frames:at(sc,f);source.append(current(r))
 if not sprint:
  bpy.ops.wm.open_mainfile(filepath=str(C/'Motions'/f'A_LMG201_{key}.blend'),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];sc=bpy.context.scene;reference=[]
  for f in frames:at(sc,f);reference.append(current(r))
  bpy.ops.wm.open_mainfile(filepath=str(source_path),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];sc=bpy.context.scene;src=r.animation_data.action
 else:
  if fixed_idle is None:raise RuntimeError('Idle must be authored before sprint')
  native_sprint=sprint_namespace(fixed_idle,rest,parents,names,settings)
 samples=[];last_pose=None
 for i,(f,original) in enumerate(zip(frames,source)):
  target={n:m.copy() for n,m in original.items()}
  if sprint:
   t=(f-start)/max(end-start,1e-8);progress=1.0 if key=='sprint_loop' else 1-t if key=='sprint_exit' else t
   native=native_sprint['make_pose'](progress,2*math.pi*t if key=='sprint_loop' else None)
   for n in changed:target[n]=native[n].copy()
  else:
   w=support_weight(key,f,reference[i])
   if w>1e-8:
    authored=support_arm(reference[i],target,rest,names,w)
    for n in changed:target[n]=authored[n]
  if key=='idle' and i==0:fixed_idle={n:m.copy() for n,m in target.items()}
  # Re-key all bones only for the 60 -> 120 Hz sprint source-clock conversion.
  # Their world poses outside the left arm remain the original samples.
  baked=names if sprint else changed
  samples.append({n:localrest[n].inverted()@(target[parents[n]].inverted()@target[n] if parents[n] else target[n]) for n in baked})
 a=src.copy();a.name='A_LMG201_'+key+'_ArmSprint06';assign(r,a)
 bags=[bag for layer in a.layers for strip in layer.strips for bag in strip.channelbags];bag=bags[0]
 for b in bags:
  for curve in list(b.fcurves):
   if any(curve.data_path.startswith('pose.bones["'+n+'"]') for n in baked):b.fcurves.remove(curve)
 for n in sorted(baked):
  rows=[];previous=None;r.pose.bones[n].rotation_mode='QUATERNION'
  for sample in samples:
   loc,q,scale=sample[n].decompose()
   if previous is not None and previous.dot(q)<0:q.negate()
   previous=q.copy();rows.append((tuple(loc),tuple(q),tuple(scale)))
  for prop,size,j in [('location',3,0),('rotation_quaternion',4,1),('scale',3,2)]:
   for axis in range(size):
    curve=bag.fcurves.new(data_path=f'pose.bones["{n}"].{prop}',index=axis);curve.keyframe_points.add(count);values=[]
    for f,row in enumerate(rows):values.extend((f,row[j][axis]))
    curve.keyframe_points.foreach_set('co',values)
    for point in curve.keyframe_points:point.interpolation='LINEAR'
    curve.update()
 sc.render.fps=fps;sc.render.fps_base=1;sc.frame_start=0;sc.frame_end=count-1;sc.frame_set(0);bpy.context.view_layer.update()
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(E/f'A_LMG201_{key}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
 bpy.ops.wm.save_as_mainfile(filepath=str(M/f'A_LMG201_{key}.blend'))
 if key=='idle':bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_ArmSprint_Editable.blend'))
 report['animations'][key]={'source':str(source_path),'fps':fps,'frames':count,'duration':(count-1)/fps,'modified_tracks':sorted(changed),'left_mode':'native AKM V4 release/hang/return' if sprint else 'support phase arm repair, hand contacts preserved'}
 (O/'motion_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('201_ARMSPRINT06_ACTION_EXPORTED',key,flush=True)
print('201_ARMSPRINT06_AUTHORING_COMPLETE',flush=True)
