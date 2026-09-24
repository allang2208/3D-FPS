"""Update only the active V14 smoke material from its authoritative HLSL source.

Run through the existing editor bridge, or a background Python commandlet when
the project editor is closed. No texture reimport, particle rebuild or tests.
"""
import json
from pathlib import Path

import unreal

root = Path(unreal.Paths.project_dir())
source = root / 'SourceAssets/MuzzleSmokeMantaflow20260923'
path = '/Game/Weapons/GunplayFX/M_MuzzleSmokeMantaflowV14'
material = unreal.load_asset(path)
if material is None:
    raise RuntimeError('Active Mantaflow smoke material is unavailable: ' + path)
lib = unreal.MaterialEditingLibrary
density = next(n for n in lib.get_material_expressions(material)
               if isinstance(n, unreal.MaterialExpressionCustom)
               and n.get_editor_property('description') == 'Mantaflow V14 smoke flipbook')
density.set_editor_property('code',
                            (source / 'MuzzleSmokeFlipbookV14.hlsl').read_text(encoding='utf-8'))
errors = lib.recompile_material(material)
if errors:
    raise RuntimeError('Smoke material compilation failed: ' + str(errors))
if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
    raise RuntimeError('Could not save muzzle smoke material')
(source / 'visibility-tuning.json').write_text(json.dumps({
    'asset': material.get_path_name(),
    'fresh_density_gain': 1.35,
    'aged_density_gain': 1.15,
    'normalized_age_transition': [0.15, 0.70],
    'status': 'material_updated_compiled_saved',
    'runtime_tested': False,
    'visual_tested': False,
}, indent=2), encoding='utf-8')
unreal.log('MUZZLE_SMOKE_VISIBILITY_SAVED fresh_gain=1.35 aged_gain=1.15')
