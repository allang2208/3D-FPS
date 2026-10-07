"""Save three M27 pounce clips; connect after the new native module is loaded."""
from pathlib import Path
import json
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV5')
SOURCE = ROOT / 'Delivery'
DEST = '/Game/Monsters/MantisM27/PounceV5/Animations'
BP = '/Game/Monsters/MantisM27/BP_MantisM27'
REPORT = ROOT / 'ue_pounce_receipt.json'
L = u.EditorAssetLibrary
manifest = json.loads((SOURCE / 'motion_manifest.json').read_text(encoding='utf-8'))

def connect():
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    bp = u.load_asset(BP)
    defaults = u.get_default_object(bp.generated_class())
    for prop, role in [('pounce_windup_clip', 'PounceWindup'), ('pounce_flight_clip', 'PounceFlight'), ('pounce_land_clip', 'PounceLand')]:
        clip = u.load_asset(report['clips'][role])
        if not clip:
            raise RuntimeError('Missing saved pounce clip ' + role)
        defaults.set_editor_property(prop, clip)
    for prop, value in {'pounce_min_range': 320., 'pounce_max_range': 1125., 'pounce_flight_seconds': .65,
                        'pounce_cooldown_seconds': 5., 'pounce_impact_radius': 250., 'pounce_impact_angle': 120.,
                        'pounce_damage_scale': 1., 'shadow_strike_multiplier': 2.}.items():
        defaults.set_editor_property(prop, value)
    L.set_metadata_tag(bp, 'PounceRevision', 'PounceV5: Mutant3-derived physical pounce, grounded landing and one-attack shadow strike')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    if not L.save_loaded_asset(bp, False):
        raise RuntimeError('Could not save the M27 Blueprint')
    report.update(blueprint_connected=True, blueprint=BP, f6_entry='MantisM27')
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('M27_POUNCE_V5_CONNECTED_AND_SAVED', flush=True)

def run():
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before saving M27 assets; preserve the editor')
    if '-m27connectpouncev5' in u.SystemLibrary.get_command_line().lower():
        connect()
        return
    mesh = u.load_asset('/Game/Monsters/MantisM27/BindingV2/SK_MantisM27_BindingV2')
    report = {'revision': 'PounceV5', 'animation_assets_saved': False, 'blueprint_connected': False,
              'clips': {}, 'runtime_tested': False, 'visual_tested': False}
    for role, info in manifest['clips'].items():
        name = Path(info['file']).stem
        opt = u.FbxImportUI()
        opt.automated_import_should_detect_type = False
        opt.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh = False
        opt.import_as_skeletal = opt.import_animations = True
        opt.import_materials = opt.import_textures = False
        opt.skeleton = mesh.skeleton
        data = opt.anim_sequence_import_data
        for prop, value in {'convert_scene': True, 'convert_scene_unit': True, 'import_uniform_scale': 1.,
                            'use_default_sample_rate': False, 'custom_sample_rate': 60,
                            'animation_length': u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,
                            'preserve_local_transform': True}.items():
            data.set_editor_property(prop, value)
        task = u.AssetImportTask()
        task.filename, task.destination_path, task.destination_name = str(SOURCE / info['file']), DEST, name
        task.automated = task.replace_existing = task.replace_existing_settings = True
        task.save = False
        task.options, task.factory = opt, u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        clip = u.load_asset(DEST + '/' + name)
        if not clip or not task.imported_object_paths:
            raise RuntimeError('Could not import ' + name)
        clip.set_preview_skeletal_mesh(mesh)
        clip.set_editor_property('enable_root_motion', False)
        clip.set_editor_property('force_root_lock', False)
        L.set_metadata_tag(clip, 'SourceAnimation', info['source'])
        L.set_metadata_tag(clip, 'M27.Authoring', 'BindingV2; Mutant3 full-body pounce adaptation; capsule-owned flight; no runtime acceptance')
        if not L.save_loaded_asset(clip, False):
            raise RuntimeError('Could not save ' + name)
        report['clips'][role] = clip.get_path_name()
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    report['animation_assets_saved'] = True
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('M27_POUNCE_V5_ANIMATIONS_SAVED', flush=True)

if __name__ == '__main__':
    run()
