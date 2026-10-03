"""Save original motion and an isolated first-person loop map; never start play."""
import json
import math
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
PROJECT = P.parents[1]
DEST = '/Game/Weapons/SwordUppercut20261003'
L = u.EditorAssetLibrary
inputs = json.loads((P/'inputs.json').read_text('utf-8'))
mesh = u.load_asset(inputs['mesh'])
receipt_file = P/'install_receipt.json'
receipt = json.loads(receipt_file.read_text('utf-8')) if receipt_file.exists() else dict(
    revision='OriginalUppercutV1', animations={}, maps={}, runtime_tested=False,
    rendered=False, paid_motion_used=False, editor_opened=False)


def record():
    receipt_file.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')


def props(obj, **values):
    for key, value in values.items():
        obj.set_editor_property(key, value)


def save_animation(variant, preview=False):
    file = P/variant/'editable_keys.json'
    patch = json.loads(file.read_text('utf-8'))
    name = 'A_Sword_UppercutV1_'+variant+('_PreviewLoop' if preview else '')
    target = DEST+'/'+variant+'/'+name
    if target in receipt['animations']:
        return u.load_asset(target)
    if L.does_asset_exist(target):
        asset = u.load_asset(target)
        if L.get_metadata_tag(asset, 'SwordUppercut.AuthorSource') != str(file):
            raise RuntimeError('Preserving existing asset '+target)
    else:
        asset = L.duplicate_asset(patch['source_idle'], target)
        if not asset:
            raise RuntimeError('Cannot create '+target)
    L.set_metadata_tag(asset, 'SwordUppercut.AuthorSource', str(file))
    samples = patch['samples']
    # The motion clip stays 1.45 seconds. Only the independent viewing loop adds
    # a short idle hold, making each completed recovery easy to distinguish.
    if preview:
        samples = samples+[samples[-1]]*round(.65*patch['fps'])
    controller = asset.get_editor_property('controller')
    if controller is None:
        controller = u.AnimDataController()
        controller.set_model(asset.get_editor_property('data_model_interface'))
    controller.open_bracket('Original sword rising cut V1', False)
    try:
        controller.remove_all_bone_tracks(False)
        controller.set_frame_rate(u.FrameRate(numerator=patch['fps'], denominator=1), False)
        controller.set_number_of_frames(u.FrameNumber(value=len(samples)-1), False)
        for name in samples[0]['bones']:
            if not controller.add_bone_curve(name, False):
                raise RuntimeError('Cannot author bone '+name)
            keys = [sample['bones'][name] for sample in samples]
            if not controller.set_bone_track_keys(name, [u.Vector(*k['p']) for k in keys],
                [u.Quat(k['q'][1], k['q'][2], k['q'][3], k['q'][0]) for k in keys],
                [u.Vector(*k['s']) for k in keys], False):
                raise RuntimeError('Cannot save keys '+name)
    finally:
        controller.close_bracket(False)
    asset.set_preview_skeletal_mesh(mesh)
    props(asset, enable_root_motion=False)
    L.set_metadata_tag(asset, 'SwordUppercut.Revision', 'OriginalUppercutV1')
    L.set_metadata_tag(asset, 'SwordUppercut.Provenance', 'Original trajectory; installed arms and idle grip; no paid motion')
    fbx = None
    if not preview:
        fbx = P/variant/(asset.get_name()+'.fbx')
        task = u.AssetExportTask()
        props(task, object=asset, filename=str(fbx), automated=True, prompt=False, replace_identical=True)
        task.options = u.FbxExportOption()
        task.options.ascii = False
        if not u.Exporter.run_asset_export_task(task):
            raise RuntimeError('FBX export failed '+target)
        import_data = asset.get_editor_property('asset_import_data')
        if import_data and hasattr(import_data, 'update_filename_only'):
            import_data.update_filename_only(str(fbx))
    if not L.save_loaded_asset(asset, False):
        raise RuntimeError('Animation save failed '+target)
    receipt['animations'][target] = dict(asset=asset.get_path_name(), seconds=(len(samples)-1)/patch['fps'],
        keys=str(file), fbx=str(fbx) if fbx else None, preview_idle_hold_seconds=.65 if preview else 0.)
    record()
    u.log('UPPERCUT_ANIMATION_SAVED '+target)
    return asset


for variant in ('Standard', 'LongGrip'):
    save_animation(variant)
loop = save_animation('Standard', True)

