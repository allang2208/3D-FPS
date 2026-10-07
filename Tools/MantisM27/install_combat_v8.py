"""Save M27 V8 combat distances; preserve the existing mesh and motion slots."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/CombatV8')
BP = '/Game/Monsters/MantisM27/BP_MantisM27'
ROOT.mkdir(parents=True, exist_ok=True)
L = u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End PIE before changing M27 combat defaults')
    if BP in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved changes to the M27 Blueprint')
bp = u.load_asset(BP)
if not bp:
    raise RuntimeError('Missing original M27 Blueprint')
defaults = u.get_default_object(bp.generated_class())
values = {'attack_range': 160., 'blade_hit_radius': 35., 'pounce_min_range': 280.,
          'pounce_impact_radius': 330., 'pounce_impact_angle': 160.}
receipt = {'revision': 'CombatV8', 'blueprint': BP, 'saved': False,
           'previous': {p: defaults.get_editor_property(p) for p in values},
           'values': values, 'gameplay_tested': False, 'rendered': False}
for prop, value in values.items():
    defaults.set_editor_property(prop, value)
L.set_metadata_tag(bp, 'CombatRevision',
    'CombatV8: 216cm melee trigger / 186cm stop / 240cm 130deg contact; takeoff prediction capped 750cm; pounce 330cm 160deg')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not L.save_loaded_asset(bp, False):
    raise RuntimeError('Could not save M27 combat defaults')
receipt['saved'] = True
receipt['clips'] = {p: defaults.get_editor_property(p).get_path_name() for p in
    ['left_slash_clip', 'right_slash_clip', 'pounce_windup_clip', 'pounce_flight_clip', 'pounce_land_clip']}
(ROOT / 'asset_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('M27_COMBAT_V8_SAVED', flush=True)
