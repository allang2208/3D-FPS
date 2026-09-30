"""Apply Bake/magwell_repair.json to SK_A762_Manny LOD0. Run through ../run_ue.ps1.

Plan: plan_magwell_repair.py (lift collar teeth, delete Meshy debris, add the rebuilt
magazine catch). Everything else is kept: arm triangles and their UV0-3, bone weights,
material slots, vertex order of untouched vertices. The asset is backed up to
BeforeRepair/ first and only saved when the read-back checks pass.
No PIE, capture or gameplay check is performed.
"""
import json
import shutil
import unreal as u
from pathlib import Path

HERE = Path(__file__).parent
MESH = '/Game/Weapons/A762/Integrated20260920/SK_A762_Manny'
VERSION = 'WS-MagwellRepair-20260930'
AU, Q, LU = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries, u.GeometryScript_List
ED, UVS, NRM, MATS, BW = (u.GeometryScript_MeshEdits, u.GeometryScript_UVs, u.GeometryScript_Normals,
                          u.GeometryScript_Materials, u.GeometryScript_BoneWeights)
ARM_KEYS = ('Manny', 'BarePalm', 'BareNative', 'BareFamily')
plan = json.loads((HERE / 'Bake' / 'magwell_repair.json').read_text(encoding='utf-8'))
RECEIPT = HERE / 'repair_receipt.json'


def pick(result, cls):
    if isinstance(result, tuple):
        for item in result:
            if isinstance(item, cls):
                return item
        raise RuntimeError('No %s in result' % cls.__name__)
    return result


def ids(fn, *a):
    return LU.convert_index_list_to_array(pick(fn(*a), u.GeometryScriptIndexList))


def weights_of(mesh_dm, v):
    r = BW.get_vertex_bone_weights(mesh_dm, v)
    return next((x for x in r if isinstance(x, (list, u.Array))), []) if isinstance(r, tuple) else []


def valid(result):
    return all(x for x in result if isinstance(x, bool)) if isinstance(result, tuple) else True


commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not commandlet:
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('A762 repair: PIE is running; nothing changed')
    if MESH in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('A762 repair: mesh has unsaved edits; nothing changed')
if RECEIPT.exists() and json.loads(RECEIPT.read_text(encoding='utf-8')).get('saved'):
    raise RuntimeError('A762 repair already applied (repair_receipt.json); restore BeforeRepair/ to re-run')

content = Path(u.Paths.project_dir()).resolve() / 'Content'
rel = MESH.removeprefix('/Game/') + '.uasset'
backup = HERE / 'BeforeRepair' / rel
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(content / rel, backup)

mesh = u.load_asset(MESH)
lod = u.GeometryScriptMeshReadLOD()
lod.set_editor_property('lod_type', u.GeometryScriptLODType.SOURCE_MODEL)
dm = u.DynamicMesh()
AU.copy_mesh_from_skeletal_mesh(mesh, dm, u.GeometryScriptCopyMeshFromAssetOptions(), lod)
if Q.get_has_triangle_id_gaps(dm) or Q.get_has_vertex_id_gaps(dm):
    raise RuntimeError('id gaps: indices would not match the plan')
positions = LU.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm, True), u.GeometryScriptVectorList))
tri_list = LU.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm, True), u.GeometryScriptTriangleList))
checksum = sum(abs(p.x) + abs(p.y) + abs(p.z) for p in positions)
if len(tri_list) != plan['triangle_count'] or len(positions) != plan['vertex_count']:
    raise RuntimeError('mesh size changed since the plan: %d/%d' % (len(tri_list), len(positions)))
if abs(checksum - plan['position_checksum']) > 1e-4 * plan['position_checksum']:
    raise RuntimeError('mesh geometry changed since the plan')
cent = 0.0
for t in plan['delete_triangles']:
    a, b, c = (positions[i] for i in (tri_list[t].x, tri_list[t].y, tri_list[t].z))
    cent += ((a.x + b.x + c.x) + 2 * (a.y + b.y + c.y) + 3 * (a.z + b.z + c.z)) / 3.0
