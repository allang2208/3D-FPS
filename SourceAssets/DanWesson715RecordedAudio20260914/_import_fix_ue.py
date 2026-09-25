"""In-editor (MCP bridge batch): swap the two DW715 speedloader one-shots.

Replaces only:
  S_DW715_Loader_Eject  <- rebuild/S_DW715_Loader_Eject_rebuilt.wav
  S_DW715_Loader_Close  <- rebuild/S_DW715_Loader_Close_rebuilt.wav

Both are the same recording windows with the high-pass raised from 200 Hz to
800 Hz; the six other cues (and S_DW715_Fire_Recorded) are untouched.

Settings are re-applied to the values the assets already use (volume 1.0,
pitch 1.0, looping off, FORCE_INLINE), read from each asset before the swap so
nothing else about the sounds changes.
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\DanWesson715RecordedAudio20260914')
DEST = '/Game/Weapons/DanWesson715/RecordedAudio20260914'
ITEMS = [
    ('S_DW715_Loader_Eject', HERE / 'rebuild/S_DW715_Loader_Eject_rebuilt.wav'),
    ('S_DW715_Loader_Close', HERE / 'rebuild/S_DW715_Loader_Close_rebuilt.wav'),
]

rows = []
for name, wav in ITEMS:
    if not wav.is_file():
        raise RuntimeError('Missing rebuilt WAV: %s' % wav)
    path = '%s/%s' % (DEST, name)
    before = u.load_asset(path)
    if before is None:
        raise RuntimeError('Target asset not found: %s' % path)
    keep = {}
    for prop in ('volume', 'pitch', 'looping', 'loading_behavior'):
        keep[prop] = before.get_editor_property(prop)
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
    for prop, value in keep.items():
        sound.set_editor_property(prop, value)

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
    u.log('DW715_WIND_FIX_SAVED ' + path)

(HERE / 'rebuild/import_receipt.json').write_text(
    json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
print('DW715_WIND_FIX_DONE ' + json.dumps(rows, indent=2))