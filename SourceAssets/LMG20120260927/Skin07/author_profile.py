"""Rebuild cumulative skin roll from elbow cap to wrist; keep every contact."""
import bpy,json,math,importlib.util
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
O=Path(__file__).parent;P=O.parent/'ArmSprint06';S=O.parent.parent;E=O/'Exports';M=O/'Motions'
E.mkdir(exist_ok=True);M.mkdir(exist_ok=True);bpy.context.preferences.filepaths.save_version=0
spec=importlib.util.spec_from_file_location('established_elbow_profile',S/'RuneSword20260913/ChargedErgoV43/twist_distribution.py');recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)
measure=json.loads((O/'skin_diagnosis.json').read_text());stations={'lowerarm_l':0.,'lowerarm_twist_02_l':measure['stations']['lowerarm_twist_02_l'],'lowerarm_twist_01_l':measure['stations']['lowerarm_twist_01_l']}
source=json.loads((P/'motion_authoring.json').read_text());changed=set(stations)|{'hand_l'}
report={'revision':'Skin07','source_revision':'ArmSprint06','mesh_modified':False,'animations':{},'stations':stations,'recipe':'V43 transported elbow frame + V46 cumulative skin station principle; distal endpoint from current hand, no donor helper additions','runtime_tested':False,'visual_tested':False}
def assign(r,a):
 r.animation_data.action=a
 if a.slots:r.animation_data.action_slot=a.slots[0]
def signed_twist(q,axis):
 q.normalize()
 if q.w<0:q.negate()
 a=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
 return (a+math.pi)%(2*math.pi)-math.pi
for key,meta in source['animations'].items():
 bpy.ops.wm.open_mainfile(filepath=str(P/'Motions'/f'A_LMG201_{key}.blend'),use_scripts=False)
 sc=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];src=r.animation_data.action;fps=sc.render.fps/sc.render.fps_base;start,end=map(int,src.frame_range)
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
 lr={n:rest[parents[n]].inverted()@rest[n] for n in changed};samples=[];angles=[];before=[];previous=None
 for f in range(start,end+1):
  sc.frame_set(f);bpy.context.view_layer.update();pose={b.name:b.matrix.copy() for b in r.pose.bones};target=dict(pose)
  info=recipe.forearm_roll(pose,rest);axis=info['axis'];zero=info['no_roll']
  # The helpers are siblings, not cumulative parent links. Determine absolute
  # endpoint roll from the actual hand, never sum their old local rotations.
  hand_deform=pose['hand_l'].to_quaternion()@rest['hand_l'].to_quaternion().inverted()
  angle=signed_twist(hand_deform@zero.inverted(),axis)
  if previous is not None:
   while angle-previous>math.pi:angle-=2*math.pi
   while angle-previous<-math.pi:angle+=2*math.pi
  previous=angle;angles.append(math.degrees(angle));before.append(math.degrees(info['roll']))
  for n,station in stations.items():
   _,_,scale=pose[n].decompose()
   target[n]=Matrix.LocRotScale(pose[n].translation,Quaternion(axis,angle*station)@zero@rest[n].to_quaternion(),scale)
  target['hand_l']=pose['hand_l'].copy()
  samples.append({n:lr[n].inverted()@target[parents[n]].inverted()@target[n] for n in changed})
 a=src.copy();a.name='A_LMG201_'+key+'_Skin07';assign(r,a)
 bags=[b for layer in a.layers for strip in layer.strips for b in strip.channelbags];bag=bags[0]
 for b in bags:
  for c in list(b.fcurves):
   if any(c.data_path.startswith('pose.bones["'+n+'"]') for n in changed):b.fcurves.remove(c)
 for n in sorted(changed):
  values=[];last=None;r.pose.bones[n].rotation_mode='QUATERNION'
  for s in samples:
   loc,q,scale=s[n].decompose()
   if last is not None and last.dot(q)<0:q.negate()
   last=q.copy();values.append((tuple(loc),tuple(q),tuple(scale)))
  for prop,count,j in [('location',3,0),('rotation_quaternion',4,1),('scale',3,2)]:
   for i in range(count):
    c=bag.fcurves.new(data_path=f'pose.bones["{n}"].{prop}',index=i);c.keyframe_points.add(len(values));coords=[]
    for f,row in enumerate(values,start):coords.extend((f,row[j][i]))
    c.keyframe_points.foreach_set('co',coords)
    for p in c.keyframe_points:p.interpolation='LINEAR'
    c.update()
 sc.frame_set(start);bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(E/f'A_LMG201_{key}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
 bpy.ops.wm.save_as_mainfile(filepath=str(M/f'A_LMG201_{key}.blend'))
 if key=='idle':bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_SkinProfile_Editable.blend'))
 report['animations'][key]={'source':str(P/'Motions'/f'A_LMG201_{key}.blend'),'fps':fps,'frames':end-start+1,'duration':(end-start)/fps,'modified_tracks':sorted(changed),'old_elbow_roll_range_deg':[min(before),max(before)],'new_distal_roll_range_deg':[min(angles),max(angles)],'new_elbow_cap_roll_degrees':0.}
 (O/'motion_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('201_SKIN07_ACTION_EXPORTED',key,'elbow_before',min(before),max(before),'distal',min(angles),max(angles),flush=True)
print('201_SKIN07_AUTHORING_COMPLETE',flush=True)
