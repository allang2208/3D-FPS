"""Save the reference-led locomotion settings; no gameplay or animation tests."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/QuadrupedTemplates/LocomotionV2'
OUT.mkdir(parents=True, exist_ok=True)
lib = u.EditorAssetLibrary
settings = {'run_blend_start_ratio': .35, 'run_blend_full_ratio': .65, 'full_turn_yaw_rate': 120.0}
report = {'version': 2, 'runtime_tested': False, 'post_change_rendered': False,
          'reference': str(OUT / 'source_reference.json'),
          'source_animation_keys_modified': False, 'sets': []}
for path in ['/Game/Monsters/QuadrupedTemplates/WolfV1/DA_QP_Wolf_AnimationSet',
             '/Game/Monsters/Wolf/DA_Wolf_AnimationSet']:
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError('Missing animation set: ' + path)
    authored = lib.get_metadata_tag(asset, 'Quadruped.LocomotionVersion') != '2'
    if authored:
        for name, value in settings.items():
            asset.set_editor_property(name, value)
        lib.set_metadata_tag(asset, 'Quadruped.LocomotionVersion', '2')
        if not lib.save_loaded_asset(asset, False):
            raise RuntimeError('Could not save ' + path)
    report['sets'].append({'path': path, 'authored_this_run': authored,
                          'settings': {name: asset.get_editor_property(name) for name in settings},
                          'walk_source_speed_cm_s': asset.get_editor_property('walk_speed'),
                          'run_source_speed_cm_s': asset.get_editor_property('run_speed')})
(OUT / 'authoring_manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('QUADRUPED_LOCOMOTION_V2_SAVED')
