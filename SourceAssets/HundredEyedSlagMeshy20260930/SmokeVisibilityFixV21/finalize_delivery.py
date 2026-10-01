"""Record saved smoke assets and the regular module build; no runtime test."""
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
ROOT = OUT.parents[2]
assets = json.loads((OUT / 'asset_installation.json').read_text('utf-8-sig'))
build = json.loads((OUT / 'build_installation.json').read_text('utf-8-sig'))
status_path = BASE / 'production_status.json'
status = json.loads(status_path.read_text('utf-8-sig'))
status.update(
    active_revision='SmokeVisibilityFixV21', working_revision='SmokeVisibilityFixV21',
    stage='persistent_body_soot_assets_saved_native_built_not_runtime_tested',
    native_build_required=False, native_class_built=True, build_log=build['log'],
    black_mist_revision='SmokeVisibilityFixV21', black_mist_assets_saved=True,
    black_mist_installation='SmokeVisibilityFixV21/asset_installation.json',
    black_mist_build='SmokeVisibilityFixV21/build_installation.json',
    black_mist_fix_installation='SmokeVisibilityFixV21/installation_complete.json',
    black_mist_runtime_build_pending=False, black_mist_coverage_build_pending=False,
    black_mist_world_space=True, black_mist_body_born=True,
    black_mist_smoke_hold_s=8, black_mist_smoke_fade_s=1.5,
    black_mist_smoke_lifetime_s=9.5, black_mist_rate_per_s=8,
    black_mist_maximum_particles=76, black_mist_coverage_scale=1.5,
    black_mist_spread_scale=1.5, black_mist_base_radius_cm=260,
    black_mist_effective_radius_parameter_cm=390,
    black_mist_dense_core_only=True, black_mist_clear_on_exit=True,
    black_mist_blur=True, black_mist_world_ray_postprocess=False,
    black_mist_view_revision='WorldSmokeV19',
    black_mist_runtime_tested=False, body_smoke_assets_saved=True,
    black_mist_material='/Game/Monsters/HundredEyedSlag/SmokeVisibilityFixV21/M_SlagPersistentBodySmoke',
    black_mist_niagara='/Game/Monsters/HundredEyedSlag/SmokeVisibilityFixV21/NS_SlagBodySmoke',
    revision_saved_asset_count=2, runtime_tested=False, pie_tested=False, tested=False)
status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', 'utf-8')
(OUT / 'installation_complete.json').write_text(json.dumps({
    'revision': 'SmokeVisibilityFixV21', 'assets': assets, 'native_build': build,
    'source_and_saved_assets_completed': True,
    'user_report': 'Smoke invisible after expansion; blindness still applies nearby.',
    'confirmed_configuration_findings': [
        'Deprecated bInterpolatedSpawning field left UE 5.8 InterpolatedSpawnMode at Interpolation.',
        'Template emitter retained a fixed +/-100 cm fallback bounding box.',
        'Shared impact smoke material played a dissipating atlas and aged erosion throughout the 8 s hold.'
    ],
    'diagnosis_limits': 'No live particle capture or game visual validation; commandlet-world activation did not produce simulation frames.',
    'latest_contract': 'Body-born world-space soot, 150% coverage, retain density for 8 s then fade 1.5 s; blind only inside and clear on exit.',
    'retained_attacks': ['SweepPhysical', 'SlamPhysical', 'EyeLaserMagic'],
    'runtime_tested': False, 'interactive_editor_started': False},
    ensure_ascii=False, indent=2) + '\n', 'utf-8')

readme_path = BASE / 'README.md'
readme = readme_path.read_text('utf-8-sig')
paragraph = (
    '当前使用 **SmokeVisibilityFixV21**：烟雾改用百目炉渣专属持续浓烟材质，'
    '纠正 UE 5.8 发射插值字段，CPU 发射器改为动态包围盒；'
    '运行烟迹边界按 Niagara 组件坐标换算。保持 50% 扩散扩大、'
    '8 秒浓烟保留和 1.5 秒渐散、世界空间上浮、每秒 8 粒及雾内目盲。'
    '新材质与 Niagara 已保存，Editor 玩法模块已常规构建；未在游戏中测试。'
    '详见 `Docs/Monsters/hundred-eyed-slag-smoke-visibility-v21-20261002.md`。\n\n')
if '当前使用 **SmokeVisibilityFixV21**' not in readme:
    readme = readme.replace('当前使用 **BodySmokeV20**', '上一轮 **BodySmokeV20**', 1)
    readme = readme.replace('## 当前交付\n\n', '## 当前交付\n\n' + paragraph, 1)
    readme_path.write_text(readme, 'utf-8')
print('SLAG_SMOKE_VISIBILITY_V21_DELIVERY_RECORDED')
