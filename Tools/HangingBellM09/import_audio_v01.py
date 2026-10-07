"""Import the seven authored S_M09_* AudioV01 waves. The native Sounds map
already resolves them by role name; nothing else needs binding."""
from pathlib import Path
import json, traceback
import unreal as u
ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/AudioV01')
DEST = '/Game/Monsters/HangingBellM09/Audio/AudioV1'; REV = 'AudioV01'
lib = u.EditorAssetLibrary; tools = u.AssetToolsHelpers.get_asset_tools()
report = {'revision': REV, 'saved': [], 'runtime_tested': False}
def receipt():
    (ROOT / 'Records' / 'import_saved.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf8')
def load(path):
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError('Missing ' + path)
    return asset
def owned(path):
    if not lib.does_asset_exist(path):
        return None
    asset = load(path)
    if lib.get_metadata_tag(asset, 'M09Production') != REV:
        raise RuntimeError('Preserve unowned asset ' + path)
    return asset
def save(asset):
    lib.set_metadata_tag(asset, 'M09Production', REV)
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed ' + asset.get_path_name())
    report['saved'].append(asset.get_path_name()); receipt()

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE session active; no asset changed')
if any(p.get_path_name().startswith('/Game/Monsters/HangingBellM09') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserving unsaved M09 content')
try:
    lib.make_directory(DEST)
    for name, looping in [('S_M09_Idle', True), ('S_M09_Travel', True), ('S_M09_Death', False),
                          ('S_M09_SwingLeft', False), ('S_M09_SwingRight', False),
                          ('S_M09_Claw', False), ('S_M09_Stagger', False),
                          ('S_M09_Alert', False), ('S_M09_RingDown', False)]:
        path = DEST + '/' + name
        sound = owned(path)
        if sound is None:
            task = u.AssetImportTask(); task.filename = str(ROOT / 'Audio' / (name + '.wav'))
            task.destination_path = DEST; task.destination_name = name
            task.automated = True; task.save = False; task.replace_existing = False
            tools.import_asset_tasks([task])
            sound = load(path)
        sound.set_editor_property('looping', looping)
        sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
        save(sound)
    report['complete'] = True; receipt()
    u.log('M09_AUDIO_V01_SAVED')
except Exception:
    report['complete'] = False; report['error'] = traceback.format_exc(); receipt(); raise
