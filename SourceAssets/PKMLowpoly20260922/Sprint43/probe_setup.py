"""Inspect the PKM sprint source and the rifle tactical-sprint references.

Prints, for each blend: armature objects, whether the left-arm bones exist, and
every action with its frame range and sample rate.
"""
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets')
CASES = [
    ('PKM source', ROOT / 'PKMLowpoly20260922' / 'Combat17' / 'PKM_base_Combat_Editable.blend'),
    ('M4 base', ROOT / 'M4TacticalSprint20260915' / 'Base' / 'M4_TacticalSprint_Base_Editable.blend'),
    ('AKM base', ROOT / 'RifleTacticalSprint20260915' / 'AKM' / 'Base' / 'AKM_TacticalSprint_Base_Editable.blend'),
    ('QBZ191 base', ROOT / 'RifleTacticalSprint20260915' / 'QBZ191' / 'Base' / 'QBZ191_TacticalSprint_Base_Editable.blend'),
    ('ASH12', ROOT / 'ASH12TacticalSprint20260919' / 'ASH12_TacticalSprint_Editable.blend'),
]
NEED = ('hand_l', 'lowerarm_l', 'upperarm_l', 'clavicle_l', 'hand_r', 'root')

out = {}
for tag, blend in CASES:
    if not blend.exists():
        print('MISSING %s %s' % (tag, blend))
        continue
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rigs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    print('\n=== %s ===' % tag)
    print('  blend: %s' % blend.name)
    print('  scene fps %s  frame %d..%d' % (scene.render.fps, scene.frame_start, scene.frame_end))
    for r in rigs:
        names = {b.name for b in r.data.bones}
        have = [n for n in NEED if n in names]
        print('  armature %-24s bones %4d  has %s' % (r.name, len(r.data.bones), have))
    acts = []
    for a in bpy.data.actions:
        fr = a.frame_range
        acts.append({'name': a.name, 'start': int(fr[0]), 'end': int(fr[1])})
    acts.sort(key=lambda x: x['name'])
    for a in acts:
        print('    action %-34s frames %4d..%-4d' % (a['name'], a['start'], a['end']))
    out[tag] = {'blend': str(blend), 'rigs': [r.name for r in rigs],
                'fps': scene.render.fps, 'actions': acts}

Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Sprint43').mkdir(
    parents=True, exist_ok=True)
Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Sprint43\setup_report.json').write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
print('\nPROBE_SETUP_DONE')