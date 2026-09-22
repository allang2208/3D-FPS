"""Independent read-back of the SVD viewmodel (fresh process, disk state only).

Checks what matters for a shared-arms weapon mesh: it must ride the M4 skeleton (not carry
its own), keep the accepted Manny arm materials, and expose the eight SVD parts as their
own slots. Also reports LOD0 size and bounds so the assembly can be compared with Blender.

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
BASE = '/Game/Weapons/SVDDragunov20260922'
M4 = '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'
SK = BASE + '/Viewmodel/SK_SVD_Manny'

report = {'stage': 'verify_viewmodel', 'mesh': SK, 'test_run': False}

mesh = u.load_asset(SK)
m4 = u.load_asset(M4)
if not isinstance(mesh, u.SkeletalMesh):
    raise RuntimeError('viewmodel mesh missing: %s' % SK)

bounds = mesh.get_bounds()
report['size_cm'] = [round(float(bounds.box_extent.x) * 2, 2), round(float(bounds.box_extent.y) * 2, 2),
                     round(float(bounds.box_extent.z) * 2, 2)]
report['origin_cm'] = [round(float(bounds.origin.x), 2), round(float(bounds.origin.y), 2),
                       round(float(bounds.origin.z), 2)]
report['skeleton'] = mesh.skeleton.get_path_name().split('.')[0] if mesh.skeleton else None
report['m4_skeleton'] = m4.skeleton.get_path_name().split('.')[0] if isinstance(m4, u.SkeletalMesh) and m4.skeleton else None
report['rides_shared_skeleton'] = bool(mesh.skeleton and isinstance(m4, u.SkeletalMesh) and mesh.skeleton == m4.skeleton)

sk_editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
try:
    report['lod_count'] = int(sk_editor.get_lod_count(mesh))
    report['lod0_verts'] = int(sk_editor.get_num_verts(mesh, 0))
    report['lod0_sections'] = int(sk_editor.get_num_sections(mesh, 0))
except Exception as exc:  # noqa: BLE001
    report['lod_error'] = str(exc)

slots = []
for index, slot in enumerate(mesh.get_editor_property('materials')):
    material = slot.get_editor_property('material_interface')
    parent = None
    if isinstance(material, u.MaterialInstanceConstant):
        parent_asset = material.get_editor_property('parent')
        parent = parent_asset.get_path_name().split('.')[0] if parent_asset else None
    slots.append({'slot': str(slot.get_editor_property('material_slot_name')),
                  'material': material.get_path_name().split('.')[0] if material else None,
                  'parent': parent})
report['material_slots'] = slots
report['unmapped_slots'] = [s['slot'] for s in slots if not s['material']]

(ROOT / 'Receipts' / 'viewmodel_verify.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('VIEWMODEL_VERIFY ' + json.dumps(report, default=str))
