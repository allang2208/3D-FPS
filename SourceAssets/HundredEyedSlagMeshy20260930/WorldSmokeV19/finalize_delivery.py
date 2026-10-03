"""Record the saved V19 assets and regular native build; does not run tests."""
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
assets = json.loads((OUT / 'asset_installation.json').read_text('utf-8-sig'))
build = json.loads((OUT / 'build_installation.json').read_text('utf-8-sig'))
path = BASE / 'production_status.json'
status = json.loads(path.read_text('utf-8-sig'))
status.update(active_revision='WorldSmokeV19', working_revision='WorldSmokeV19',
              stage='world_smoke_and_in_volume_blur_saved_native_built_not_runtime_tested',
              native_build_required=False, native_class_built=True, build_log=build['log'],
              black_mist_revision='WorldSmokeV19',
              black_mist_installation='WorldSmokeV19/asset_installation.json',
              black_mist_build='WorldSmokeV19/build_installation.json',
              black_mist_fix_installation='WorldSmokeV19/installation_complete.json',
              black_mist_assets_saved=True, black_mist_runtime_build_pending=False,
              black_mist_world_space=True, black_mist_smoke_lifetime_s=3.6,
              black_mist_dense_core_only=True, black_mist_clear_on_exit=True,
              black_mist_blur=True, black_mist_world_ray_postprocess=False,
              black_mist_runtime_tested=False, revision_saved_asset_count=2,
              runtime_tested=False, pie_tested=False, tested=False)
path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', 'utf-8')
(OUT / 'installation_complete.json').write_text(json.dumps({
    'revision': 'WorldSmokeV19', 'assets': assets, 'native_build': build,
    'source_and_saved_assets_completed': True,
    'retained_attacks': ['SweepPhysical', 'SlamPhysical', 'EyeLaserMagic'],
    'slam_stun_s': 2, 'laser_multiplier': .8, 'sweep_multiplier': 1.25,
    'latest_contract': 'blindness only while inside dense smoke, clear immediately on exit',
    'runtime_tested': False, 'interactive_editor_started': False}, ensure_ascii=False, indent=2), 'utf-8')
print('SLAG_WORLD_SMOKE_DELIVERY_RECORDED')