if abs(cent - plan['delete_centroid_checksum']) > 1e-3 * max(1.0, abs(plan['delete_centroid_checksum'])):
    raise RuntimeError('deletion set does not match the mesh (%.4f vs %.4f)' % (cent, plan['delete_centroid_checksum']))

slots = [(str(s.material_slot_name), s.material_interface.get_path_name() if s.material_interface else None)
         for s in mesh.get_editor_property('materials')]
arm_ids = {i for i, (_, p) in enumerate(slots) if any(k in (p or '') for k in ARM_KEYS)}
bone_names = {}
for b in next(x for x in BW.get_all_bones_info(dm) if isinstance(x, (list, u.Array))):
    bone_names[b.index] = str(b.name)


def arm_fingerprint(mesh_dm):
    """Arm triangles, their UV0-3 sums and the weight sums of non-weapon bones."""
    t_ids = ids(Q.get_all_triangle_i_ds, mesh_dm)
    m_ids = ids(MATS.get_all_triangle_material_i_ds, mesh_dm)
    sets = Q.get_num_uv_sets(mesh_dm)
    fp = {'arm_triangles': 0, 'arm_uv': [0.0] * sets, 'triangles': len(t_ids), 'per_slot': {}}
    for k, t in enumerate(t_ids):
        m = m_ids[t if len(m_ids) > t else k]
        fp['per_slot'][m] = fp['per_slot'].get(m, 0) + 1
        if m not in arm_ids:
            continue
        fp['arm_triangles'] += 1
        for c in range(sets):
            r = Q.get_triangle_u_vs(mesh_dm, c, t)
            fp['arm_uv'][c] += r[0].x + r[0].y + r[1].x + r[1].y + r[2].x + r[2].y
    weights = {}
    for v in ids(Q.get_all_vertex_i_ds, mesh_dm):
        for w in weights_of(mesh_dm, v):
            name = bone_names.get(w.bone_index, str(w.bone_index))
            if not name.startswith('WPN'):
                weights[name] = weights.get(name, 0.0) + w.weight
    fp['arm_bone_weights'] = {k: round(v, 3) for k, v in sorted(weights.items())}
    return fp


before = arm_fingerprint(dm)

# A. Lift collar teeth.
for vid, p in plan['move_vertices'].items():
    if not valid(ED.set_vertex_position(dm, int(vid), u.Vector(*p), True)):
        raise RuntimeError('invalid vertex %s' % vid)
# B-E. Delete debris.
removed = ED.delete_triangles_from_mesh(dm, LU.convert_array_to_index_list(plan['delete_triangles']), True)
removed = next((x for x in removed if isinstance(x, int)), None) if isinstance(removed, tuple) else removed
if removed != len(plan['delete_triangles']):
    raise RuntimeError('deleted %s of %d triangles' % (removed, len(plan['delete_triangles'])))
# D. Rebuilt catch parts.
slot_index = {name: i for i, (name, _) in enumerate(slots)}
added = 0
for part in plan['add_parts']:
    donor = weights_of(dm, part['bone_donor_vertex'])
    if not donor or bone_names.get(max(donor, key=lambda w: w.weight).bone_index) != 'WPN_root':
        raise RuntimeError('bone donor is not a WPN_root vertex')
    new_v = ids(ED.add_vertices_to_mesh, dm, LU.convert_array_to_vector_list([u.Vector(*p) for p in part['vertices']]), True)
    for v in new_v:
        if not valid(BW.set_vertex_bone_weights(dm, v, donor)):
            raise RuntimeError('bone weights not set on new vertex %d' % v)
    new_t = ids(ED.add_triangles_to_mesh, dm,
                LU.convert_array_to_triangle_list([u.IntVector(new_v[a], new_v[b], new_v[c]) for a, b, c in part['triangles']]), 0, True)
    if len(new_t) != len(part['triangles']):
        raise RuntimeError('added %d of %d triangles' % (len(new_t), len(part['triangles'])))
    mid = slot_index[part['slot']]
    for t, corners in zip(new_t, part['triangles']):
        MATS.set_triangle_material_id(dm, t, mid, True)
        uv = u.GeometryScriptUVTriangle()
        uv.uv0, uv.uv1, uv.uv2 = (u.Vector2D(*part['uv0'][k]) for k in corners)
        UVS.set_mesh_triangle_u_vs(dm, 0, t, uv, True)
        mask = u.GeometryScriptUVTriangle()
        mask.uv0 = mask.uv1 = mask.uv2 = u.Vector2D(*part['uv1'])
        UVS.set_mesh_triangle_u_vs(dm, 1, t, mask, True)
        zero = u.GeometryScriptUVTriangle()
        for c in range(2, Q.get_num_uv_sets(dm)):
            UVS.set_mesh_triangle_u_vs(dm, c, t, zero, True)
        n = u.GeometryScriptTriangle()
        n.vector0, n.vector1, n.vector2 = (u.Vector(*part['normals'][k]) for k in corners)
        NRM.set_mesh_triangle_normals(dm, t, n, True)
    added += len(new_t)

