"""In-editor (MCP bridge batch): swap the PKM reload one-shots for the de-BGM WAVs.

Runs inside the already-running editor under the bridge's batch mutex, because
those packages are loaded in that process and must not be overwritten by a
second commandlet.

Replaces only the five contacts whose tail measurement found the bed exposed:

  ReloadAudio22/S_PKM_BeltSeat           <- out/S_PKM_BeltSeat_debgm_delivered.wav
  ReloadAudio22/S_PKM_BoxOut             <- out/S_PKM_BoxOut_debgm_delivered.wav
  ReloadAudio22/S_PKM_BeltLift           <- out/S_PKM_BeltLift_debgm_delivered.wav
  ChargeAudio35/S_PKM_ChargeRearStop     <- out/S_PKM_ChargeRearStop_debgm_delivered.wav
  ChargeAudio35/S_PKM_ChargePullMove     <- out/S_PKM_ChargePullMove_debgm_delivered.wav

`S_PKM_CoverOpen` / `S_PKM_CoverClose` already carry their 2026-09-25 tail repair
and are deliberately left byte-identical.  BoxInsert, ChargeFrontStop and
ChargePushMove were measured and skipped (see `out/debgm_report.json`).

Every SoundWave property that is readable before the import is re-applied
afterwards and then re-read, so an import default cannot silently reset the
sound class, submix, volume, pitch, looping or loading behaviour that the
runtime path already depends on.
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\BeltAudio22\ReloadTailRepair20260928')
OUT = HERE / 'out'
DEST = {
    'ReloadAudio22': '/Game/Weapons/PKMLowpoly20260922/ReloadAudio22',
    'ChargeAudio35': '/Game/Weapons/PKMLowpoly20260922/ChargeAudio35',
}

report = json.loads((OUT / 'debgm_report.json').read_text(encoding='utf-8'))
ITEMS = [(r['clip'], r['folder'], OUT / f"S_PKM_{r['clip']}_debgm_delivered.wav")
         for r in report['rows'] if r['action'] == 'rebuilt']

# properties carried over verbatim; unknown/None values are reported, not guessed
CARRY = ['volume', 'pitch', 'looping', 'loading_behavior', 'sound_class_object',
         'sound_submix_object', 'virtualization_mode', 'duration', 'sample_rate',
         'num_channels', 'compression_quality', 'num_channels']


def snapshot(sound):
    snap = {}
    for prop in CARRY:
        try:
            snap[prop] = sound.get_editor_property(prop)
        except Exception as exc:                      # noqa: BLE001 - report, never guess
            snap[prop] = f'<unreadable: {type(exc).__name__}>'
    return snap


def same(a, b):
    try:
        if a is None or b is None:
            return a is b
        return a == b
    except Exception:                                 # noqa: BLE001
        return str(a) == str(b)


rows = []
for name, folder, wav in ITEMS:
    if not wav.is_file():
        raise RuntimeError('Missing de-BGM WAV: %s' % wav)
    dest_path = DEST[folder]
    asset_name = 'S_PKM_%s' % name
    path = '%s/%s' % (dest_path, asset_name)
    before = u.load_asset(path)
    if before is None:
        raise RuntimeError('Target asset not found: %s' % path)
    snap_before = snapshot(before)

    task = u.AssetImportTask()
    task.filename = str(wav)
    task.destination_path = dest_path
    task.destination_name = asset_name
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

    # re-apply everything that was readable and is not already equal
    restored, failed = {}, {}
    for prop, value in snap_before.items():
        if isinstance(value, str) and value.startswith('<unreadable'):
            continue
        if prop in ('duration', 'sample_rate', 'num_channels'):
            continue                                   # owned by the new audio data
        try:
            if not same(sound.get_editor_property(prop), value):
                sound.set_editor_property(prop, value)
            restored[prop] = str(sound.get_editor_property(prop))
        except Exception as exc:                       # noqa: BLE001
            failed[prop] = '%s: %s' % (type(exc).__name__, exc)
    if snap_before.get('loading_behavior') is None:
        sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
        restored['loading_behavior'] = str(sound.get_editor_property('loading_behavior'))

    if not u.EditorAssetLibrary.save_asset(path, False):
        raise RuntimeError('Save failed: %s' % path)

    after = u.load_asset(path)
    snap_after = snapshot(after)
    mismatched = {p: {'before': str(snap_before.get(p)), 'after': str(snap_after.get(p))}
                  for p in ('volume', 'pitch', 'looping', 'loading_behavior',
                            'sound_class_object', 'sound_submix_object')
                  if p in snap_before and not isinstance(snap_before[p], str)
                  and not same(snap_before[p], snap_after.get(p))}
    rows.append({
        'asset': after.get_path_name(),
        'source': str(wav),
        'saved': True,
        'duration_before': snap_before.get('duration'),
        'duration_after': after.get_editor_property('duration'),
        'sample_rate': after.get_editor_property('sample_rate'),
        'num_channels': after.get_editor_property('num_channels'),
        'settings_restored': restored,
        'settings_unwritable': failed,
        'settings_mismatched_after_save': mismatched,
    })
    u.log('PKM_RELOAD_DEBGM_SAVED ' + path)
    print('PKM_RELOAD_DEBGM ' + json.dumps(rows[-1], default=str))

if any(r['settings_mismatched_after_save'] for r in rows):
    raise RuntimeError('A carried SoundWave setting did not survive the save: %s'
                       % json.dumps([r['settings_mismatched_after_save'] for r in rows], default=str))

(OUT / 'import_receipt.json').write_text(json.dumps(rows, indent=2, default=str),
                                         encoding='utf-8')
print('PKM_RELOAD_DEBGM_DONE ' + json.dumps([r['asset'] for r in rows], default=str))