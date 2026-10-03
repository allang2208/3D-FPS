"""Compare the PKM animation rig with the V7 bare-arms native rig.
Read-only."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
OUT = ROOT / 'Elbow39'
OUT.mkdir(parents=True, exist_ok=True)

SRC = ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend'
V7 = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925'
          r'\BarePalmV7\Editable\PKM_BareArmsV7.blend')

CHAIN = ['clavicle_l', 'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
         'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l',
         'clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r']


def read_rig(path, rig_name):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects[rig_name]
    data = {'scale': list(rig.scale), 'bones': {}}
    for name in CHAIN:
        if name not in rig.data.bones:
            continue
        b = rig.data.bones[name]
        m = b.matrix_local
        data['bones'][name] = {
            'head': list(m.translation),
            'dir': list((b.tail_local - b.head_local).normalized()),
            'parent': b.parent.name if b.parent else None,
        }
    return data


src = read_rig(SRC, 'PKM_Manny_Rig')
v7 = read_rig(V7, 'PKM_NativeReference')

report = {'src_parent': {}, 'v7_parent': {}, 'dir_delta_deg': {}}
for name in CHAIN:
    a = src['bones'].get(name)
    b = v7['bones'].get(name)
    if not a or not b:
        continue
    report['src_parent'][name] = a['parent']
    report['v7_parent'][name] = b['parent']
    va = Vector(a['dir'])
    vb = Vector(b['dir'])
    ang = math.degrees(va.angle(vb))
    report['dir_delta_deg'][name] = round(ang, 4)
report['parents_match'] = report['src_parent'] == report['v7_parent']
(OUT / 'compare_rigs.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('COMPARE_RIGS_DONE', flush=True)