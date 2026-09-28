"""Regenerate every PKM reload tail repair from the reference decode.

One entry point for both repair rounds, so the repaired WAVs that
`import_audio.py` and `tail_repair_manifest.json` point at can always be rebuilt
from scratch:

  1. `_author_rebuild.py`                     -> rebuild/  (2026-09-25: CoverOpen, CoverClose)
  2. `ReloadTailRepair20260928/_author_debgm.py` -> .../out/ (2026-09-28: the other five)

Both need `reference_audio.wav`, which `prepare_reference_audio.py` regenerates
from the local reference video.  Nothing here touches Content or the editor: run
`import_audio.py` (or the round's `_import_*_ue.py` inside a running editor)
afterwards to install the results.

    python apply_tail_repair.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE / 'ReloadTailRepair20260928'

STEPS = [
    ('2026-09-25 cover tails', HERE / '_author_rebuild.py'),
    ('2026-09-28 remaining contacts', ROUND / '_author_debgm.py'),
]


def main():
    if not (HERE / 'reference_audio.wav').is_file():
        raise SystemExit('reference_audio.wav missing; run prepare_reference_audio.py first')

    for label, script in STEPS:
        if not script.is_file():
            raise SystemExit('missing recipe %s (%s)' % (script, label))
        print('=== %s -> %s' % (label, script.name), flush=True)
        subprocess.run([sys.executable, str(script)], check=True)

    # verify against the manifest before handing off to the importer
    manifest = json.loads((HERE / 'tail_repair_manifest.json').read_text(encoding='utf-8'))
    missing, present = [], []
    for row in manifest['repairs']:
        wav = HERE / row['wav']
        (present if wav.is_file() else missing).append(
            '%s (%s)' % (row['asset_name'], row['wav']))
    print('\nrepaired WAVs present : %d' % len(present))
    for line in present:
        print('  OK   ' + line)
    if missing:
        print('repaired WAVs MISSING : %d' % len(missing))
        for line in missing:
            print('  FAIL ' + line)
        raise SystemExit(1)
    print('\nnext: run import_audio.py (or a round _import_*_ue.py) to install them')


if __name__ == '__main__':
    main()