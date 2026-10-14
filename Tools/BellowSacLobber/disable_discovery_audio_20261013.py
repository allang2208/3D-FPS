"""Remove the user-rejected standing discovery inhales; preserve other sounds."""
from pathlib import Path
import json
import shutil
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUTPUT = ROOT / 'Saved/BellowAudioCleanup20261013'
BP = '/Game/Monsters/BellowSacLobber/BP_BellowSacLobber'
DISABLED_ROLES = {'AlertA', 'AlertB', 'Charge'}

if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('End PIE before saving the M-09 audio change')
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if BP in dirty:
        raise RuntimeError('Preserve unsaved M-09 Blueprint changes')

bp = u.load_asset(BP)
if not bp:
    raise RuntimeError('Missing M-09 Blueprint')
defaults = u.get_default_object(bp.generated_class())
sounds = dict(defaults.get_editor_property('bellow_sounds'))
removed = {str(key): sound.get_path_name() if sound else None
           for key, sound in sounds.items() if str(key) in DISABLED_ROLES}
retained = {key: sound for key, sound in sounds.items() if str(key) not in DISABLED_ROLES}

backup = OUTPUT / 'Before/BP_BellowSacLobber.uasset'
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(ROOT / 'Content/Monsters/BellowSacLobber/BP_BellowSacLobber.uasset', backup)
bp.modify()
defaults.modify()
defaults.set_editor_property('bellow_sounds', retained)
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not u.EditorAssetLibrary.save_loaded_asset(bp, False):
    raise RuntimeError('Could not save M-09 Blueprint without the discovery inhales')

report = dict(blueprint=BP, disabled_roles=sorted(DISABLED_ROLES), removed=removed,
              retained_roles=sorted(str(key) for key in retained), blueprint_saved=True,
              flight_audio_changed=False, listened=False, runtime_tested=False)
(OUTPUT / 'asset-receipt.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('BELLOW_DISCOVERY_AUDIO_REMOVED ' + json.dumps(report, ensure_ascii=False), flush=True)
