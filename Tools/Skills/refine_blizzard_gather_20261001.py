"""Save held Blizzard cloud motion/temporal settings and the shared red preview.

Only edits the held-cloud system, its own material copies and the aim material.
No game, simulation advancement, rendering or acceptance tests.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, ref, emitters, save, CREATED
from build_fireball_flight import expression
from build_blizzard_charged_v3 import (
    DEST, CLOUD_LAYERS, GATHER_CLOUD_COUNTS, gather_cloud_material,
    cloud_lifecycle, cloud_layer, preview_color, finish)

EAL = u.EditorAssetLibrary
targets = [DEST + '/' + name for name in [
    'NS_BlizzardGatherCloud', 'M_BlizzardGatherCloud',
    'MI_BlizzardGatherCloud', 'M_BlizzardAimPreview']]
dirty = {str(package.get_path_name()) for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(path in dirty for path in targets):
    raise RuntimeError('Preserve unsaved Blizzard gather/preview packages')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('End PIE before saving Blizzard gather/preview assets')

source = u.load_asset(DEST + '/MI_BlizzardStormCloud')
system = u.load_asset(DEST + '/NS_BlizzardGatherCloud')
preview = u.load_asset(DEST + '/M_BlizzardAimPreview')
if not source or not system or not preview:
    raise RuntimeError('Restore existing Blizzard ChargedV3 assets')
color = preview_color()
gather = gather_cloud_material(source)
for name in emitters(system):
    API.call_method('RemoveEmitter', (ref(system, name),))
lifecycle = cloud_lifecycle()
for count, (name, level, tint) in zip(GATHER_CLOUD_COUNTS, CLOUD_LAYERS):
    if count:
        cloud_layer(system, gather, name, count, level, tint, lifecycle, True)
expression(system, '', 'SystemUpdateScript', 'SystemState', 'Loop Duration',
           'max(.6,User.StormDuration+.6)')
system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-90, -90, -90), max=u.Vector(90, 90, 90)))
save(system)

for node in LIB.get_material_expressions(preview):
    if isinstance(node, u.MaterialExpressionVectorParameter) and str(node.get_editor_property('parameter_name')) == 'Tint':
        node.set_editor_property('default_value', color)
        break
else:
    raise RuntimeError('Blizzard preview Tint parameter is unavailable')
finish(preview)

receipt = {
    'saved_assets': list(CREATED), 'local_space': True, 'spawn_interpolation': 'NoInterpolation',
    'motion_vectors': 'Precise', 'output_translucent_velocity': False, 'responsive_aa': True,
    'gather_particle_count': sum(GATHER_CLOUD_COUNTS),
    'motion': 'independent rolling, vertical drift, breathing, density and texture animation',
    'preview_color_source': 'FPSMagicPreview::LineColor',
    'preview_linear_color': [color.r, color.g, color.b, color.a],
    'native_source_changed': False, 'gameplay_tested': False, 'rendered': False}
folder = ROOT / 'Saved/BlizzardGatherNatural20261001'
folder.mkdir(parents=True, exist_ok=True)
(folder / 'asset-authoring.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('BLIZZARD_GATHER_NATURAL_SAVED ' + json.dumps(receipt, ensure_ascii=False))
