"""Express the SVCh's measured landmarks in WPN_root local space.

`UpdateADSPose` does `Root.TransformPosition(SVCHWeaponAssets::RearSight)` where
Root is the accumulated WPN_root bone transform. That call treats the constant as
a point in the bone's own space, exactly like AKMSoviet::Rear/Front. The values in
the header were written in component space instead, so the sight points collapsed
toward the root origin and the ADS camera landed in the wrong place.

rest.json stores the rig's bone matrices in metres, which is the same unit the
header uses (the imported UE root carries the x100 metre-to-centimetre scale), so
the conversion is one inverse bind matrix per point.

Prints the corrected constants.
"""
import json
from pathlib import Path

O = Path(__file__).parent
rest = json.loads((O / 'Skeleton' / 'rest.json').read_text(encoding='utf-8'))
bones = rest['bones'] if isinstance(rest, dict) and 'bones' in rest else rest

root = None
for b in bones:
    if str(b.get('name')) == 'WPN_root':
        root = b
        break
if root is None:
    raise SystemExit('WPN_root not found in rest.json')

M = [list(map(float, row)) for row in root['matrix']]
# 4x4 invert (rows, row-major, translation in the last column).
def inv4(m):
    a = [row[:] + [1.0 if i == j else 0.0 for j in range(4)] for i, row in enumerate(m)]
    for i in range(4):
        p = max(range(i, 4), key=lambda r: abs(a[r][i]))
        a[i], a[p] = a[p], a[i]
        d = a[i][i]
        if abs(d) < 1e-12:
            raise SystemExit('singular bind matrix')
        a[i] = [v / d for v in a[i]]
        for r in range(4):
            if r != i and abs(a[r][i]) > 1e-12:
                f = a[r][i]
                a[r] = [v - f * w for v, w in zip(a[r], a[i])]
    return [row[4:] for row in a]

Mi = inv4(M)


def to_local(p):
    return [sum(Mi[i][j] * (list(p) + [1.0])[j] for j in range(4)) for i in range(3)]


pts = {
    'RearSight': (0.0607, -0.1637, 0.0765),
    'FrontSight': (0.0607, -0.7014, 0.0767),
    'MuzzlePoint': (0.0607, -0.9247, -0.0094),
    'EjectPort': (0.0708, -0.3302, -0.0039),
}
print('WPN_root bind matrix (metres):')
for row in M:
    print('  ', [round(v, 5) for v in row])
print()
for name, p in pts.items():
    q = to_local(p)
    print('%-12s component=%-28s local=%s' %
          (name, p, '(' + ', '.join('%.6ff' % v for v in q) + ')'))
