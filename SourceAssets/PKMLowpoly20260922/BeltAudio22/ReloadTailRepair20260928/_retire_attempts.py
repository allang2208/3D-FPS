"""Retire the failed de-BGM attempts to trash/, with a hash manifest.

`trash/` is fully gitignored, per WORKFLOW.md section 8 ("退役文件放 trash/<task>/ 并
记录散列").  Nothing here is deleted -- it is moved and hashed so the record is exact
and the files are still on disk if anyone wants them back.

What goes: the 09-28 v1/v2/v3 authoring, verification, import, rendering and
diagnostic scripts, and every WAV/report/image they produced.  All three rounds were
rejected by the user, and the installed state no longer derives from any of them.

What stays, because the installed assets still derive from it:
  * _author_rebuild.py + rebuild/   -- the 09-25 recipe behind the two installed covers
  * _import_restore_20260928.py     -- the recipe that produced the current state
  * out_restore/                    -- its receipt
  * BeforeImport/, BeforeRestore20260928/ -- rollback points (not attempts)
  * tail_repair_manifest.json, README.md, BGM_FINDINGS.md,
    TAIL_REPAIR_FINDINGS.md, RESTORE_20260928.md -- the records
  * S_PKM_*.wav, ChargeAudio35/S_PKM_*.wav, audio_manifest.json -- the source cuts
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(r'D:/FPS3D/FPSGAME')
ROUND = ROOT / 'SourceAssets/PKMLowpoly20260922/BeltAudio22/ReloadTailRepair20260928'
TRASH = ROOT / 'trash/pkm-reload-debgm-attempts-20260928'
TRASH.mkdir(parents=True, exist_ok=True)

# files and directories, relative to ROUND
RETIRE = [
    '_author_debgm.py', '_author_debgm2.py', '_author_debgm3.py',
    '_verify_debgm.py', '_verify_debgm2.py',
    '_import_debgm_ue.py', '_import_debgm2_ue.py', '_import_debgm3_ue.py',
    '_build_pack2.py', '_build_pack3.py', '_build_covers_ab.py',
    '_viz_v3.py', '_viz_spectro.py', '_viz_comb_check.py',
    '_diag_music_level.py', '_diag_levelmap.py', '_diag_akm_set.py',
    'out', 'out2', 'out3',
    'spectro_v3.png', 'spectro_coarse.png', 'spectro_installed.png',
    'spectro_zoom.png', 'spectra_avg.png',
    'ue-import2.log', 'ue-import3.log', 'ue-restore.log',
]


def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


entries, missing = [], []
for rel in RETIRE:
    src = ROUND / rel
    if not src.exists():
        missing.append(rel)
        continue
    dst = TRASH / rel
    if dst.exists():
        shutil.rmtree(dst) if dst.is_dir() else dst.unlink()
    shutil.move(str(src), str(dst))
    if dst.is_dir():
        files = sorted(p for p in dst.rglob('*') if p.is_file())
        entries.append({'path': rel, 'kind': 'dir', 'files': len(files),
                        'bytes': sum(p.stat().st_size for p in files),
                        'sha256': digest(dst / f) if False else None,
                        'members': {str(p.relative_to(dst)).replace('\\', '/'): digest(p)
                                    for p in files}})
    else:
        entries.append({'path': rel, 'kind': 'file', 'bytes': dst.stat().st_size,
                        'sha256': digest(dst)})

# the pre-restore (v3) snapshot is a rejected state, not a rollback anyone wants
snap = ROUND / 'BeforeRestore20260928'
if snap.is_dir():
    dst = TRASH / 'BeforeRestore20260928'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.move(str(snap), str(dst))
    files = sorted(p for p in dst.rglob('*') if p.is_file())
    entries.append({'path': 'BeforeRestore20260928', 'kind': 'dir', 'files': len(files),
                    'bytes': sum(p.stat().st_size for p in files),
                    'note': 'the v3 state the restore replaced; rejected, kept only for the record',
                    'members': {p.name: digest(p) for p in files}})

(TRASH / 'RETIRED.json').write_text(json.dumps({
    'task': 'pkm-reload-debgm-attempts-20260928',
    'retired_on': '2026-09-28',
    'why': 'All three 09-28 de-BGM rounds (v1, v2, v3) were rejected by the user and '
           'the installed assets no longer derive from any of them.',
    'installed_state': '09-25 covers + raw cuts; see '
                       'ReloadTailRepair20260928/RESTORE_20260928.md',
    'restore_from': 'move the entries back under '
                    'SourceAssets/PKMLowpoly20260922/BeltAudio22/ReloadTailRepair20260928/',
    'entries': entries}, indent=2, ensure_ascii=False), encoding='utf-8')

print('retired %d entries into %s' % (len(entries), TRASH))
for e in entries:
    print('  %-26s %-4s %3s files %9d B' % (e['path'], e['kind'], e.get('files', 1), e['bytes']))
if missing:
    print('not present (skipped):', ', '.join(missing))
print('\nstill in place:')
for p in sorted(ROUND.iterdir()):
    print('  %-34s %s' % (p.name, 'dir' if p.is_dir() else '%d B' % p.stat().st_size))