"""Reconnaissance: how do the project's existing weapons are structured?

Read-only. The weapon workflow (step 2) requires checking the live weapons before
touching a new source, so this dumps the skeleton, bone names and material slots of the
current viewmodel meshes - that is the target structure a new gun has to match
(magazine / bolt / charging-handle / trigger bones, optics bones, shared arms).

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/SVDDragunov20260922/Receipts')
OUT.mkdir(parents=True, exist_ok=True)

CANDIDATES = [
    '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
    '/Game/Weapons/AKMIntegration/SK_AKM_MannyNative',
    '/Game/Weapons/QBZ191/SK_QBZ191_Manny',
    '/Game/Weapons/M16A2/SK_M16_Manny',
]

report = {'skeletal_meshes': {}, 'static_meshes': {}}


def vec(v):
    return [round(float(v.x), 2), round(float(v.y), 2), round(float(v.z), 2)]


for path in CANDIDATES:
    mesh = u.load_asset(path)
    if mesh is None:
        report['skeletal_meshes'][path] = {'found': False}
        continue
    entry = {'found': True, 'class': mesh.get_class().get_name()}
    try:
        sk = mesh.get_editor_property('skeleton')
        entry['skeleton'] = sk.get_path_name().split('.')[0] if sk else None
        ref = sk.get_editor_property('reference_skeleton') if sk else None
        bones = []
        if ref:
            bones = [str(b) for b in ref.get_editor_property('bone_names')]
        entry['bone_count'] = len(bones)
        entry['bones'] = bones
        keywords = ('mag', 'bolt', 'charge', 'handle', 'trigger', 'safety', 'slide', 'breech',
                    'optic', 'sight', 'muzzle', 'barrel', 'stock', 'grip', 'fire', 'hammer')
        entry['mechanical_bones'] = [b for b in bones if any(k in b.lower() for k in keywords)]
        entry['material_slots'] = [str(s.material_slot_name) for s in mesh.get_editor_property('materials')]
        entry['bounds'] = {'origin': vec(mesh.get_bounds().origin), 'extent': vec(mesh.get_bounds().box_extent)}
    except Exception as exc:  # noqa: BLE001
        entry['error'] = str(exc)
    report['skeletal_meshes'][path] = entry

(OUT / 'weapon-recon.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
for path, entry in report['skeletal_meshes'].items():
    if not entry.get('found'):
        print('MISSING', path)
        continue
    print('MESH', path)
    print('   class=%s skeleton=%s bones=%s' % (entry.get('class'), entry.get('skeleton'), entry.get('bone_count')))
    print('   slots=%s' % (entry.get('material_slots'),))
    print('   mechanical_bones=%s' % (entry.get('mechanical_bones'),))
    if entry.get('bones'):
        print('   all_bones=%s' % (entry['bones'],))
