"""Attach existing female-zombie source actions to the matching rig; no preview playback."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V02')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V02.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
rest_world=rig.matrix_world.copy()
ours=set(bpy.data.objects);motions=[]
for role,src in [('Idle','Idle05'),('Walk','Walk01Forward'),('Attack','AttackForward05')]:
 before=set(bpy.data.objects)
 bpy.ops.import_scene.fbx(filepath='D:/FPS3D/FPSGAME/Saved/NurseZombie/ANMS_ZombieFemale'+src+'.fbx',use_anim=True)
 imported=set(bpy.data.objects)-before;donor=next(o for o in imported if o.type=='ARMATURE')
 action=donor.animation_data.action.copy();action.name='Receptionist_'+role
 donor.animation_data.action=action;donor.animation_data.action_slot=action.slots[0]
 first,last=map(int,action.frame_range)
 # Production conversion matches the Nurse source convention: remove only
 # the linear horizontal root drift, retain every rotation and vertical key.
 for o in imported:
  if o.type=='MESH':bpy.data.objects.remove(o,do_unlink=True)
 if role!='Idle':
  samples=[]
  for f in range(first,last+1):
   bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
   samples.append(donor.matrix_world@donor.pose.bones['pelvis'].matrix)
  drift=samples[-1].translation-samples[0].translation;drift.z=0
  for f,world in zip(range(first,last+1),samples):
   bpy.context.scene.frame_set(f);p=donor.pose.bones['pelvis']
   p.matrix=donor.matrix_world.inverted()@Matrix.Translation(-drift*((f-first)/(last-first)))@world
   p.keyframe_insert(data_path='location',frame=f,group='pelvis')
 action.use_fake_user=True
 rig.animation_data_create();rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
 track=rig.animation_data.nla_tracks.new();track.name=role
 strip=track.strips.new(action.name,first,action);strip.action_slot=action.slots[0];strip.extrapolation='NOTHING'
 track.mute=True
 motions.append({'role':role,'action':action.name,'first':first,'last':last,'fps':bpy.context.scene.render.fps,'source':'Saved/NurseZombie/ANMS_ZombieFemale'+src+'.fbx','horizontal_drift_removed':role!='Idle'})
 for o in list(bpy.data.objects):
  if o not in ours:bpy.data.objects.remove(o,do_unlink=True)
rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
bpy.context.scene.frame_set(0)
rig.matrix_world=rest_world
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V02.blend'))
(ROOT/'animation_sources.json').write_text(json.dumps(motions,indent=2),encoding='utf-8')
print('RECEPTIONIST_SOURCE_ACTIONS_SAVED '+json.dumps(motions),flush=True)
