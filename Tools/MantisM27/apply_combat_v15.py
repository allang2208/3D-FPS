"""Save the moving-target melee range without replacing M27 animation assets."""
from pathlib import Path
import json
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/CombatV15')
OUT.mkdir(parents=True, exist_ok=True)
BP = '/Game/Monsters/MantisM27/BP_MantisM27'
report = {'revision': 'CombatV15', 'blueprint': BP, 'saved': False,
          'gameplay_tested': False, 'rendered': False}

try:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before saving the M27 combat defaults')
        if BP in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
            raise RuntimeError('Preserve unsaved changes to the M27 Blueprint')
    bp = u.load_asset(BP)
    defaults = u.get_default_object(bp.generated_class())
    report['previous_attack_range'] = defaults.get_editor_property('attack_range')
    defaults.set_editor_property('attack_range', 190.0)
    report['attack_range_base_cm'] = 190.0
    report['effective_weapon_reach_cm'] = 285.0
    report['start_range_formula'] = '285 * 0.95 + victim capsule radius'
    report['contact_range_formula'] = '285 + victim capsule radius'
    report['preserved_clips'] = {}
    for prop in ['left_slash_clip', 'right_slash_clip', 'pounce_windup_clip', 'pounce_flight_clip', 'pounce_land_clip']:
        clip = defaults.get_editor_property(prop)
        report['preserved_clips'][prop] = clip.get_path_name() if clip else None
    u.EditorAssetLibrary.set_metadata_tag(bp, 'M27.CombatRevision',
        'CombatV15: live moving goal, 0.12s pursuit replan, attack handoff before stop, '
        'cooldown closing distance, 190cm base melee reach; preserve animation timing')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    if not u.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError('Could not save the M27 Blueprint')
    report['saved'] = True
    print('M27_COMBAT_V15_SAVED', flush=True)
except Exception as error:
    report['error'] = str(error)
    raise
finally:
    (OUT / 'asset_receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
