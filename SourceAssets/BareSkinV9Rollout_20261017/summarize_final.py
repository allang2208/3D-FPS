"""Final offline numbers per viewmodel group: rest folds, held / worst pinholes (joint + grip correctives from the
mesh payload build) and worst after the JC_Pose examples. Output Work/final_summary.json."""
import json, re
from rollout import R

out = {}
for b in ('batch1', 'batch2', 'batch3', 'batch4'):
    raw = (R / 'Work' / ('rebuild_%s.log' % b)).read_bytes()        # PowerShell *> writes UTF-16
    log = raw.decode('utf-16') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('utf-8', 'replace')
    for line in log.splitlines():
        m = re.match(r'^(.{0,75}?)\s+\d+s (\{[^}]*\}) shapes (\d+) \| worst pinholes (\S*) (\{[^}]*\}) \| idle (.*)$', line)
        if not m: continue
        st = json.loads(m.group(2)); worst = eval(m.group(5)) if m.group(5) != '{}' else {}
        idle = eval(m.group(6)) if m.group(6).strip() != '{}' else {}
        out[m.group(1).strip().split('/')[-1]] = dict(batch=b, rest_before=st['pinholes_before'], rest_after=st['pinholes_after'], shapes=int(m.group(3)),
                                                    worst_clip=m.group(4), worst_plain=worst.get('plain'), worst_jc=worst.get('corrected'),
                                                    held_plain=max([v['plain'] for v in idle.values()] or [0]),
                                                    held_jc=max([v['corrected'] for v in idle.values()] or [0]))
    import os
    rep_f = R / 'Work' / (b + os.environ.get('V9R_POSE_SUB', '_pose')) / 'report.json'
    rep = json.loads(rep_f.read_text()) if rep_f.exists() else {}
    for grp, s in rep.items():
        lead = s['lead'].split('/')[-1]
        if lead in out:
            out[lead].update(pose_examples=len(s['examples']), worst_pose=max(s['worst_after'].values()), held_pose=max(s['held_after'].values()))
(R / 'Work/final_summary.json').write_text(json.dumps(out, indent=1))
for k, v in out.items():
    if 'pose_examples' in v:
        print('%-40s rest %3d->%d  held %3d->%2d->%2d  worst %3s->%3s->%3s (%d ex)' % (k[:40], v['rest_before'], v['rest_after'], v['held_plain'], v['held_jc'], v['held_pose'],
              v['worst_plain'], v['worst_jc'], v['worst_pose'], v['pose_examples']))
