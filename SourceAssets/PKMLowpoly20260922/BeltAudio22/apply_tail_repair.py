"""Regenerate every PKM reload tail repair from the reference decode.

One entry point for the active recipe, so the repaired WAVs that
`import_audio.py` and `tail_repair_manifest.json` point at can always be rebuilt
from scratch:

  `ReloadTailRepair20260928/_author_debgm2.py` -> `ReloadTailRepair20260928/out2/`

It needs `reference_audio.wav`, which `prepare_reference_audio.py` regenerates
from the local reference video.  Nothing here touches Content or the editor: run
`import_audio.py` (or the round's `_import_debgm2_ue.py`) afterwards to install
the results -- through the MCP bridge if the editor is running, otherwise as an
`UnrealEditor-Cmd -run=pythonscript` commandlet.

The two earlier recipes (`_author_rebuild.py` from 2026-09-25 and
`_author_debgm.py` from the first 2026-09-28 attempt) are **superseded**: both
colour-matched the replacement to the bed's own spectrum and then envelope-matched
it to the bed's level, so the rebuilt tail was a resynthesis of the music.  They
are kept only for the record and are no longer run.

    python apply_tail_repair.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE / 'ReloadTailRepair20260928'

STEPS = [
    ('active recipe: de-BGM v3, whole-cue gate (all nine repaired contacts)',
     ROUND / '_author_debgm3.py'),
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