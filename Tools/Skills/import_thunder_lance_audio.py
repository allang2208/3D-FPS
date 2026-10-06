"""Import Thunder Lance audio waves into /Game/Skills/ElectricMagic."""
from pathlib import Path
import json, traceback
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/ThunderLanceRay20261005')
DEST = '/Game/Skills/ElectricMagic'; REV = 'ThunderLanceRayV1'
lib = u.EditorAssetLibrary; tools = u.AssetToolsHelpers.get_asset_tools()
report = {'revision': REV, 'saved': [], 'runtime_tested': False}

def receipt():
    (ROOT / 'Records' / 'audio_import.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf8')
def load(path):
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError('Missing ' + path)
    return asset
def owned(path):
    if not lib.does_asset_exist(path):
        return None
    asset = load(path)
    if lib.get_metadata_tag(asset, 'LanceRayProduction') != REV:
        raise RuntimeError('Preserve unowned asset ' + path)
    return asset
def save(asset):
    lib.set_metadata_tag(asset, 'LanceRayProduction', REV)
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed ' + asset.get_path_name())
    report['saved'].append(asset.get_path_name()); receipt()

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE session active; no asset changed')
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith('/Game/Skills/ElectricMagic') for p in dirty):
    raise RuntimeError('Preserving unsaved electric magic content')
try:
    for name in ('S_ThunderLanceCharge', 'S_ThunderLanceDischarge'):
        path = DEST + '/' + name
        sound = owned(path)
        task = u.AssetImportTask(); task.filename = str(ROOT / 'Audio' / (name + '.wav'))
        task.destination_path = DEST; task.destination_name = name
        task.automated = True; task.save = False; task.replace_existing = sound is not None
        tools.import_asset_tasks([task])
        sound = load(path)
        sound.set_editor_property('looping', False)
        sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
        save(sound)
    report['complete'] = True; receipt()
    u.log('LANCE_AUDIO_IMPORT_SAVED')
except Exception:
    report['complete'] = False; report['error'] = traceback.format_exc(); receipt(); raise
