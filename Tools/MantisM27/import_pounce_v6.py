"""Import the separated scythe poses and change only M27's three pounce slots."""
from pathlib import Path
import json
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV6')
SOURCE = ROOT / 'Delivery'
DEST = '/Game/Monsters/MantisM27/PounceV6/Animations'
BP = '/Game/Monsters/MantisM27/BP_MantisM27'
L = u.EditorAssetLibrary
manifest = json.loads((SOURCE / 'motion_manifest.json').read_text(encoding='utf-8'))
report = {'revision': 'PounceV6', 'animation_assets_saved': False, 'blueprint_connected': False,
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
        L.set_metadata_tag(clip, 'M27.Authoring', 'PounceV6: rigid scythe separation via whole-arm shoulder rotations; original body and timing')
        if not L.save_loaded_asset(clip, False):
            raise RuntimeError('Could not save ' + name)
        report['clips'][role] = clip.get_path_name()
        receipt()
    report['animation_assets_saved'] = True
    receipt()
    for prop, role in slots.items():
        defaults.set_editor_property(prop, u.load_asset(report['clips'][role]))
    L.set_metadata_tag(bp, 'PounceRevision', 'PounceV6: separated left/right rigid scythes; existing PounceV5 combat behavior')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    if not L.save_loaded_asset(bp, False):
        raise RuntimeError('Could not save the M27 Blueprint')
    report.update(blueprint_connected=True, blueprint=BP, f6_entry='MantisM27')
    receipt()
    print('M27_POUNCE_V6_CONNECTED_AND_SAVED', flush=True)
except Exception as error:
    report['error'] = str(error)
    receipt()
    raise
