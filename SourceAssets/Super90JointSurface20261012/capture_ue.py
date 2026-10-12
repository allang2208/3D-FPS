"""User-requested before/after material and pose review, temporary actors only."""
import json,sys
from pathlib import Path
import unreal as u
O=Path(__file__).parent;sys.path.insert(0,str(O))
from ue_pipeline import DEST
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Stop PIE for the isolated Super90 capture.')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();aa=u.get_editor_subsystem(u.EditorActorSubsystem)
selection=aa.get_selected_level_actors();created=[];origin=u.Vector(0,0,200000)
def spawn(cls,local=u.Vector(),rot=u.Rotator()):
 a=aa.spawn_actor_from_class(cls,origin+local,rot,transient=True);assert a;created.append(a);return a
report=[]
try:
 for pos,power,size in [((-60,0,80),3.5,80),((60,-60,20),1.8,80),((-30,-100,40),2.2,80)]:
  loc=u.Vector(*pos);light=spawn(u.RectLight,loc,u.MathLibrary.find_look_at_rotation(loc,u.Vector(0,-30,-20))).get_component_by_class(u.RectLightComponent)
  light.set_mobility(u.ComponentMobility.MOVABLE);light.set_intensity(power)
  light.set_editor_property('source_width',size);light.set_editor_property('source_height',size);light.set_editor_property('attenuation_radius',500.)
 capture=spawn(u.SceneCapture2D).capture_component2d
 capture.capture_every_frame=False;capture.capture_on_movement=False;capture.always_persist_rendering_state=False
 capture.primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST
 flags=[u.EngineShowFlagsSetting(show_flag_name=n,enabled=False) for n in ('DirectionalLights','SkyLighting','Atmosphere','Fog','GlobalIllumination','ReflectionEnvironment','MotionBlur','EyeAdaptation','DynamicShadows','ContactShadows','AmbientOcclusion','DistanceFieldAO')]
 capture.set_editor_property('show_flag_settings',flags)
 pp=capture.post_process_settings
 for k,v in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),('override_auto_exposure_bias',True),('auto_exposure_bias',-4.),('override_bloom_intensity',True),('bloom_intensity',0.),('override_motion_blur_amount',True),('motion_blur_amount',0.)]:pp.set_editor_property(k,v)
 capture.post_process_settings=pp
 rt=u.RenderingLibrary.create_render_target2d(world,1000,750,u.TextureRenderTargetFormat.RTF_RGBA8,u.LinearColor(.025,.025,.025,1));capture.texture_target=rt
 shots=[('idle','idle',0.,u.Vector(),u.Vector(0,-40,-22),65.),('reload','reload_full',1.5,u.Vector(),u.Vector(0,-40,-22),65.),('reload_late','reload_full',3.83,u.Vector(),u.Vector(0,-40,-22),65.),('elbow','idle',0.,u.Vector(-8,-3,-5),u.Vector(-18,-33,-25),40.)]
 for version,path in [('before','/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7'),('after',DEST+'/Candidates/SK_Super90JointCandidate_full')]:
  mesh=u.load_asset(path);assert mesh
  options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh;options.evaluation_type=u.AnimDataEvalType.COMPRESSED
  for label,clip,time,eye,target,fov in shots:
   # A fresh primitive per shot avoids frame-zero skin-cache reuse in a
   # commandlet. Shadow proxies are excluded from this surface comparison.
   actor=spawn(u.SkeletalMeshActor);actor.skeletal_mesh_component.set_visibility(False)
   preview=actor.call_method('AddComponentByClass',(u.PoseableMeshComponent.static_class(),False,u.Transform(),False))
   preview.set_skinned_asset_and_update(mesh);preview.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
   preview.set_cast_shadow(False);preview.set_visibility(True);preview.set_hidden_in_game(False)
   capture.clear_show_only_components();capture.show_only_component(preview)
   seq=u.load_asset('/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_'+clip);pose=u.AnimPoseExtensions.get_anim_pose_at_time(seq,time,options)
   for bone in u.AnimPoseExtensions.get_bone_names(pose):preview.set_bone_transform_by_name(bone,u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.WORLD),u.BoneSpaces.COMPONENT_SPACE)
   options_copy=u.GeometryScriptCopyMeshFromComponentOptions();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.RENDER_DATA;options_copy.requested_lod=lod
   copied=u.GeometryScript_SceneUtils.copy_mesh_from_component(preview,u.DynamicMesh(),options_copy,False)
   if copied[-1]!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot refresh the review pose: '+str(copied))
   capture.get_owner().set_actor_location_and_rotation(origin+eye,u.MathLibrary.find_look_at_rotation(eye,target),False,True);capture.fov_angle=fov
   capture.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
   u.AutomationLibrary.finish_loading_before_screenshot()
   for _ in range(5):
    capture.capture_scene();u.RenderingLibrary.read_render_target_raw_pixel(world,rt,500,375,False)
   filename='ue_'+version+'_'+label+'.png';u.RenderingLibrary.export_render_target(world,rt,str(O),filename)
   report.append(dict(version=version,mesh=path,clip=clip,time=time,file=filename))
   print('SUPER90_UE_CAPTURE',filename,flush=True)
   if label=='idle':
    capture.capture_source=u.SceneCaptureSource.SCS_BASE_COLOR
    capture.capture_scene();u.RenderingLibrary.read_render_target_raw_pixel(world,rt,500,375,False)
    u.RenderingLibrary.export_render_target(world,rt,str(O),'ue_'+version+'_basecolour.png')
   aa.destroy_actor(actor);created.remove(actor)
finally:
 for a in reversed(created):aa.destroy_actor(a)
 aa.set_selected_level_actors(selection)
 (O/'ue_captures.json').write_text(json.dumps(report,indent=2))
