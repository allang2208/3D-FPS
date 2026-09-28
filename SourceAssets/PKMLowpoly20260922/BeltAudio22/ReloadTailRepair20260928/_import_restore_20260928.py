"""Restore the state the user asked for: 09-25 covers + raw cuts for everything else.

    CoverOpen, CoverClose            -> BeltAudio22/rebuild/*_rebuilt_delivered.wav  (09-25 recipe)
    BeltLift, BoxOut, BoxInsert,     -> BeltAudio22/S_PKM_*.wav                      (raw cut)
    BeltSeat
    ChargePullMove, ChargeRearStop,  -> ChargeAudio35/S_PKM_*.wav                    (raw cut)
    ChargeFrontStop

    ChargePushMove is left alone: it is already the raw cut (imported 09-23) and v3
    never changed it.

This undoes the 09-28 v1/v2/v3 rounds.  Known caveat, recorded rather than hidden:
the 09-25 recipe used the bed itself as its timbre reference (`rebuild_report.json`
says `timbre_reference: 9.05-10.0 s (quiet surround)`, which is a BED window), so its
rebuilt tails carry the bed's colour.  That is the flaw documented in
TAIL_REPAIR_FINDINGS.md.  It is restored because it is the state the user asked for,
not because it is clean.

Carries every SoundWave setting, forces FORCE_INLINE, saves, reads back, and fails
loudly on any mismatch -- the same mechanism the earlier rounds used.
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent                      # .../PKMLowpoly20260922/BeltAudio22
ROOT = PARENT.parent                      # .../PKMLowpoly20260922
OUT = HERE / 'out_restore'
OUT.mkdir(exist_ok=True)

DEST = {
    'ReloadAudio22': '/Game/Weapons/PKMLowpoly20260922/ReloadAudio22',
    'ChargeAudio35': '/Game/Weapons/PKMLowpoly20260922/ChargeAudio35',
}

RESTORE = [
    ('CoverOpen',       'ReloadAudio22', PARENT / 'rebuild/S_PKM_CoverOpen_rebuilt_delivered.wav',  '20260925 rebuild'),
    ('CoverClose',      'ReloadAudio22', PARENT / 'rebuild/S_PKM_CoverClose_rebuilt_delivered.wav', '20260925 rebuild'),
    ('BeltLift',        'ReloadAudio22', PARENT / 'S_PKM_BeltLift.wav',   'raw cut'),
    ('BoxOut',          'ReloadAudio22', PARENT / 'S_PKM_BoxOut.wav',     'raw cut'),
    ('BoxInsert',       'ReloadAudio22', PARENT / 'S_PKM_BoxInsert.wav',  'raw cut'),
    ('BeltSeat',        'ReloadAudio22', PARENT / 'S_PKM_BeltSeat.wav',   'raw cut'),
    ('ChargePullMove',  'ChargeAudio35', ROOT / 'ChargeAudio35/S_PKM_ChargePullMove.wav',  'raw cut'),
    ('ChargeRearStop',  'ChargeAudio35', ROOT / 'ChargeAudio35/S_PKM_ChargeRearStop.wav',  'raw cut'),
    ('ChargeFrontStop', 'ChargeAudio35', ROOT / 'ChargeAudio35/S_PKM_ChargeFrontStop.wav', 'raw cut'),
]

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
for name, folder, wav, origin in RESTORE:
    if not wav.is_file():
        raise RuntimeError('Missing restore source for %s: %s' % (name, wav))
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
    rows.append({'asset': after.get_path_name(), 'restored_from': str(wav), 'origin': origin,
                 'saved': True,
                 'duration': after.get_editor_property('duration'),
                 'sample_rate': after.get_editor_property('sample_rate'),
                 'num_channels': after.get_editor_property('num_channels'),
                 'settings_restored': restored, 'settings_unwritable': failed,
                 'settings_mismatched_after_save': mismatched})
    u.log('PKM_RELOAD_RESTORE_SAVED ' + path)
    print('PKM_RELOAD_RESTORE ' + json.dumps(rows[-1], default=str))

if any(r['settings_mismatched_after_save'] for r in rows):
    raise RuntimeError('A carried SoundWave setting did not survive the save')

(OUT / 'import_receipt.json').write_text(json.dumps(rows, indent=2, default=str), encoding='utf-8')
print('PKM_RELOAD_RESTORE_DONE ' + json.dumps([r['asset'] for r in rows]))