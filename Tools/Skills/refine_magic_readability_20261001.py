"""Save current lance flux/circle readability and the held Blizzard shader fix.

Restores the current flux assets and three circle/cloud materials. No play,
render or acceptance tests. Produce the original flux mesh/fields first.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_thunder_lance_column import build_column
from build_thunder_lance_circle import build_circle
from build_blizzard_charged_v3 import gather_cloud_material

targets = {'/Game/Skills/ElectricMagic/ThunderFluxV3/' + name for name in
           ['T_ThunderFluxFields', 'SM_ThunderFluxTube', 'M_ThunderFluxBody', 'M_ThunderFluxFilaments']}
targets.add('/Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceCircle')
targets.update('/Game/Skills/Blizzard/ChargedV3/' + name for name in
               ['M_BlizzardGatherCloud', 'MI_BlizzardGatherCloud'])
dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):
    raise RuntimeError('Preserve unsaved magic readability materials')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('End PIE before saving magic readability materials')

saved = build_column()
circle = build_circle()
saved.append(circle.get_path_name())
storm = u.load_asset('/Game/Skills/Blizzard/ChargedV3/MI_BlizzardStormCloud')
if not storm:
    raise RuntimeError('Existing Blizzard storm material is unavailable')
held = gather_cloud_material(storm)
parent = held.get_editor_property('parent')
saved.extend([parent.get_path_name(), held.get_path_name()])

receipt = {
    'saved_assets': saved,
    'column_diameters_cm': [264, 168, 87, 291],
    'column_emission': [12, 21, 31.5, 42],
    'column_body_blend': 'translucent', 'column_filament_blend': 'additive',
    'column_envelope': 'full hold followed by single linear fade',
    'circle_diameter_cm': 64, 'circle_staff_front_cm': 24,
    'circle_emissive_gain': 14,
    'blizzard_cause': 'DepthFade scene-depth read conflicts with translucent velocity depth write on SM6',
    'blizzard_output_translucent_velocity': bool(parent.get_editor_property('output_translucent_velocity')),
    'blizzard_responsive_aa': bool(parent.get_editor_property('enable_responsive_aa')),
    'blizzard_local_space_and_motion': 'existing Niagara unchanged',
    'gameplay_tested': False, 'rendered': False}
folder = ROOT / 'Saved/MagicReadability20261001'
folder.mkdir(parents=True, exist_ok=True)
(folder / 'asset-authoring.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('MAGIC_READABILITY_SAVED ' + json.dumps(receipt, ensure_ascii=False))
