"""Package existing captured frames only; no game launch or asset edits."""
from pathlib import Path
import ast
import json

base = Path(__file__).parent
run = base / 'WireRuns/20261111-100916'
tree = ast.parse((base.parent / 'Wrist34/VisualReview/package.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef))], type_ignores=[]), 'helpers', 'exec'))
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
out = base / 'review'
summary = {}
for peer, selected_case in [('host', 10), ('client', 11)]:
    root = run / peer / 'Visual'
    rows = [json.loads(s) for s in (root / 'owner.jsonl').read_text(encoding='utf-8-sig').splitlines()]
    good = [x for x in rows if (root / 'Owner' / x['image']).exists()]
    cases = []
    for case in sorted({x['case'] for x in rows}):
        part = [x for x in good if x['case'] == case]
        cases.append(dict(case=case, frames=len(part), stages=sorted({x['stage'] for x in part}),
                          max_gap=max(b['time'] - a['time'] for a, b in zip(part, part[1:]))))
    remote = [json.loads(s) for s in (root / 'remote.jsonl').read_text(encoding='utf-8-sig').splitlines()]
    remote = [x for x in remote if x.get('profile', '').startswith('/Game/Weapons/M249/')]
    remote_good = [x for x in remote if (root / 'Remote' / x['image']).exists()]
    groups = {}
    for x in remote_good:
        groups.setdefault(x['weapon_instance'], []).append(x)
    for i, part in enumerate(groups.values()):
        target = root / 'ReviewLive' / f'remote_{i:02d}.jpg'
        if not target.exists():
            sheet([part[round(j*(len(part)-1)/23)] for j in range(24)], root / 'Remote', target, cols=4, width=360)
    selected = [x for x in good if x['case'] == selected_case]
    name = f'{peer}_prism_{"empty" if selected_case % 2 else "normal"}'
    offset = .9 if selected_case % 2 else 0
    for label, lo, hi in [('regrip', 2.25-offset, 2.85-offset), ('belt', 4.28-offset, 5.31-offset)]:
        part = [x for x in selected if x['stage'] == 3 and lo <= x['source_time'] <= hi]
        sheet(part, root / 'Owner', out / f'{name}_{label}_sequential.jpg', cols=4, width=480)
    video(selected, root / 'Owner', out / (name + '.mp4'))
    summary[peer] = dict(owner_frames=len(good), owner_missing=[x for x in rows if x not in good],
        cases=cases, remote_frames=len(remote_good), remote_missing=[x for x in remote if x not in remote_good],
        remote_instances=len(groups), representative_video=str(out / (name + '.mp4')))
    print(peer, 'owner', len(good), 'remote', len(remote_good), 'missing', len(rows)-len(good), len(remote)-len(remote_good), flush=True)
(run / 'visual_capture_inventory.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