map_target = DEST+'/Preview/L_SwordUppercut_V1'
if map_target not in receipt['maps']:
    if L.does_asset_exist(map_target):
        raise RuntimeError('Preserving existing map '+map_target)
    world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)

    def spawn(cls, label, pos=(0, 0, 0), rot=None):
        actor = actors.spawn_actor_from_class(cls, u.Vector(*pos), rot or u.Rotator())
        if not actor:
            raise RuntimeError('Cannot create '+label)
        actor.set_actor_label(label)
        actor.set_folder_path('SwordUppercutV1')
        return actor

    # An ordinary engine GameMode prevents the production pawn and combat HUD
    # from taking over this motion-only viewing scene.
    gm_path = DEST+'/Preview/BP_SwordUppercutPreviewMode'
    if L.does_asset_exist(gm_path):
        gm = u.load_asset(gm_path)
        if L.get_metadata_tag(gm, 'SwordUppercut.Revision') != 'OriginalUppercutV1':
            raise RuntimeError('Preserving existing GameMode '+gm_path)
    else:
        factory = u.BlueprintFactory()
        factory.set_editor_property('parent_class', u.GameModeBase)
        gm = u.AssetToolsHelpers.get_asset_tools().create_asset('BP_SwordUppercutPreviewMode',
            DEST+'/Preview', u.Blueprint, factory)
    defaults = u.get_default_object(gm.generated_class())
    props(defaults, default_pawn_class=None, hud_class=None)
    u.BlueprintEditorLibrary.compile_blueprint(gm)
    L.set_metadata_tag(gm, 'SwordUppercut.Revision', 'OriginalUppercutV1')
    if not L.save_loaded_asset(gm, False):
        raise RuntimeError('Preview GameMode save failed')
    world.get_world_settings().set_editor_property('default_game_mode', gm.generated_class())

    camera = spawn(u.CameraActor, 'FirstPersonCamera', (0, 0, 170))
    camera.set_editor_property('auto_activate_for_player', u.AutoReceiveInput.PLAYER0)
    cc = camera.camera_component
    # The game uses a 75-degree vertical FOV; constrain to 16:9 for this subject.
    props(cc, field_of_view=math.degrees(2*math.atan(math.tan(math.radians(75)*.5)*16/9)),
        aspect_ratio=16/9, constrain_aspect_ratio=True)
    pp = cc.get_editor_property('post_process_settings')
    props(pp, override_auto_exposure_method=True, auto_exposure_method=u.AutoExposureMethod.AEM_MANUAL,
        override_auto_exposure_bias=True, auto_exposure_bias=-2.5,
        override_auto_exposure_apply_physical_camera_exposure=True, auto_exposure_apply_physical_camera_exposure=False,
        override_motion_blur_amount=True, motion_blur_amount=0., override_bloom_intensity=True, bloom_intensity=0.)
    cc.set_editor_property('post_process_settings', pp)
    arms = spawn(u.SkeletalMeshActor, 'Uppercut_V7_Arms', (0, 0, 170), u.Rotator(pitch=0, yaw=90, roll=0))
    component = arms.skeletal_mesh_component
    component.set_mobility(u.ComponentMobility.MOVABLE)
    component.set_skeletal_mesh_asset(mesh)
    component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    component.set_cast_shadow(False)
    component.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
    props(component, visibility_based_anim_tick_option=u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    anim = component.get_editor_property('animation_data')
    props(anim, anim_to_play=loop, saved_playing=True, saved_looping=True, saved_play_rate=1., saved_position=0.)
    component.set_editor_property('animation_data', anim)

    modules = json.loads((PROJECT/'Content/ColdSteelData/rune-sword-modules.json').read_text('utf-8-sig'))
    mount = modules['bone_mount']
    blade = None
    for slot in ('blade_1', 'guard', 'grip', 'pommel'):
        spec = modules['slots'][slot]['factory']
        actor = spawn(u.StaticMeshActor, 'Sword_'+slot)
        part = actor.static_mesh_component
        part.set_mobility(u.ComponentMobility.MOVABLE)
        part.set_static_mesh(u.load_asset(spec['mesh']))
        part.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        part.set_cast_shadow(False)
        if slot == 'blade_1':
            actor.attach_to_component(component, modules['drive_bone'], u.AttachmentRule.KEEP_RELATIVE,
                u.AttachmentRule.KEEP_RELATIVE, u.AttachmentRule.KEEP_RELATIVE, False)
            part.set_relative_location(u.Vector(*mount['location_cm']), False, False)
            part.set_relative_rotation(u.Quat(*mount['rotation_xyzw']).rotator(), False, False)
            part.set_relative_scale3d(u.Vector(*mount['scale']))
            blade = part
        else:
            actor.attach_to_component(blade, '', u.AttachmentRule.KEEP_RELATIVE,
                u.AttachmentRule.KEEP_RELATIVE, u.AttachmentRule.KEEP_RELATIVE, False)
            part.set_relative_location(u.Vector(*spec.get('location_cm', [0, 0, 0])), False, False)
            r = spec.get('rotation_deg', [0, 0, 0])
            part.set_relative_rotation(u.Rotator(pitch=r[0], yaw=r[1], roll=r[2]), False, False)
            part.set_relative_scale3d(u.Vector(*spec.get('scale', [1, 1, 1])))

    for label, pos, scale in [('Backdrop', (260, 0, 170), (.2, 12, 8)), ('Floor', (100, 0, -5), (12, 12, .1))]:
        actor = spawn(u.StaticMeshActor, label, pos)
        actor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
        actor.static_mesh_component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        actor.set_actor_scale3d(u.Vector(*scale))
    for label, pos, power, color in [
        ('KeyLight', (0, -100, 300), 350, (1., .95, .88)),
        ('FillLight', (50, 110, 220), 200, (.82, .9, 1.)),
        ('RimLight', (170, 0, 250), 220, (1., 1., 1.))]:
        light = spawn(u.RectLight, label, pos)
        light.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos), u.Vector(40, 0, 155)), False)
        lc = light.get_component_by_class(u.RectLightComponent)
        lc.set_mobility(u.ComponentMobility.MOVABLE)
        lc.set_intensity(power)
        lc.set_light_color(u.LinearColor(*color, 1))
        props(lc, source_width=130., source_height=130., attenuation_radius=600.)
    sky = spawn(u.SkyLight, 'AmbientLight')
    sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sky.light_component.set_intensity(.6)
    props(sky.light_component, source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,
        cubemap=u.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
    if not u.EditorLoadingAndSavingUtils.save_map(world, map_target):
        raise RuntimeError('Preview map save failed')
    receipt['maps'][map_target] = dict(saved=True, game_mode=gm_path, animation=loop.get_path_name(),
        first_person=True, loop_seconds=2.10, production_combat_changed=False)
    record()
    u.log('UPPERCUT_PREVIEW_MAP_SAVED '+map_target)
receipt['stage'] = 'assets_and_preview_map_saved'
record()
