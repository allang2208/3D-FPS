"""Isolated rendered repro of the reported no-flame fault, no map/save mutation."""
import json
import unreal as u
from pathlib import Path

root = Path(u.Paths.project_dir()) / 'SourceAssets/FireballFluidBurn20260914'
stage = 'after' if '-flamefixed' in u.SystemLibrary.get_command_line().lower() else 'before'
out = root / ('VisibilityProbe_' + stage)
out.mkdir(exist_ok=True)
world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
effect = actors.spawn_actor_from_class(u.NiagaraActor, u.Vector(0,0,0))
component = effect.get_component_by_class(u.NiagaraComponent)
component.set_asset(u.load_asset('/Game/Skills/Fireball/NS_FireballSlowBurnCore'))
component.set_variable_float('User.Flight', 0)
component.set_variable_float('User.FlightAge', 0)
component.activate(True)
component.advance_simulation(100, 1/60)
capture = actors.spawn_actor_from_class(u.SceneCapture2D, u.Vector(110,0,16), u.Rotator(0,180,0))
camera = capture.get_component_by_class(u.SceneCaptureComponent2D)
camera.set_editor_property('capture_every_frame', False)
camera.set_editor_property('capture_on_movement', False)
camera.set_editor_property('always_persist_rendering_state', True)
camera.set_editor_property('capture_source', u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
camera.set_editor_property('fov_angle', 35)
target = u.RenderingLibrary.create_render_target2d(world, 512, 512, u.TextureRenderTargetFormat.RTF_RGBA8)
camera.set_editor_property('texture_target', target)
records = {}
def set_exposure(bias):
    settings = camera.get_editor_property('post_process_settings')
    settings.set_editor_property('override_auto_exposure_method', True)
    settings.set_editor_property('auto_exposure_method', u.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property('override_auto_exposure_bias', True)
    settings.set_editor_property('auto_exposure_bias', bias)
    settings.set_editor_property('override_auto_exposure_apply_physical_camera_exposure', True)
    settings.set_editor_property('auto_exposure_apply_physical_camera_exposure', False)
    settings.set_editor_property('override_bloom_intensity', True)
    settings.set_editor_property('bloom_intensity', 0.2)
    camera.set_editor_property('post_process_settings', settings)

def capture_at_exposure(name, bias):
    camera.capture_scene()
    u.RenderingLibrary.export_render_target(world,target,str(out),name+'.png')
    records[name] = {'bias':bias,'file':name+'.png'}

frames = 0
def on_tick(delta):
    global frames
    frames += 1
    component.advance_simulation(1, 1/60)
    if frames == 80:
        set_exposure(0)
    if frames == 140:
        set_exposure(-10)
    if 80 <= frames <= 320:
        camera.capture_scene()
    if frames == 120:
        capture_at_exposure('neutral', 0)
    if frames == 180:
        capture_at_exposure('daylight', -10)
    if frames == 200:
        component.set_emitter_enable('FireballFluidHeatHaze', False)
    if frames == 235:
        capture_at_exposure('without_haze', -10)
    if frames == 245:
        component.set_emitter_enable('FireballFluidThinWisp', False)
    if frames == 275:
        capture_at_exposure('fire_only', -10)
    if frames == 285:
        component.set_emitter_enable('FireballFluidShortFlames', False)
    if frames == 315:
        capture_at_exposure('body_only', -10)
    if frames == 330:
        mat = u.load_asset('/Game/Skills/Fireball/FluidBurn20260914/M_FireballFluid_A')
        records['front_material'] = str(u.MaterialEditingLibrary.get_material_property_input_node(mat,u.MaterialProperty.MP_FRONT_MATERIAL))
        records['editor_frames'] = frames
        (out/'capture.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        u.log('FIREBALL_VISIBILITY_PROBE_CAPTURED '+stage)
        u.unregister_slate_post_tick_callback(callback)
        u.SystemLibrary.quit_editor()

callback = u.register_slate_post_tick_callback(on_tick)
