"""Analyse the dumped runtime SVD viewmodel: arm sections, placement and weights."""
import json
from pathlib import Path
import numpy as np

JOB = Path(r'D:\FPS3D\FPSGAME\SourceAssets\SVDReloadLeftArm20260925')
RT = JOB / 'runtime'
BONES = json.loads((JOB.parent / 'ModularOutfit20260925/BareArmsFamilyV6/Sources/SVD.json')
                   .read_text(encoding='utf-8-sig'))['bones']


def load(name):
    return json.loads((RT / f'{name}.json').read_text())


def arm_report(name, arm_slots):
    d = load(name)
    pos = np.asarray(d['positions'], dtype=float)
    w = d['weights']
    slots = d['slots']
    span = pos.max(0) - pos.min(0)
    print(f'==== {name} verts {len(pos)} slots {len(slots)}')
    print(f'   all-vertex span {np.round(span,2)} min {np.round(pos.min(0),2)}')
    left = np.zeros(len(pos), dtype=bool)
    right = np.zeros(len(pos), dtype=bool)
    unresolved = 0
    spread = np.zeros(len(pos))
    for i, pairs in enumerate(w):
        for bname, weight in pairs:
            b = BONES.get(bname)
            if not b:
                unresolved += 1
                continue
            spread[i] += weight * float(np.linalg.norm(pos[i] - np.asarray(b['position'], dtype=float)))
            if bname.endswith('_l'):
                left[i] = True
            elif bname.endswith('_r'):
                right[i] = True
    print(f'   unresolved bone names in weights: {unresolved}')
    for label, mask in (('left', left), ('right', right)):
        if mask.sum() == 0:
            print(f'   {label}: none')
            continue
        sub = pos[mask]
        print(f'   {label} verts {int(mask.sum())} span {np.round(sub.max(0)-sub.min(0),2)} '
              f'min {np.round(sub.min(0),2)} max {np.round(sub.max(0),2)}')
        sp = spread[mask]
        print(f'   {label} weight spread cm mean {sp.mean():.2f} p99 {np.percentile(sp,99):.2f} '
              f'max {sp.max():.2f} over 15cm {int((sp>15).sum())} over 25cm {int((sp>25).sum())}')
    return d


svd = arm_report('svd_modular_stock', [0, 1])
gloved = arm_report('svd_gloved_source', [0, 1])
m4 = arm_report('m4_viewmodel', [6, 7])
