"""Isolated commandlet sword capture using the saved UE meshes and materials."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent
E=u.MaterialEditingLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Background only')
context=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
created=[]
def spawn(cls,loc,rot=u.Rotator()):
    a=actors.spawn_actor_from_class(cls,loc,rot,transient=True)
    if not a:raise RuntimeError('Cannot spawn temporary preview '+str(cls))
    created.append(a);return a
try:
    for rotation,intensity in [(u.Rotator(-40,-55,0),6.),(u.Rotator(-15,150,0),3.)]:
        light=spawn(u.DirectionalLight,u.Vector(),rotation)
        light.light_component.set_mobility(u.ComponentMobility.MOVABLE)
        light.light_component.set_intensity(intensity)
    sky=spawn(u.SkyLight,u.Vector())
    sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('source_type',u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky.light_component.set_cubemap(u.load_asset('/Game/UI/GunsmithWorkbench/T_StudioEnvironment'))
    sky.light_component.set_intensity(1.)
    actor=spawn(u.StaticMeshActor,u.Vector(0,0,0))
    component=actor.static_mesh_component
    component.set_static_mesh(u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/BladeV3/Meshes/SM_XuanChi_Complete_V3'))
    component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    actor.set_actor_hidden_in_game(False)
    capture=spawn(u.SceneCapture2D,u.Vector(0,-300,30),u.Rotator(0,90,0)).capture_component2d
    capture.capture_every_frame=False;capture.capture_on_movement=False
    capture.projection_type=u.CameraProjectionMode.PERSPECTIVE
    capture.fov_angle=14.
    capture.primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST
    capture.show_only_component(component)
    capture.capture_source=u.SceneCaptureSource.SCS_FINAL_TONE_CURVE_HDR
    pp=capture.post_process_settings
    for k,v in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),('override_auto_exposure_bias',True),('auto_exposure_bias',0.)]:pp.set_editor_property(k,v)
    capture.post_process_settings=pp
    for m in component.get_materials():
        if isinstance(m,u.Material):E.recompile_material(m)
    rt=u.RenderingLibrary.create_render_target2d(context,512,1536,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(0,0,0,1))
    capture.texture_target=rt
    u.AutomationLibrary.finish_loading_before_screenshot()
    for _ in range(8):
        capture.capture_scene()
        u.RenderingLibrary.read_render_target_raw_pixel(context,rt,256,700,False)
    u.RenderingLibrary.export_render_target(context,rt,str(P),'lit_sword_before.exr')
    # Base color pass preserves material normals/UVs while excluding light and exposure.
    capture.capture_source=u.SceneCaptureSource.SCS_BASE_COLOR
    capture.capture_scene()
    u.RenderingLibrary.export_render_target(context,rt,str(P),'base_sword_before.exr')
    task=u.AssetExportTask();task.object=component.static_mesh;task.filename=str(P/'Imported_Complete_V3.fbx');task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
    print('EXPORTED_IMPORTED_MESH',u.Exporter.run_asset_export_task(task))
    print('XUANCHI_LIT_AND_BASE_CAPTURED')
finally:
    for a in reversed(created):actors.destroy_actor(a)
