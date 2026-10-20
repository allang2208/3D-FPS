"""Offline: JC_Pose groups whose clips the R3c / R3d arm rewrites changed (InstalledArm3 + InstalledArm4 receipts or
the plans in Work/ArmPlan3, ArmPlan4). Prints one line per batch: <batch> <comma-joined group keys>."""
import json, glob
from rollout import R

changed = set()
for d in ('Work/ArmPlan3', 'Work/ArmPlan4'):
    for f in glob.glob(str(R / d / '*.json')): changed.add(json.loads(open(f).read())['path'])
for b in ('batch1', 'batch2', 'batch3', 'batch4'):
    plan = json.loads((R / (b + '.json')).read_text()); groups = set()
    for e in plan['meshes']:
        srcs = tuple(e.get('pose_sources') or [e['pose_source']])
        clips = set()
        for s in srcs:
            f = R / 'ClipsSim2' / (s + '.json')
            if f.exists(): clips |= set(json.loads(f.read_text())['clips'])
        if clips & changed: groups.add('|'.join(srcs))
    print(b, ','.join(sorted(groups)))
