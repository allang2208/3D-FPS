"""Entry point for the PKM reload audio.

HISTORY, because it is the whole point of this file.  Five rounds tried to take the
BGM out of these cuts and all five were rejected or unverified:

    2026-09-25  tail rebuild on CoverOpen/CoverClose      -- its output is INSTALLED now
    2026-09-28  v1  tail rebuild, 5 contacts              -- rejected, retired to trash
    2026-09-28  v2  tail rebuild, 9 contacts              -- rejected, retired to trash
    2026-09-28  v3  whole-cue look-ahead gate, 9 contacts -- rejected, retired to trash

On 2026-09-28 the user asked to revert to the 09-25 state, so the installed set is now:

    CoverOpen, CoverClose                 09-25 rebuilt tails   (rebuild/*_rebuilt_delivered.wav)
    BeltLift, BoxOut, BoxInsert, BeltSeat raw cuts              (BeltAudio22/S_PKM_*.wav)
    ChargePullMove, ChargeRearStop,
    ChargeFrontStop                       raw cuts              (ChargeAudio35/S_PKM_*.wav)
    ChargePushMove                        untouched (already the raw cut)

This is NOT a clean state and the record says so: the 09-25 recipe used the bed itself
as its timbre reference (rebuild_report.json: `timbre_reference: 9.05-10.0 s`), and the
other six contacts are unprocessed cuts that still carry the BGM.

What that implies, and why another tail/gate/filter round is not the next step: the
reference video is a finished mixed soundtrack.  The BGM and the mechanical sound are
recorded into the same file, overlapping in both time and frequency, with no stems.
Five rounds of masking, donor-splicing, high-passing and gating all hit the same wall.
The remaining honest option is to stop cutting from that video and author the contacts
from clean material.

Usage:  python apply_tail_repair.py          (verify only; it does not import)
Import: run ReloadTailRepair20260928/_import_restore_20260928.py through a background
        commandlet -- never underneath an open editor, which holds the assets in memory.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'tail_repair_manifest.json'
RECIPE = HERE / 'ReloadTailRepair20260928' / '_import_restore_20260928.py'


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    active = manifest.get('active_recipe', {})
    print('state      : %s' % active.get('status', 'unknown'))
    print('record     : %s' % active.get('record', '-'))
    print('recipe     : %s' % active.get('script', '-'))
    print('receipt    : %s' % active.get('receipt', '-'))
    retired = manifest.get('retired_attempts', {})
    if retired:
        print('retired    : %s' % retired.get('location', '-'))
    print()

    repairs = manifest.get('repairs', [])
    print('installed contacts : %d' % len(repairs))
    missing, bad = [], []
    for r in repairs:
        wav = HERE.parent.parent.parent / r['wav']
        if not wav.is_file():
            missing.append(r['wav'])
            mark = 'MISSING'
        else:
            size = wav.stat().st_size
            if size < 1000:
                bad.append(r['wav'])
            mark = 'OK  %7d B' % size
        print('  %-5s %-22s %-16s %s' % (mark.split()[0], r['asset_name'],
                                         r.get('origin', '-'), r['wav']))

    problems = []
    if not RECIPE.is_file():
        problems.append('recipe missing: %s' % RECIPE)
    for name in ('S_PKM_ChargePull', 'S_PKM_ChargeRelease'):
        if any(r['asset_name'] == name for r in repairs):
            problems.append('%s is a dead asset and must not be listed' % name)
    if missing:
        problems.append('missing source WAVs: %s' % ', '.join(missing))
    if bad:
        problems.append('suspiciously small source WAVs: %s' % ', '.join(bad))

    print()
    if problems:
        for p in problems:
            print('PROBLEM: %s' % p)
        return 1
    print('nothing dangling. The installed state matches the manifest.')
    print('To re-import: background commandlet running %s' % RECIPE.name)
    print('Do NOT import while the UE editor is open.')
    return 0


if __name__ == '__main__':
    sys.exit(main())