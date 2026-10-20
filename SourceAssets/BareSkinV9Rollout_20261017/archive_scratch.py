"""Archive scrapped/superseded rollout files into trash/bare-skin-v9-scratch-20261020/ with a sha256 manifest.

Moves (not copies): failed/rolled-back approaches, one-off probes and experiments, run logs, consumed
install payloads and superseded clip data. Canonical pipeline scripts, final receipts, ground-truth data
(ClipsTrue, ClipsSim2, Snapshots) and surviving backups (Before/) stay in place.
"""
import hashlib, json, shutil, sys
from pathlib import Path

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017')
T = Path('D:/FPS3D/FPSGAME/trash/bare-skin-v9-scratch-20261020')

DIRS = {
    'Clips': 'superseded clip reads from the wrong read path (replaced by ClipsTrue)',
    'ClipsAfter': 'post-write clip reads of the rolled-back pass',
    'ClipsSim': 'offline clip simulation superseded by ClipsSim2',
    'Work': 'consumed install payloads and planning intermediates (all installed)',
    'Receipts_pre_reader_0': 'receipts predating the data-model reader',
    'InstalledGlitch_raw': 'receipts of the rolled-back write pass',
    'InstalledGlitch2_loose': 'receipts of the rolled-back write pass',
    'Installed_pose5': 'receipt of an accidental partial install (reverted)',
}

GROUPS = {
    'rolled-back anim approach': ['anim_fix_raw.py', 'anim_glitch.py', 'anim_glitch2.py', 'anim_glitch3.py',
        'read_clips.py', 'check_bindpops.py', 'check_pops.py', 'verify_twist.py',
        'run_glitch_twist.py', 'run_chain.py', 'left_rawfix.py', 'loop_ue.ps1',
        'run_fix_batch1.py', 'run_fix_batch2.py', 'run_fix_batch3.py', 'run_fix_batch4.py', 'run_fix_all.ps1'],
    'one-off probe': ['probe_api.py', 'probe_api2.py', 'probe_bind.py', 'probe_contact.py', 'probe_corr.py',
        'probe_globalrelax.py', 'probe_left.py', 'probe_match.py', 'probe_normals.py', 'probe_offset.py',
        'probe_pinholes.py', 'probe_render_rest.py', 'probe_transfer.py', 'probe_twist.py', 'probe_uv.py',
        'probe_viper_materials.py', 'blender_view.py'],
    'one-off experiment': ['debug_example.py', 'exp_armfix.py', 'exp_elbow.py', 'exp_hinge_stats.py',
        'exp_reroute.py', 'exp_reroute2.py', 'exp_resolve.py', 'exp_shares.py', 'exp_swivel.py',
        'exp_unspin.py', 'resolve_arm.py'],
    'superseded analysis': ['analyze_elbow_roll.py', 'analyze_roll.py', 'analyze_spin_source.py',
        'rate_probe.py', 'find_rate_misreads.py', 'summarize.py', 'anim_stats.py', 'stats_after_armfix.py'],
    'applied one-off helper': ['update_skill_ref.py', 'update_skill_ref2.py', 'update_skill_ref3.py',
        'update_skill_ref4.py', 'redo_batch1.py'],
    'superseded runner': ['run_reads.py', 'run_reads2.py', 'run_reads3.py', 'run_reads_after.py',
        'run_reads_after3.py', 'run_reads_after_all.py', 'run_read_batch1.py', 'run_read_batch2.py',
        'run_read_batch3.py', 'run_read_batch4.py', 'run_true_batch1.py', 'run_true_batch2.py',
        'run_true_batch3.py', 'run_true_batch4.py', 'run_reread2.py', 'run_armfix_write2.py',
        'run_matprobe_orig.py', 'run_matprobe_v8only.py', 'run_matprobe_viper.py',
        'eval_r3c.ps1', 'run_r3b_chain.ps1', 'run_r3c_chain.ps1', 'run_r3c_post.ps1', 'run_r3d_chain.ps1',
        'run_armfix_chain.ps1', 'run_matfix_chain.ps1', 'wait_and_run.ps1', 'install_loop.ps1',
        'run_rest.ps1', 'run_snapshot_after.ps1'],
    'run log': [],  # filled with *.log
}

FILES = {}
for reason, names in GROUPS.items():
    for n in names:
        FILES[n] = reason
for p in sorted(R.glob('*.log')):
    FILES[p.name] = 'run log'


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def main():
    entries, missing = [], []
    total_bytes = 0
    items = []
    for d, reason in DIRS.items():
        src = R / d
        if not src.is_dir():
            missing.append(d)
            continue
        for f in sorted(src.rglob('*')):
            if f.is_file():
                items.append((f, f.relative_to(R), reason))
    for n, reason in FILES.items():
        f = R / n
        if not f.is_file():
            missing.append(n)
            continue
        items.append((f, Path(n), reason))

    for f, rel, reason in items:
        size = f.stat().st_size
        digest = sha256(f)
        entries.append({'original': 'SourceAssets/BareSkinV9Rollout_20261017/' + rel.as_posix(),
                        'archived': 'trash/bare-skin-v9-scratch-20261020/SourceAssets/BareSkinV9Rollout_20261017/' + rel.as_posix(),
                        'bytes': size, 'sha256': digest, 'reason': reason})
        total_bytes += size

    if '--dry-run' in sys.argv:
        print(json.dumps({'file_count': len(entries), 'bytes': total_bytes, 'missing': missing}, ensure_ascii=False, indent=1))
        return

    manifest = {
        'scope': 'Bare-skin V9 rollout scratch: rolled-back approaches, one-off probes/experiments, run logs, consumed payloads',
        'archived_at': '2026-10-20',
        'decision': 'V9 rollout complete and user-approved. Scrapped passes, investigation one-offs, logs and consumed intermediates archived; canonical pipeline, final receipts, ground-truth data (ClipsTrue/ClipsSim2/Snapshots) and surviving Before/ backups remain.',
        'replacement': 'Current assets are the approved baseline (snapshot at D:/FPS3D/FPSGAME_Backups/BareSkinV9Baseline20261019/). Regenerate payloads via the kept pipeline (build_batch.py / install_batch.py / armfix*.py / pose_examples.py).',
        'file_count': len(entries),
        'bytes': total_bytes,
        'files': entries,
    }
    for f, rel, _ in items:
        dst = T / 'SourceAssets/BareSkinV9Rollout_20261017' / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(dst))
    for d in DIRS:
        src = R / d
        if src.is_dir():
            try:
                src.rmdir()
            except OSError:
                pass
    T.mkdir(parents=True, exist_ok=True)
    (T / 'archive-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(json.dumps({'moved': len(entries), 'bytes': total_bytes, 'missing': missing}, ensure_ascii=False))


if __name__ == '__main__':
    main()
