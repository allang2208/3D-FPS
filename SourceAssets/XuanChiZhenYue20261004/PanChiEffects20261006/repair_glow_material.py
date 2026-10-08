"""Scoped offline comparison and repair of the guard's charge glow."""
import json, runpy
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
LIVE=bool(globals().get('PANCHI_LIVE_CAPTURE_ONLY',False))
if LIVE and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Exit PIE before the isolated material capture')
if not LIVE and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Background material diagnosis only')
E=u.MaterialEditingLibrary
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if not LIVE:u.SystemLibrary.execute_console_command(world,'r.PSOPrecache.ProxyCreationWhenPSOReady 0')
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
selection=actors.get_selected_level_actors()
origin=u.Vector(0,0,100000) if LIVE else u.Vector()
created=[]
report={'scope':'guard material only; no player, save or combat state modified','captures':[]}
def spawn(cls,loc,rot=u.Rotator()):
    a=actors.spawn_actor_from_class(cls,loc,rot,transient=True)
    if not a:raise RuntimeError('Temporary material capture actor failed')
    created.append(a);return a
try:
    actor=spawn(u.StaticMeshActor,origin)
    mesh=actor.static_mesh_component
    mesh.set_static_mesh(u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/PanChiGuard20261006/Meshes/SM_XuanChi_Guard_PanChiZhanYue_V1'))
    mesh.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    mesh.set_cast_shadow(False)
    actor.set_actor_hidden_in_game(False);mesh.set_visibility(True)
    if not LIVE:
        light=spawn(u.DirectionalLight,u.Vector(),u.Rotator(pitch=-30,yaw=70,roll=0)).light_component
        light.set_mobility(u.ComponentMobility.MOVABLE);light.set_intensity(4.)
    capture=spawn(u.SceneCapture2D,origin+u.Vector(0,-120,4.5),u.Rotator(pitch=0,yaw=90,roll=0)).capture_component2d
    capture.capture_every_frame=False;capture.capture_on_movement=False
    capture.fov_angle=25.
    capture.primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST
    capture.show_only_component(mesh)
    capture.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    pp=capture.post_process_settings
    for key,value in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),('override_auto_exposure_bias',True),('auto_exposure_bias',0.),('override_bloom_intensity',True),('bloom_intensity',.3)]:pp.set_editor_property(key,value)
    capture.post_process_settings=pp
    rt=u.RenderingLibrary.create_render_target2d(world,1280,640,u.TextureRenderTargetFormat.RTF_RGBA8,u.LinearColor(0,0,0,1))
    capture.texture_target=rt
    report['setup']={'mesh_hidden':str(mesh.get_editor_property('hidden_in_game')),'mesh_visible':str(mesh.get_editor_property('visible')),'capture_location':str(capture.get_world_location()),'capture_rotation':str(capture.get_world_rotation()),'mesh_location':str(mesh.get_world_location())}
    material=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/PanChiEffects20261006/M_PanChiGuardGlow')
    errors=[] if LIVE else list(E.recompile_material(material));report['before_shader_errors']=errors
    if errors:raise RuntimeError(str(errors))
    def frame(label,stacks):
        mid=u.MaterialLibrary.create_dynamic_material_instance(world,material)
        mid.set_scalar_parameter_value('Stacks',float(stacks));mid.set_scalar_parameter_value('Ready',1.)
        mesh.set_overlay_material(mid)
        u.AutomationLibrary.finish_loading_before_screenshot()
        for _ in range(3):
            capture.capture_scene()
            u.RenderingLibrary.read_render_target_raw_pixel(world,rt,640,320,False)
        u.RenderingLibrary.export_render_target(world,rt,str(P),label+'.png')
        report['captures'].append({'label':label,'stacks':stacks,'file':label+'.png'})
    # Preserve the first failing captures instead of overwriting the evidence.
    if not (P/'glow_before_0.png').exists():frame('glow_before_0',0)
    if not (P/'glow_before_3.png').exists():frame('glow_before_3',3)
    if not LIVE:runpy.run_path(str(P/'install_assets.py'),init_globals={'PANCHI_GUARD_ONLY':True})
    report['after_shader_errors']=[] if LIVE else list(E.recompile_material(material))
    if report['after_shader_errors']:raise RuntimeError(str(report['after_shader_errors']))
    frame('glow_after_0',0)
    frame('glow_after_1',1)
    frame('glow_after_3',3)
    report['material_saved']=not LIVE
    print('PANCHI_GLOW_CAPTURE_COMPLETE' if LIVE else 'PANCHI_GLOW_REPAIR_SAVED')
finally:
    for a in reversed(created):actors.destroy_actor(a)
    actors.set_selected_level_actors(selection)
    (P/('glow-live-material-capture-20261007.json' if LIVE else 'glow-repair-20261007.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