opts = u.GeometryScriptCopyMeshToAssetOptions()
opts.set_editor_property('enable_recompute_normals', False)
opts.set_editor_property('enable_recompute_tangents', False)
opts.set_editor_property('enable_remove_degenerates', False)
opts.set_editor_property('use_original_vertex_order', True)
opts.set_editor_property('replace_materials', False)
wlod = u.GeometryScriptMeshWriteLOD()
wlod.set_editor_property('lod_index', 0)
result = AU.copy_mesh_to_skeletal_mesh(dm, mesh, opts, wlod)
outcome = [x for x in result if isinstance(x, u.GeometryScriptOutcomePins)] if isinstance(result, tuple) else []
if outcome and outcome[0] != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('CopyMeshToSkeletalMesh failed')

check = u.DynamicMesh()
AU.copy_mesh_from_skeletal_mesh(mesh, check, u.GeometryScriptCopyMeshFromAssetOptions(), lod)
after = arm_fingerprint(check)
slots_after = [(str(s.material_slot_name), s.material_interface.get_path_name() if s.material_interface else None)
               for s in mesh.get_editor_property('materials')]
close = lambda a, b, tol=1e-4: abs(a - b) <= tol * max(abs(a), abs(b), 1.0)
expected = before['triangles'] - len(plan['delete_triangles']) + added
problems = []
if after['triangles'] != expected:
    problems.append('triangles %d vs expected %d' % (after['triangles'], expected))
if after['arm_triangles'] != before['arm_triangles'] or any(not close(a, b) for a, b in zip(after['arm_uv'], before['arm_uv'])):
    problems.append('arm triangles/UVs changed')
if after['arm_bone_weights'] != before['arm_bone_weights']:
    problems.append('arm bone weights changed')
if slots_after != slots:
    problems.append('material slots changed')
fa = slot_index['M_A762_FrontAssembly_Rebuilt']
if after['per_slot'].get(fa, 0) != before['per_slot'].get(fa, 0) + added:
    problems.append('rebuilt parts not in FrontAssembly slot')
if problems:
    raise RuntimeError('A762 repair verification failed, mesh NOT saved: ' + '; '.join(problems))
E = u.EditorAssetLibrary
E.set_metadata_tag(mesh, 'WeaponSurfaceRepair', VERSION)
if not E.save_loaded_asset(mesh, False):
    raise RuntimeError('save failed')
receipt = {'version': VERSION, 'backup': str(backup), 'saved': True,
           'lifted_vertices': len(plan['move_vertices']), 'deleted_triangles': len(plan['delete_triangles']),
           'added_triangles': added, 'triangles_before': before['triangles'], 'triangles_after': after['triangles'],
           'arm_triangles': after['arm_triangles'], 'game_tested': False, 'rendered': False}
RECEIPT.write_text(json.dumps(receipt, indent=1), encoding='utf-8')
print('A762_REPAIR_SAVED', json.dumps(receipt), flush=True)
