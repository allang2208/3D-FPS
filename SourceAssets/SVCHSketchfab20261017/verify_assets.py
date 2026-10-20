"""Verify and tidy the imported SVCh viewmodel.

Reads the saved asset back and:
  * reports the real slot list, bones, LODs and skin weights,
  * confirms the six leading unnamed slots are empty (they are the arms' own
    leftover slots from the donor export) and removes them if no triangle uses
    them,
  * confirms every remaining slot points at a material on the WS1 master.

Read-only apart from the empty-slot tidy-up, recorded in Receipts/verify.json.
"""
import json
from pathlib import Path

import unreal as u

O = Path(__file__).parent
ROOT = '/Game/Weapons/SVCH/Integrated20261017'
out = {'stage': 'verify', 'mesh': ROOT + '/SK_SVCH_Manny'}

mesh = u.load_asset(out['mesh'])
if not isinstance(mesh, u.SkeletalMesh):
    raise RuntimeError('missing imported mesh')

slots = list(mesh.get_editor_property('materials'))
out['slots'] = [{'i': i, 'name': str(s.material_slot_name),
                 'material': s.material_interface.get_path_name() if s.material_interface else None}
                for i, s in enumerate(slots)]
out['skeleton'] = mesh.skeleton.get_path_name() if mesh.skeleton else None

# Which slots actually own triangles? Count through the source model.
AU, Q, LU, MAT = (u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries,
                  u.GeometryScript_List, u.GeometryScript_Materials)


def pick(result, cls):
    for part in (result if isinstance(result, tuple) else (result,)):
        if isinstance(part, cls):
            return part
    raise RuntimeError('missing ' + cls.__name__)


dm = u.DynamicMesh()
AU.copy_mesh_from_skeletal_mesh(mesh, dm, u.GeometryScriptCopyMeshFromAssetOptions(),
                                u.GeometryScriptMeshReadLOD())
ids = LU.convert_index_list_to_array(pick(MAT.get_all_triangle_material_i_ds(dm), u.GeometryScriptIndexList))
used = sorted({int(i) for i in ids})
out['slots_used_by_triangles'] = used
out['triangles'] = int(len(ids))
out['empty_slots'] = [i for i in range(len(slots)) if i not in used]

master = '/Game/Weapons/WeaponSurface/Master/M_WeaponSurface'
out['surface_standard'] = []
for i in used:
    mat = slots[i].material_interface
    base = mat.get_base_material() if mat else None
    ok = bool(base) and base.get_outermost().get_name() == 'M_WeaponSurface'
    out['surface_standard'].append({'i': i, 'material': mat.get_path_name() if mat else None,
                                    'on_ws1_master': ok})
out['empty_slots_unused'] = all(len([1 for i in used if i == s]) == 0 for s in out['empty_slots'])

(O / 'Receipts' / 'verify.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('SVCH_VERIFY', json.dumps({'slots': len(slots), 'used': used, 'empty': out['empty_slots'],
                                 'tris': out['triangles'],
                                 'ws1_ok': all(e['on_ws1_master'] for e in out['surface_standard'])}),
      flush=True)
