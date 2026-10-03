"""Requested death-floor diagnosis. Read active physics, skeleton and existing actors; no playback or save."""
import json
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
project=Path(u.Paths.project_dir()).resolve()
if project not in (ROOT.resolve(),Path('D:/FPS3D/FPSGAME-mp').resolve()):raise RuntimeError('Wrong project')
mesh=u.load_asset('/Game/Monsters/HundredEyedSlag/ArticulationV12/SK_HundredEyedSlag_V12')
if not mesh:raise RuntimeError('Current mesh not loaded')
physics=mesh.get_editor_property('physics_asset')
def value(obj,prop):
 try:
  v=obj.get_editor_property(prop)
  if hasattr(v,'export_text'):return v.export_text()
  return str(v)
 except Exception as ex:return 'UNAVAILABLE '+str(ex)
row={'project':str(project),'mesh':mesh.get_path_name(),'physics_asset':physics.get_path_name() if physics else None,
 'per_poly':value(mesh,'enable_per_poly_collision'),'body_setups':[],'actors':[]}
if physics:
 api=u.get_default_object(u.PhysicsAssetToolset)
 for name in api.call_method('GetBodyNames',(physics,)):
  shapes=api.call_method('GetBodyShapes',(physics,name))
  row['body_setups'].append({'bone':str(name),'shapes':[s.export_text() for s in shapes]})
 # NewObject-created setups are individual subobjects, even though the asset's
 # private body array itself is not exposed to editor Python.
 row['body_subobjects']=[]
 for ix in range(20):
  body=u.load_object(None,physics.get_path_name()+':SkeletalBodySetup_'+str(ix))
  if body:row['body_subobjects'].append({p:value(body,p) for p in ('bone_name','physics_type','collision_trace_flag','default_instance')})
 row['reference_bones']=[]
 clip=u.load_asset('/Game/Monsters/HundredEyedSlag/PolishV2/Animations/A_HundredEyedSlag_Death_V2')
 options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
 for time in (0.,.42):
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,options)
  for name in ('Armature','root','pelvis','spine','chest','front_palm_R','front_palm_L','rear_palm_L','rear_palm_R'):
   if name in [str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)]:
    row['reference_bones'].append({'time':time,'bone':name,'reference':str(u.AnimPoseExtensions.get_ref_bone_pose(pose,name,u.AnimPoseSpaces.WORLD)),'animated':str(u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD))})
world=u.EditorLevelLibrary.get_game_world()
row['game_world']=world.get_name() if world else None
if world:
 actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
 for actor in actors:
  if 'HundredEyedSlag' in actor.get_class().get_name():
   comp=actor.get_component_by_class(u.SkeletalMeshComponent)
   item={'name':actor.get_name(),'class':actor.get_class().get_name(),'state':value(actor,'state'),'location':str(actor.get_actor_location()),
    'mesh_location':str(comp.get_world_location()),'mesh_scale':str(comp.get_world_scale()),'simulating':comp.is_simulating_physics(),
    'profile':str(comp.get_collision_profile_name()),'enabled':str(comp.get_collision_enabled()),'object_type':str(comp.get_collision_object_type()),
    'world_static_response':str(comp.get_collision_response_to_channel(u.CollisionChannel.ECC_WORLD_STATIC)),
    'world_dynamic_response':str(comp.get_collision_response_to_channel(u.CollisionChannel.ECC_WORLD_DYNAMIC)),
    'root_bones':[],'physics_asset':comp.get_physics_asset().get_path_name() if comp.get_physics_asset() else None}
   for name in ('Armature','root','pelvis','spine','chest','front_palm_R','front_palm_L','rear_palm_L','rear_palm_R'):
    if comp.get_bone_index(name)>=0:item['root_bones'].append({'bone':name,'location':str(comp.get_socket_location(name)),'velocity':str(comp.get_physics_linear_velocity(name))})
   row['actors'].append(item)
(OUT/'ragdoll_sources.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
print('SLAG_DEATH_FLOOR_SOURCES '+str(row['physics_asset'])+' existing actors='+str(len(row['actors'])),flush=True)
