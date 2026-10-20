"""Measure the accepted SVD's contacts in the shared rig's runtime bind space.

The runtime viewmodel keeps every weapon triangle in this exact space (the idle
pose is applied by the armature, not baked into the vertices), so the SVCh is
seated here too: one translation from its own measured grip panel onto the SVD's.
"""
import gzip
import json
from pathlib import Path

import numpy as np

O = Path(__file__).parent
vm = json.load(gzip.open(O / 'Donor' / 'vm.json.gz', 'rt', encoding='utf-8'))
slots = vm['slots']
tris = np.array(vm['triangles']).reshape(-1, 3)
mat = np.array(vm['material'])
P = np.array(vm['positions']).reshape(-1, 3)


def part(prefixes):
    ids = [i for i, s in enumerate(slots) if any(s.startswith(p) for p in prefixes)]
    m = np.isin(mat, ids)
    if not m.any():
        return None, np.zeros((0, 3))
    v = np.unique(tris[m].ravel())
    return m, P[v]


out = {'space': 'runtime bind space, centimetres (UE component space)', 'parts': {}}
for key, pre in (('Body', ('SM_SVD_Body',)), ('Trigger', ('SM_SVD_Trigger',)),
                 ('Magazine', ('SM_SVD_Magazine',)), ('ChargingHandle', ('SM_SVD_ChargingHandle',))):
    m, pts = part(pre)
    if not len(pts):
        continue
    out['parts'][key] = {'min': [round(float(v), 2) for v in pts.min(0)],
                         'max': [round(float(v), 2) for v in pts.max(0)],
                         'centre': [round(float(v), 2) for v in (pts.min(0) + pts.max(0)) / 2],
                         'n': int(len(pts))}

body = part(('SM_SVD_Body',))[1]
tc = np.array(out['parts']['Trigger']['centre'])
# Pistol grip panel: behind the trigger (muzzle is -Y) and below it.
for dx, dy, dzt, dzb, tag in ((2.2, 11.0, 15.0, 1.0, 'grip'),
                              (3.0, 15.0, 20.0, 0.5, 'grip_wide')):
    band = body[(np.abs(body[:, 0] - tc[0]) < dx) &
                (body[:, 1] > tc[1] + 1.5) & (body[:, 1] < tc[1] + dy) &
                (body[:, 2] > tc[2] - dzt) & (body[:, 2] < tc[2] - dzb)]
    if len(band) >= 8:
        out[tag] = {'min': [round(float(v), 2) for v in band.min(0)],
                    'max': [round(float(v), 2) for v in band.max(0)],
                    'centre': [round(float(v), 2) for v in (band.min(0) + band.max(0)) / 2],
                    'n': int(len(band))}

(O / 'Authoring' / 'svd_bind_space.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('SVD_BIND', json.dumps({k: v for k, v in out.items() if k != 'parts'}), flush=True)
print('SVD_BIND_PARTS', json.dumps(out['parts']), flush=True)
