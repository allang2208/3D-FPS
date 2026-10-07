"""Install M27 geometry-oriented scythes and capture scoped UE direction readback."""
from pathlib import Path
import json
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV11')
SOURCE = ROOT / 'Delivery'
DEST = '/Game/Monsters/MantisM27/PounceV11/Animations'
BP = '/Game/Monsters/MantisM27/BP_MantisM27'
L = u.EditorAssetLibrary
manifest = json.loads((SOURCE / 'motion_manifest.json').read_text(encoding='utf-8'))
report = {'revision': 'PounceV11', 'animation_assets_saved': False, 'blueprint_connected': False,
          'clips': {}, 'previous': {}, 'native_code_changed': False, 'runtime_tested': False, 'rendered': False}

def receipt():
    (ROOT / 'ue_pounce_receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

try:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before saving M27 animation assets; preserve the editor')
        if BP in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
            raise RuntimeError('Preserve unsaved changes to the M27 Blueprint')
    mesh = u.load_asset('/Game/Monsters/MantisM27/BindingV2/SK_MantisM27_BindingV2')
    bp = u.load_asset(BP)
    defaults = u.get_default_object(bp.generated_class())
    if defaults.get_editor_property('visual_mesh') != mesh:
        raise RuntimeError('M27 binding changed during authoring; preserve the current Blueprint')
    slots = {'pounce_windup_clip': 'PounceWindup', 'pounce_flight_clip': 'PounceFlight', 'pounce_land_clip': 'PounceLand'}
    for prop, role in slots.items():
        old = defaults.get_editor_property(prop)
        report['previous'][prop] = old.get_path_name() if old else None
    for role, info in manifest['clips'].items():
        name = Path(info['file']).stem
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh = False
        options.import_as_skeletal = options.import_animations = True
        options.import_materials = options.import_textures = False
        options.skeleton = mesh.skeleton
        for prop, value in {'convert_scene': True, 'convert_scene_unit': True, 'import_uniform_scale': 1.,
                            'use_default_sample_rate': False, 'custom_sample_rate': 60,
                            'animation_length': u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,
                            'preserve_local_transform': True}.items():
            options.anim_sequence_import_data.set_editor_property(prop, value)
        task = u.AssetImportTask()
        task.filename, task.destination_path, task.destination_name = str(SOURCE / info['file']), DEST, name
        task.automated = task.replace_existing = task.replace_existing_settings = True
        task.save = False
        task.options, task.factory = options, u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        clip = u.load_asset(DEST + '/' + name)
        if not clip or not task.imported_object_paths:
            raise RuntimeError('Could not import ' + name)
        clip.set_preview_skeletal_mesh(mesh)
        clip.set_editor_property('enable_root_motion', False)
        clip.set_editor_property('force_root_lock', False)
        L.set_metadata_tag(clip, 'SourceAnimation', info['source'])
        L.set_metadata_tag(clip, 'M27.Authoring', 'PounceV11: Geometry-derived blade plane and cutting-edge direction; overhead downstroke; continuous quaternion correction')
        if not L.save_loaded_asset(clip, False):
            raise RuntimeError('Could not save ' + name)
        report['clips'][role] = clip.get_path_name()
        receipt()
    report['animation_assets_saved'] = True
    receipt()
    for prop, role in slots.items():
        defaults.set_editor_property(prop, u.load_asset(report['clips'][role]))
    L.set_metadata_tag(bp, 'PounceRevision', 'PounceV11: V6-based overhead downstroke with blade plane and cutting edge aligned; existing CombatV8 behavior')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    if not L.save_loaded_asset(bp, False):
        raise RuntimeError('Could not save the M27 Blueprint')
    report.update(blueprint_connected=True, blueprint=BP, f6_entry='MantisM27')
    receipt()
    print('M27_POUNCE_V11_CONNECTED_AND_SAVED', flush=True)
except Exception as error:
    report['error'] = str(error)
    receipt()
    raise

# Historical direction diagnosis runs only when explicitly requested.
if "-m27directionreadback" in u.SystemLibrary.get_command_line().lower():
    # Requested direction diagnosis, not a gameplay run. Read RAW imported tracks
    # at the same exact 60-fps frames as the offline source inspection.
    import math
    def vec(v):
        return (v.x, v.y, v.z)
    def sub(a, b):
        return tuple(x-y for x, y in zip(a, b))
    def dot(a, b):
        return sum(x*y for x, y in zip(a, b))
    def norm(a):
        length = math.sqrt(dot(a, a))
        return tuple(x/length for x in a)
    options = u.AnimPoseEvaluationOptions()
    options.evaluation_type = u.AnimDataEvalType.RAW
    options.optional_skeletal_mesh = mesh
    options.set_editor_property('should_retarget', False)
    options.set_editor_property('extract_root_motion', False)
    readback = {'revision': 'PounceV11', 'samples': [], 'runtime_tested': False}
    for role, time in [('PounceWindup', .60), ('PounceFlight', .20), ('PounceFlight', .48),
                       ('PounceFlight', .65), ('PounceLand', .0), ('PounceLand', .10)]:
        clip = u.load_asset(report['clips'][role])
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, round(time*60)/60., options)
        def position(name, reference=False):
            fn = u.AnimPoseExtensions.get_ref_bone_pose if reference else u.AnimPoseExtensions.get_bone_pose
            return vec(fn(pose, name, u.AnimPoseSpaces.WORLD).translation)
        lateral = sub(position('upperarm_l', True), position('upperarm_r', True))
        lateral = norm((lateral[0], lateral[1], 0.))
        forward = sub(position('headfront', True), position('head', True))
        forward = norm((forward[0], forward[1], 0.))
        up = (0., 0., 1.)
        entry = {'role': role, 'time': time, 'sides': {}}
        for side in ['l', 'r']:
            root, mid, tip = [position('blade_' + part + '_' + side) for part in ['root', 'mid', 'tip']]
            chord = norm(sub(tip, root))
            bend = sub(mid, root)
            bend = norm(sub(bend, tuple(x*dot(bend, chord) for x in chord)))
            entry['sides'][side] = {k: [dot(v, lateral), -dot(v, forward), dot(v, up)]
                                     for k, v in [('chord', chord), ('bend', bend)]}
        readback['samples'].append(entry)
    (ROOT / 'ue_direction_readback.json').write_text(json.dumps(readback, indent=2), encoding='utf-8')
    print('M27_V11_DIRECTION_READBACK_SAVED', flush=True)
