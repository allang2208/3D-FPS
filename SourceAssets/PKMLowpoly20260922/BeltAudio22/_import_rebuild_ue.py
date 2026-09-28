"""In-editor (MCP bridge batch): swap the two PKM cover one-shots for the rebuilt WAVs.

Runs inside the already-running editor under the bridge's batch mutex, because
the packages are loaded in that process and must not be overwritten by a second
commandlet.

Replaces only:
  S_PKM_CoverOpen   <- rebuild/S_PKM_CoverOpen_rebuilt_delivered.wav
  S_PKM_CoverClose  <- rebuild/S_PKM_CoverClose_rebuilt_delivered.wav

Settings are re-applied to the values the assets already use (volume 1.0,
pitch 1.0, looping off, FORCE_INLINE) so nothing else about the sounds changes.
Other six contacts and S_PKM_Fire are untouched.
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\BeltAudio22')
DEST = '/Game/Weapons/PKMLowpoly20260922/ReloadAudio22'
ITEMS = [
    ('S_PKM_CoverOpen', HERE / 'rebuild/S_PKM_CoverOpen_rebuilt_delivered.wav'),
    ('S_PKM_CoverClose', HERE / 'rebuild/S_PKM_CoverClose_rebuilt_delivered.wav'),
]
SETTINGS = {'volume': 1.0, 'pitch': 1.0, 'looping': False}

rows = []
for name, wav in ITEMS:
    if not wav.is_file():
        raise RuntimeError('Missing rebuilt WAV: %s' % wav)
    path = '%s/%s' % (DEST, name)
    before = u.load_asset(path)
    if before is None:
        raise RuntimeError('Target asset not found: %s' % path)
    duration_before = before.get_editor_property('duration')

    task = u.AssetImportTask()
    task.filename = str(wav)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import failed: %s' % name)

    sound = u.load_asset(task.imported_object_paths[0])
    if sound is None:
        raise RuntimeError('Imported object not loadable: %s' % name)
    if sound.get_path_name().split('.')[0] != path:
        raise RuntimeError('Import landed on the wrong object: %s' % sound.get_path_name())

    sound.set_editor_property('volume', SETTINGS['volume'])
    sound.set_editor_property('pitch', SETTINGS['pitch'])
    sound.set_editor_property('looping', SETTINGS['looping'])
    sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)

    if not u.EditorAssetLibrary.save_asset(path, False):
        raise RuntimeError('Save failed: %s' % path)

    after = u.load_asset(path)
    rows.append({
        'asset': after.get_path_name(),
        'source': str(wav),
        'saved': True,
        'duration_before': duration_before,
        'duration_after': after.get_editor_property('duration'),
        'volume': after.get_editor_property('volume'),
        'pitch': after.get_editor_property('pitch'),
        'looping': after.get_editor_property('looping'),
        'loading_behavior': str(after.get_editor_property('loading_behavior')),
        'sample_rate': after.get_editor_property('sample_rate'),
        'num_channels': after.get_editor_property('num_channels'),
    })
    u.log('PKM_COVER_REBUILT_SAVED ' + path)

(HERE / 'rebuild/import_receipt.json').write_text(
    json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
print('PKM_COVER_REBUILT_DONE ' + json.dumps(rows, indent=2))