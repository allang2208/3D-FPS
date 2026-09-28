"""In-editor (MCP bridge batch): install the second-generation de-BGM rebuilds.

Runs inside the already-running editor under the bridge's batch mutex.

Replaces nine contacts from `out2/` (ChargePushMove is skipped: its trailing
region is digital silence, so it needs nothing and is left byte-identical).
Every readable SoundWave property is re-applied after the import and read back,
so an import default cannot silently reset the sound class, submix, volume,
pitch, looping or loading behaviour the runtime path depends on.
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\BeltAudio22\ReloadTailRepair20260928')
OUT = HERE / 'out2'
DEST = {
    'ReloadAudio22': '/Game/Weapons/PKMLowpoly20260922/ReloadAudio22',
    'ChargeAudio35': '/Game/Weapons/PKMLowpoly20260922/ChargeAudio35',
}
CHARGE = ('ChargePullMove', 'ChargeRearStop', 'ChargePushMove', 'ChargeFrontStop')

report = json.loads((OUT / 'debgm2_report.json').read_text(encoding='utf-8'))
ITEMS = [(r['clip'], 'ChargeAudio35' if r['clip'] in CHARGE else 'ReloadAudio22',
          OUT / f"S_PKM_{r['clip']}_debgm2.wav")
         for r in report['rows'] if r['action'] == 'rebuilt']

CARRY = ['volume', 'pitch', 'looping', 'loading_behavior', 'sound_class_object',
         'sound_submix_object', 'virtualization_mode', 'compression_quality']


def snapshot(sound):
    snap = {}
    for prop in CARRY:
        try:
            snap[prop] = sound.get_editor_property(prop)
        except Exception as exc:                      # noqa: BLE001
            snap[prop] = '<unreadable: %s>' % type(exc).__name__
    return snap


def same(a, b):
    try:
        return a is b if (a is None or b is None) else a == b
    except Exception:                                 # noqa: BLE001
        return str(a) == str(b)


rows = []
for name, folder, wav in ITEMS:
    if not wav.is_file():
        raise RuntimeError('Missing de-BGM WAV: %s' % wav)
    asset_name = 'S_PKM_%s' % name
    path = '%s/%s' % (DEST[folder], asset_name)
    before = u.load_asset(path)
    if before is None:
        raise RuntimeError('Target asset not found: %s' % path)
    snap_before = snapshot(before)

    task = u.AssetImportTask()
    task.filename = str(wav)
    task.destination_path = DEST[folder]
    task.destination_name = asset_name
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import failed: %s' % asset_name)

    sound = u.load_asset(task.imported_object_paths[0])
    if sound is None or sound.get_path_name().split('.')[0] != path:
        raise RuntimeError('Import landed on the wrong object: %s' % asset_name)

    restored, failed = {}, {}
    for prop, value in snap_before.items():
        if isinstance(value, str) and value.startswith('<unreadable'):
            continue
        try:
            if not same(sound.get_editor_property(prop), value):
                sound.set_editor_property(prop, value)
            restored[prop] = str(sound.get_editor_property(prop))
        except Exception as exc:                       # noqa: BLE001
            failed[prop] = '%s: %s' % (type(exc).__name__, exc)
    if snap_before.get('loading_behavior') is None:
        sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)

    if not u.EditorAssetLibrary.save_asset(path, False):
        raise RuntimeError('Save failed: %s' % path)

    after = u.load_asset(path)
    snap_after = snapshot(after)
    mismatched = {p: {'before': str(snap_before.get(p)), 'after': str(snap_after.get(p))}
                  for p in ('volume', 'pitch', 'looping', 'loading_behavior',
                            'sound_class_object', 'sound_submix_object')
                  if p in snap_before and not isinstance(snap_before[p], str)
                  and not same(snap_before[p], snap_after.get(p))}
    rows.append({'asset': after.get_path_name(), 'source': str(wav), 'saved': True,
                 'duration': after.get_editor_property('duration'),
                 'sample_rate': after.get_editor_property('sample_rate'),
                 'num_channels': after.get_editor_property('num_channels'),
                 'settings_restored': restored, 'settings_unwritable': failed,
                 'settings_mismatched_after_save': mismatched})
    u.log('PKM_RELOAD_DEBGM2_SAVED ' + path)
    print('PKM_RELOAD_DEBGM2 ' + json.dumps(rows[-1], default=str))

if any(r['settings_mismatched_after_save'] for r in rows):
    raise RuntimeError('A carried SoundWave setting did not survive the save')

(OUT / 'import_receipt.json').write_text(json.dumps(rows, indent=2, default=str), encoding='utf-8')
print('PKM_RELOAD_DEBGM2_DONE ' + json.dumps([r['asset'] for r in rows]))