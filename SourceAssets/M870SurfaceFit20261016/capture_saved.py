"""Render saved compressed M870 clips and native outfits using runtime framing.

This is an isolated asset preview, not a gameplay/input acceptance run.
"""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent;OUT=O/'UEReview';OUT.mkdir(exist_ok=True)
ROOT='/Game/Weapons/M870/Tactical20261015';NATIVE='/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90/'
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();aa=u.get_editor_subsystem(u.EditorActorSubsystem)
selection=aa.get_selected_level_actors();created=[];origin=u.Vector(0,0,200000);report=[]
def spawn(cls,local=u.Vector(),rot=u.Rotator()):
 a=aa.spawn_actor_from_class(cls,origin+local,rot,transient=True);assert a;created.append(a);return a
def mul(a,b):return u.Quat(a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z)
def inv(q):return u.Quat(-q.x,-q.y,-q.z,q.w)
def bone(p,n):return u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.should_retarget=False
def pose(path,t=0.):
 seq=u.load_asset(path);assert seq,path;return u.AnimPoseExtensions.get_anim_pose_at_time(seq,t,opt)
def frame(p,up):
 rear=bone(p,'WPN_RearSight').translation;front=bone(p,'WPN_FrontSight').translation
 axis=front-rear;physical=bone(p,'WPN_root').rotation.rotate_vector(up)
 return u.MathLibrary.make_rot_from_xz(axis,physical).quaternion(),rear,bone(p,'hand_r').translation
ref=pose('/Game/Weapons/M4ContactImpactFinal/A_AKM_idle');idle=pose(ROOT+'/Animations/A_M870_idle')
refq,_,refhand=frame(ref,u.Vector(0,0,1));ownq,rear,ownhand=frame(idle,u.Vector(0,-1,0));base=u.Rotator(0,90,0).quaternion()
hipq=mul(mul(base,refq),inv(ownq));hipp=u.Vector(0,7,-7)+base.rotate_vector(refhand)+u.Vector(6,0,0)-hipq.rotate_vector(ownhand)
adsq=inv(ownq);adsp=u.Vector(18,0,0)-adsq.rotate_vector(rear)
def preview(path,p,location,rotation,hidden=()):
 actor=spawn(u.SkeletalMeshActor,location,rotation.rotator());actor.skeletal_mesh_component.set_visibility(False)
 c=actor.call_method('AddComponentByClass',(u.PoseableMeshComponent.static_class(),False,u.Transform(),False));mesh=u.load_asset(path);assert mesh,path
 c.set_skinned_asset_and_update(mesh);c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);c.set_cast_shadow(False);c.set_visibility(True);c.set_hidden_in_game(False)
 for n in u.AnimPoseExtensions.get_bone_names(p):
  if c.get_bone_index(n)>=0:c.set_bone_transform_by_name(n,bone(p,n),u.BoneSpaces.COMPONENT_SPACE)
 for index in hidden:c.show_material_section(index,index,False,0)
 copyopt=u.GeometryScriptCopyMeshFromComponentOptions();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.RENDER_DATA;copyopt.requested_lod=lod
 copied=u.GeometryScript_SceneUtils.copy_mesh_from_component(c,u.DynamicMesh(),copyopt,False)
 if copied[-1]!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot refresh posed mesh: '+path)
 return actor,c
try:
 for pos,power,size in [((-30,-50,70),5.,80),((60,50,40),3.,80),((100,-30,40),3.,80)]:
  loc=u.Vector(*pos);light=spawn(u.RectLight,loc,u.MathLibrary.find_look_at_rotation(loc,u.Vector(40,0,-10))).get_component_by_class(u.RectLightComponent)
  light.set_mobility(u.ComponentMobility.MOVABLE);light.set_intensity(power);light.set_editor_property('source_width',size);light.set_editor_property('source_height',size);light.set_editor_property('attenuation_radius',600.)
 capture=spawn(u.SceneCapture2D).capture_component2d;capture.capture_every_frame=False;capture.capture_on_movement=False;capture.always_persist_rendering_state=False
 capture.primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST
 capture.set_editor_property('show_flag_settings',[u.EngineShowFlagsSetting(show_flag_name=n,enabled=False) for n in ('DirectionalLights','SkyLighting','Atmosphere','Fog','GlobalIllumination','ReflectionEnvironment','MotionBlur','EyeAdaptation','DynamicShadows','ContactShadows','AmbientOcclusion','DistanceFieldAO')])
 pp=capture.post_process_settings
 for k,v in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),('override_auto_exposure_bias',True),('auto_exposure_bias',-3.),('override_bloom_intensity',True),('bloom_intensity',0.),('override_motion_blur_amount',True),('motion_blur_amount',0.)]:pp.set_editor_property(k,v)
 capture.post_process_settings=pp
 rt=u.RenderingLibrary.create_render_target2d(world,1280,720,u.TextureRenderTargetFormat.RTF_RGBA8,u.LinearColor(.04,.04,.04,1));capture.texture_target=rt;capture.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
 shots=[('hip','idle',0.,False),('ads','idle',0.,True),('pump','fire',.35,False),('closed','fire',.75,False)]
 for role in ('reload_continuous','reload_full'):
  for t in (.15,.40,44/60,1.16,1.57,3.23,5.73,6.,6.35,6.52,6.65):shots.append((role+'_'+str(round(t*60)),role,t,False))
 shots.append(('empty_return','reload_full',7.0666,False))
 for dressed in (False,True):
  for label,role,t,ads in shots:
   p=pose(ROOT+'/Animations/A_M870_'+role,t);location,rotation=(adsp,adsq) if ads else (hipp,hipq);parts=[];capture.clear_show_only_components()
   for path,hidden in [(ROOT+'/SK_M870_V7',(1,2,3,4)),(NATIVE+'SK_Super90_BareArmsV7',(0,1) if dressed else ())]+([(NATIVE+'SK_Super90_ue_chainmail_shirt',())] if dressed else []):
    a,c=preview(path,p,location,rotation,hidden);parts.append(a);capture.show_only_component(c)
   capture.fov_angle=65. if ads else 90.;u.AutomationLibrary.finish_loading_before_screenshot()
   for _ in range(3):capture.capture_scene();u.RenderingLibrary.read_render_target_raw_pixel(world,rt,640,360,False)
   file=('chain_' if dressed else 'bare_')+label+'.png';u.RenderingLibrary.export_render_target(world,rt,str(OUT),file)
   report.append({'file':file,'role':role,'time':t,'ads':ads,'chainmail':dressed,'hip_location':list(hipp.to_tuple()),'ads_location':list(adsp.to_tuple())});print('M870_UE_PREVIEW',file,flush=True)
   for a in parts:aa.destroy_actor(a);created.remove(a)
finally:
 for a in reversed(created):aa.destroy_actor(a)
 aa.set_selected_level_actors(selection);(OUT/'captures.json').write_text(json.dumps(report,indent=2))
print('M870_SAVED_PREVIEW_COMPLETE',len(report))
