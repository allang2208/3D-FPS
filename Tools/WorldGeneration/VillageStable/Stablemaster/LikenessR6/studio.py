"""Photograph the active stablemaster blueprint in a transient world, at the reference camera scale."""
import json, os
from pathlib import Path
import unreal as u

batch=Path(os.environ['STABLEMASTER_WORK'])
out=Path(os.environ['STABLEMASTER_REVIEW'])
stage=os.environ['STABLEMASTER_STAGE']
report=json.loads((batch/('map-'+stage+'.json')).read_bytes())
world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
def spawn(cls,position=(0,0,0),rot=None):
    return actors.spawn_actor_from_class(cls,u.Vector(*position),rot or u.Rotator(),True)
npc=spawn(u.load_class(None,report['actor_class']),(0,0,84),u.Rotator(yaw=90))
placed={c['name']:c for c in report['parts']}
for c in npc.get_components_by_class(u.SkeletalMeshComponent):
    binding=placed[c.get_name()]
    if stage=='before' and c.skeletal_mesh_asset.get_path_name()!=binding['mesh']:
        c.set_skeletal_mesh_asset(u.load_asset(binding['mesh']))
    if c.skeletal_mesh_asset.get_path_name()!=binding['mesh'] or [c.get_material(i).get_path_name() for i in range(c.get_num_materials())]!=binding['materials']:
        raise ValueError('Portrait components differ from the saved village instance')
    c.set_forced_lod(1)
for pitch,yaw,intensity in [(-26,-110,1.95),(-14,-48,1.2),(-35,91,.8),(-12,175,1.1),(15,172,1.45),(37,-78,.55)]:
    l=spawn(u.DirectionalLight,(0,0,260),u.Rotator(pitch=pitch,yaw=yaw)).light_component
    l.set_mobility(u.ComponentMobility.MOVABLE);l.set_intensity(intensity);l.set_cast_shadows(False)
sky=spawn(u.SkyLight).light_component
sky.set_mobility(u.ComponentMobility.MOVABLE)
sky.set_editor_property('source_type',u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
sky.set_editor_property('cubemap',u.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'));sky.set_intensity(.7)
cam=spawn(u.SceneCapture2D);cap=cam.capture_component2d
cap.capture_every_frame=cap.capture_on_movement=False
cap.projection_type=u.CameraProjectionMode.ORTHOGRAPHIC;cap.ortho_width=30.
pp=cap.post_process_settings
for k,v in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),('override_auto_exposure_bias',True),('auto_exposure_bias',.2),('override_vignette_intensity',True),('vignette_intensity',0.)]:pp.set_editor_property(k,v)
cap.set_editor_property('post_process_settings',pp)
for cmd in ['r.TextureStreaming 0','r.ScreenPercentage 100','r.Shadow.Virtual.Enable 0','r.Tonemapper.Sharpen 0','r.MotionBlurQuality 0']:
    u.SystemLibrary.execute_console_command(world,cmd)
u.AutomationLibrary.finish_loading_before_screenshot()
aim=u.Vector(0.,0.,153.175)
for slug,x,y in [('front',0.,100.),('side',100.,0.)]:
    eye=aim+u.Vector(x,y,0);cam.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,aim),False,False)
    for mode,source in [('lit',u.SceneCaptureSource.SCS_FINAL_COLOR_LDR),('albedo',u.SceneCaptureSource.SCS_BASE_COLOR)]:
        cap.capture_source=source
        rt=u.RenderingLibrary.create_render_target2d(world,600,625,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        cap.texture_target=rt
        for _ in range(4):cap.capture_scene()
        u.RenderingLibrary.export_render_target(world,rt,str(out),stage+'-'+slug+'-'+mode+'.png')
