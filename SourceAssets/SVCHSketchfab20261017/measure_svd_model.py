"""Measure the accepted SVD's model-space contact landmarks (no pose applied).

`SM_SVD_Body` vertices in the blend are stored in the shared rig's WPN_root model
space, so the pistol-grip panel and the trigger are directly comparable with the
SVCh's own author-space measurements. Writes Authoring/svd_model.json.
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

O = Path(__file__).parent
SRC = Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/SVD_Complete_Editable.blend')

bpy.ops.wm.open_mainfile(filepath=str(SRC))


def pts(name):
    ob = bpy.data.objects[name]
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices]


body = pts('SM_SVD_Body')
trig = pts('SM_SVD_Trigger')
mag = pts('SM_SVD_Magazine')
ch = pts('SM_SVD_ChargingHandle')


def box(points):
    mn = Vector((min(p[i] for p in points) for i in range(3)))
    mx = Vector((max(p[i] for p in points) for i in range(3)))
    return {'min': [round(v, 5) for v in mn], 'max': [round(v, 5) for v in mx],
            'centre': [round(v, 5) for v in ((mn + mx) / 2)], 'n': len(points)}


out = {'source': str(SRC),
       'Body': box(body), 'Trigger': box(trig),
       'Magazine': box(mag), 'ChargingHandle': box(ch)}

tc = Vector(out['Trigger']['centre'])
# Pistol grip: behind the trigger (+Y is rearward: muzzle is at -Y) and below it,
# close to the weapon's centreline.
for dy, dz, dx, tag in ((0.115, 0.150, 0.030, 'grip'),
                        (0.115, 0.190, 0.035, 'grip_wide')):
    band = [p for p in body
            if abs(p.x - tc.x) < dx
            and tc.y + 0.012 < p.y < tc.y + dy
            and tc.z - dz < p.z < tc.z - 0.008]
    if band:
        out[tag] = box(band)

# Grip centreline: the densest lateral cluster in the grip band.
if 'grip' in out:
    g = Vector(out['grip']['centre'])
    out['grip_centre'] = [round(v, 5) for v in g]

(O / 'Authoring').mkdir(exist_ok=True)
(O / 'Authoring' / 'svd_model.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('SVD_MODEL', json.dumps(out, ensure_ascii=False), flush=True)
