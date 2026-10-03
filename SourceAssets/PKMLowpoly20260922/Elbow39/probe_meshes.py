"""Probe PKM sources: which meshes carry the left arm skin, and how the
elbow band is weighted. Read-only."""
import json
from pathlib import Path

import bpy

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
OUT = ROOT / 'Elbow39'
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = {
    'idle_src': ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
    'reload_src': ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
    'v7': Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925'
               r'\BarePalmV7\Editable\PKM_BareArmsV7.blend'),
}

ARM_BONES = [
    'clavicle_l', 'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
    'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l',
]

report = {}
for key, path in TARGETS.items():
    entry = {'path': str(path), 'exists': path.exists()}
    if not path.exists():
        report[key] = entry
        continue
    bpy.ops.wm.open_mainfile(filepath=str(path))
    entry['objects'] = []
    rig = None
    for ob in bpy.data.objects:
        row = {'name': ob.name, 'type': ob.type, 'verts': 0, 'groups': 0}
        if ob.type == 'MESH':
            row['verts'] = len(ob.data.vertices)
            row['groups'] = len(ob.vertex_groups)
            row['materials'] = [m.name for m in ob.data.materials]
        entry['objects'].append(row)
    rigs = [ob for ob in bpy.data.objects if ob.type == 'ARMATURE']
    entry['armatures'] = [r.name for r in rigs]
    if rigs:
        rig = rigs[0]
        entry['bones'] = [b.name for b in rig.data.bones]
        rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
        entry['elbow'] = {
            'upperarm_l_head': list(rest['upperarm_l'].translation),
            'elbow_l': list(rest['lowerarm_l'].translation),
            'wrist_l': list(rest['hand_l'].translation),
        }
        if 'upperarm_l' in rest and 'lowerarm_l' in rest:
            import math
            up = (rest['lowerarm_l'].translation - rest['upperarm_l'].translation).length
            lo = (rest['hand_l'].translation - rest['lowerarm_l'].translation).length
            entry['bone_lengths'] = {'upperarm_l': up, 'lowerarm_l': lo}
    # which meshes carry the left arm skin
    entry['arm_meshes'] = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        names = {g.name for g in ob.vertex_groups}
        hits = names.intersection(ARM_BONES)
        if len(hits) >= 4:
            entry['arm_meshes'].append({
                'name': ob.name,
                'verts': len(ob.data.vertices),
                'matched': sorted(hits),
            })
    entry['actions'] = sorted(a.name for a in bpy.data.actions)
    report[key] = entry

(OUT / 'probe_meshes.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('PROBE_MESHES_DONE', flush=True)