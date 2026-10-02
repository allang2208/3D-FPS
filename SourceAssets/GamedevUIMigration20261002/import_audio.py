"""Import gamedev UI/music migration assets. No PIE or playback."""
from pathlib import Path
import json
import unreal as u

HERE = Path(__file__).resolve().parent
JOBS = [
    # (wav, destination_path, destination_name, looping)
    ('S_Button_Click.wav', '/Game/Audio/GamedevUI20261002', 'S_Button_Click', False),
    ('S_RomanCourtyard.wav', '/Game/Audio/GodSpaceBGM20261002', 'S_RomanCourtyard', True),
]
receipt = []
for wav, dest, name, looping in JOBS:
    task = u.AssetImportTask()
    task.filename = str(HERE / wav)
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import failed: ' + name)
    sound = u.load_asset(task.imported_object_paths[0])
    sound.set_editor_property('looping', looping)
    sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
    if not u.EditorAssetLibrary.save_loaded_asset(sound, False):
        raise RuntimeError('Save failed: ' + name)
    receipt.append(dict(asset=sound.get_path_name(), looping=looping, source=task.filename))
(HERE / 'import-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('GAMEDEV_UI_MIGRATION_IMPORTED ' + json.dumps(receipt))
