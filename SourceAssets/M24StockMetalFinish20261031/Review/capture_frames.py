"""Saved UE asset A/B captures; temporary component overrides only, no asset writes."""
import unreal as u, json
from pathlib import Path
O = Path(__file__).resolve().parent
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('This review runs only in an isolated commandlet')
before = json.loads((O.parent / 'inputs.json').read_text(encoding='utf-8'))
current = json.loads((O / 'inputs.json').read_text(encoding='utf-8'))
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
created = []
report = {'complete': False, 'source': 'actual saved UE meshes and material instances',
          'asset_writes': False, 'gameplay_test': False, 'captures': [], 'textures': {}}
for row in current['materials'].values():
    for role in ('SurfaceNormal','SourceRoughness','SurfaceMask'):
        path=row['parameters']['texture'].get(role)
        if not path or path in report['textures']:continue
        texture=u.load_asset(path)
        report['textures'][path]={'role':role,'srgb':texture.get_editor_property('srgb'),
                                 'compression':str(texture.get_editor_property('compression_settings')),
                                 'flip_green':texture.get_editor_property('flip_green_channel')}

def spawn(cls, location, rotation=u.Rotator()):
    actor = actors.spawn_actor_from_class(cls, location, rotation, transient=True)
    if not actor: raise RuntimeError('Preview spawn failed ' + str(cls))
    created.append(actor)
    return actor

try:
    for rotation, intensity in [(u.Rotator(-35,-45,0),3.), (u.Rotator(-15,135,0),1.)]:
        light = spawn(u.DirectionalLight, u.Vector(), rotation)
        light.light_component.set_mobility(u.ComponentMobility.MOVABLE)
        light.light_component.set_intensity(intensity)
    sky = spawn(u.SkyLight, u.Vector())
    sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('source_type', u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky.light_component.set_cubemap(u.load_asset('/Game/UI/GunsmithWorkbench/T_StudioEnvironment'))
    sky.light_component.set_intensity(.8)
    camera = spawn(u.SceneCapture2D, u.Vector())
    capture = camera.capture_component2d
    capture.capture_every_frame = False
    capture.capture_on_movement = False
    capture.projection_type = u.CameraProjectionMode.PERSPECTIVE
    capture.primitive_render_mode = u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST
    capture.capture_source = u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    capture.set_editor_property('override_custom_near_clipping_plane', True)
    capture.set_editor_property('custom_near_clipping_plane', .001)
    pp = capture.post_process_settings
    for key, value in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),
                       ('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),
                       ('override_auto_exposure_bias',True),('auto_exposure_bias',0.),
                       ('override_bloom_intensity',True),('bloom_intensity',0.),
                       ('override_motion_blur_amount',True),('motion_blur_amount',0.)]:
        pp.set_editor_property(key,value)
    capture.post_process_settings = pp
    target = u.RenderingLibrary.create_render_target2d(world,1600,800,u.TextureRenderTargetFormat.RTF_RGBA8,u.LinearColor(.025,.028,.033,1.))
    capture.texture_target = target
    for group, keys in [('original_stock_body',['standard']), ('skeleton_stock_body',['skeleton_front','skeleton_seat'])]:
        parts = []
        low, high = [float('inf')]*3, [-float('inf')]*3
        for key in keys:
            mesh = u.load_asset(current['assets'][key]['path'])
            actor = spawn(u.StaticMeshActor,u.Vector())
            comp = actor.static_mesh_component
            comp.set_mobility(u.ComponentMobility.MOVABLE)
            comp.set_static_mesh(mesh)
            comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
            comp.set_cast_shadow(False)
            parts.append((key,actor,comp))
            capture.show_only_component(comp)
            bounds = mesh.get_bounds()
            for axis,name in enumerate(('x','y','z')):
                center,extent = getattr(bounds.origin,name),getattr(bounds.box_extent,name)
                low[axis] = min(low[axis],center-extent)
                high[axis] = max(high[axis],center+extent)
        center = u.Vector(*[(a+b)*.5 for a,b in zip(low,high)])
        span = max(high[1]-low[1],2*(high[2]-low[2]))
        position = center + u.Vector(span*1.65,span*.08,span*.35)
        camera.set_actor_location(position,False,True)
        camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(position,center),False)
        capture.fov_angle = 40.
        for mode in ('before','after'):
            for key,actor,comp in parts:
                slots = before['assets'][key]['slots'] if mode=='before' else current['assets'][key]['slots']
                for i,slot in enumerate(slots):comp.set_material(i,u.load_asset(slot['material']))
            u.AutomationLibrary.finish_loading_before_screenshot()
            for _ in range(12):
                capture.capture_scene()
                u.RenderingLibrary.read_render_target_raw_pixel(world,target,800,400,False)
            name = group+'_'+mode+'.png'
            u.RenderingLibrary.export_render_target(world,target,str(O),name)
            report['captures'].append({'file':name,'group':group,'mode':mode,'bounds':[low,high],
                                       'camera':str(position),'fov':40.,'exposure':0.})
            print('M24_FINISH_CAPTURE',name,flush=True)
        capture.clear_show_only_components()
        for key,actor,comp in parts:actors.destroy_actor(actor);created.remove(actor)
    report['complete'] = True
finally:
    for actor in reversed(created):actors.destroy_actor(actor)
    (O/'capture_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
