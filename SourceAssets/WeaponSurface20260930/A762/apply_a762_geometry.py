"""Apply items 1, 4, 5, 6 to SK_A762_Manny LOD0 in one write. Run through ../run_ue.ps1.

- Bake/denoise_plan.bin (plan_denoise.py): moved Meshy vertices and their corner normals.
- Bake/rebuild_parts.bin (rebuild_slots_blender.py): replacement geometry for the magazine
  shell and the bevelled rebuilt slots ('replace'), plus the rivets ('add').
Both plans index the A762_AfterRepair dump; the mesh must still match it. Arm triangles and
their UV0-3, non-weapon bone weights and material slots are verified unchanged before the
save; the asset is backed up to BeforeGeometry/ first. New triangles get a temporary UV1
(neutral mask texel) until the full UV1 re-bake (item 3) rewrites every gun triangle.
No PIE, capture or gameplay check is performed.
"""
import array
import json
import shutil
import unreal as u
from pathlib import Path

HERE = Path(__file__).parent
MESH = '/Game/Weapons/A762/Integrated20260920/SK_A762_Manny'
VERSION = 'WS-Geometry-20260930'
AU, Q, LU = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries, u.GeometryScript_List
ED, UVS, NRM, MATS, BW = (u.GeometryScript_MeshEdits, u.GeometryScript_UVs, u.GeometryScript_Normals,
                          u.GeometryScript_Materials, u.GeometryScript_BoneWeights)
ARM_KEYS = ('Manny', 'BarePalm', 'BareNative', 'BareFamily')
NEUTRAL_UV1 = (0.7002, 0.1494)
RECEIPT = HERE / 'geometry_receipt.json'


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


def read_plan(path):
    with open(path, 'rb') as f:
        header = json.loads(f.readline().decode('utf-8'))
        return header, f.read()


def take(buf, offset, code, count):
    a = array.array(code)
    size = a.itemsize * count
    a.frombytes(buf[offset:offset + size])
    return a, offset + size


commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not commandlet:
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('A762 geometry: PIE is running; nothing changed')
    if MESH in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('A762 geometry: mesh has unsaved edits; nothing changed')
if RECEIPT.exists() and json.loads(RECEIPT.read_text(encoding='utf-8')).get('saved'):
    raise RuntimeError('A762 geometry already applied (geometry_receipt.json); restore BeforeGeometry/ to re-run')

dn_head, dn = read_plan(HERE / 'Bake' / 'denoise_plan.bin')
rb_head, rb = read_plan(HERE / 'Bake' / 'rebuild_parts.bin')
off = 0
moved, off = take(dn, off, 'i', dn_head['moved'])
moved_pos, off = take(dn, off, 'f', dn_head['moved'] * 3)
normal_tris, off = take(dn, off, 'i', dn_head['normal_triangles'])
normal_vals, off = take(dn, off, 'f', dn_head['normal_triangles'] * 9)
parts, off = [], 0
for p in rb_head['parts']:
    P, off = take(rb, off, 'f', p['vertices'] * 3)
    T, off = take(rb, off, 'i', p['triangles'] * 3)
    N, off = take(rb, off, 'f', p['triangles'] * 9)
    UV, off = take(rb, off, 'f', p['triangles'] * 6)
    parts.append(dict(p, P=P, T=T, N=N, UV=UV))

content = Path(u.Paths.project_dir()).resolve() / 'Content'
rel = MESH.removeprefix('/Game/') + '.uasset'
backup = HERE / 'BeforeGeometry' / rel
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(content / rel, backup)

mesh = u.load_asset(MESH)
lod = u.GeometryScriptMeshReadLOD()
lod.set_editor_property('lod_type', u.GeometryScriptLODType.SOURCE_MODEL)
dm = u.DynamicMesh()
AU.copy_mesh_from_skeletal_mesh(mesh, dm, u.GeometryScriptCopyMeshFromAssetOptions(), lod)
if Q.get_has_triangle_id_gaps(dm) or Q.get_has_vertex_id_gaps(dm):
    raise RuntimeError('id gaps: indices would not match the plans')
positions = LU.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm, True), u.GeometryScriptVectorList))
checksum = sum(abs(p.x) + abs(p.y) + abs(p.z) for p in positions)
n_tris = len(ids(Q.get_all_triangle_i_ds, dm))
for head in (dn_head, rb_head):
    if n_tris != head['triangle_count'] or len(positions) != head['vertex_count']:
        raise RuntimeError('mesh size changed since the plan (%d/%d)' % (n_tris, len(positions)))
    if abs(checksum - head['position_checksum']) > 1e-4 * head['position_checksum']:
        raise RuntimeError('mesh geometry changed since the plan')

slots = [(str(s.material_slot_name), s.material_interface.get_path_name() if s.material_interface else None)
         for s in mesh.get_editor_property('materials')]
slot_index = {name: i for i, (name, _) in enumerate(slots)}
arm_ids = {i for i, (_, p) in enumerate(slots) if any(k in (p or '') for k in ARM_KEYS)}
bone_names = {b.index: str(b.name) for b in next(x for x in BW.get_all_bones_info(dm) if isinstance(x, (list, u.Array)))}


def fingerprint(mesh_dm):
    t_ids = ids(Q.get_all_triangle_i_ds, mesh_dm)
    m_ids = ids(MATS.get_all_triangle_material_i_ds, mesh_dm)
    sets = Q.get_num_uv_sets(mesh_dm)
    fp = {'arm_triangles': 0, 'arm_uv': [0.0] * sets, 'triangles': len(t_ids), 'per_slot': {}, 'uv_sets': sets}
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


before = fingerprint(dm)
all_tris = ids(Q.get_all_triangle_i_ds, dm)
mat_ids = ids(MATS.get_all_triangle_material_i_ds, dm)
tri_list = LU.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm, True), u.GeometryScriptTriangleList))

# Donor bone weights per affected slot, read before anything is deleted.
donors = {}
for part in parts:
    sid = slot_index[part['slot']]
    if sid in donors:
        continue
    t = next(k for k in all_tris if mat_ids[k] == sid)
    donors[sid] = weights_of(dm, tri_list[t].x)
    if not donors[sid]:
        raise RuntimeError('no bone weights to copy for ' + part['slot'])

# 1. Denoise: vertex moves, then corner normals of the Meshy triangles.
for i, v in enumerate(moved):
    if not valid(ED.set_vertex_position(dm, v, u.Vector(moved_pos[3 * i], moved_pos[3 * i + 1], moved_pos[3 * i + 2]), True)):
        raise RuntimeError('invalid vertex %d' % v)
for i, t in enumerate(normal_tris):
    n = u.GeometryScriptTriangle()
    o = 9 * i
    n.vector0 = u.Vector(normal_vals[o], normal_vals[o + 1], normal_vals[o + 2])
    n.vector1 = u.Vector(normal_vals[o + 3], normal_vals[o + 4], normal_vals[o + 5])
    n.vector2 = u.Vector(normal_vals[o + 6], normal_vals[o + 7], normal_vals[o + 8])
    if not valid(NRM.set_mesh_triangle_normals(dm, t, n, True)):
        raise RuntimeError('invalid triangle %d' % t)

# 4-5. Replace whole slots.
replace = {slot_index[p['slot']] for p in parts if p['mode'] == 'replace'}
doomed = [t for t in all_tris if mat_ids[t] in replace]
removed = ED.delete_triangles_from_mesh(dm, LU.convert_array_to_index_list(doomed), True)
removed = next((x for x in removed if isinstance(x, int)), None) if isinstance(removed, tuple) else removed
if removed != len(doomed):
    raise RuntimeError('deleted %s of %d triangles' % (removed, len(doomed)))

# 4-6. Add the new geometry.
uv_sets = Q.get_num_uv_sets(dm)
added = {}
for part in parts:
    sid = slot_index[part['slot']]
    P, T, N, UV = part['P'], part['T'], part['N'], part['UV']
    new_v = ids(ED.add_vertices_to_mesh, dm,
                LU.convert_array_to_vector_list([u.Vector(P[3 * i], P[3 * i + 1], P[3 * i + 2]) for i in range(part['vertices'])]), True)
    for v in new_v:
        if not valid(BW.set_vertex_bone_weights(dm, v, donors[sid])):
            raise RuntimeError('bone weights not set on %d' % v)
    new_t = ids(ED.add_triangles_to_mesh, dm, LU.convert_array_to_triangle_list(
        [u.IntVector(new_v[T[3 * i]], new_v[T[3 * i + 1]], new_v[T[3 * i + 2]]) for i in range(part['triangles'])]), 0, True)
    if len(new_t) != part['triangles']:
        raise RuntimeError('%s: added %d of %d triangles' % (part['slot'], len(new_t), part['triangles']))
    mask = u.GeometryScriptUVTriangle()
    mask.uv0 = mask.uv1 = mask.uv2 = u.Vector2D(*NEUTRAL_UV1)
    zero = u.GeometryScriptUVTriangle()
    for i, t in enumerate(new_t):
        MATS.set_triangle_material_id(dm, t, sid, True)
        uv = u.GeometryScriptUVTriangle()
        o = 6 * i
        uv.uv0, uv.uv1, uv.uv2 = u.Vector2D(UV[o], UV[o + 1]), u.Vector2D(UV[o + 2], UV[o + 3]), u.Vector2D(UV[o + 4], UV[o + 5])
        UVS.set_mesh_triangle_u_vs(dm, 0, t, uv, True)
        UVS.set_mesh_triangle_u_vs(dm, 1, t, mask, True)
        for c in range(2, uv_sets):
            UVS.set_mesh_triangle_u_vs(dm, c, t, zero, True)
        n = u.GeometryScriptTriangle()
        o = 9 * i
        n.vector0 = u.Vector(N[o], N[o + 1], N[o + 2])
        n.vector1 = u.Vector(N[o + 3], N[o + 4], N[o + 5])
        n.vector2 = u.Vector(N[o + 6], N[o + 7], N[o + 8])
        NRM.set_mesh_triangle_normals(dm, t, n, True)
    added[sid] = added.get(sid, 0) + len(new_t)

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
after = fingerprint(check)
slots_after = [(str(s.material_slot_name), s.material_interface.get_path_name() if s.material_interface else None)
               for s in mesh.get_editor_property('materials')]
close = lambda a, b, tol=1e-4: abs(a - b) <= tol * max(abs(a), abs(b), 1.0)
expected = before['triangles'] - len(doomed) + sum(added.values())
problems = []
if after['triangles'] != expected:
    problems.append('triangles %d vs expected %d' % (after['triangles'], expected))
if after['arm_triangles'] != before['arm_triangles'] or any(not close(a, b) for a, b in zip(after['arm_uv'], before['arm_uv'])):
    problems.append('arm triangles/UVs changed')
if after['arm_bone_weights'] != before['arm_bone_weights']:
    problems.append('arm bone weights changed')
if slots_after != slots:
    problems.append('material slots changed')
for sid in set(added) | replace:
    want = (0 if sid in replace else before['per_slot'].get(sid, 0)) + added.get(sid, 0)
    if after['per_slot'].get(sid, 0) != want:
        problems.append('%s has %d triangles, expected %d' % (slots[sid][0], after['per_slot'].get(sid, 0), want))
if problems:
    raise RuntimeError('A762 geometry verification failed, mesh NOT saved: ' + '; '.join(problems))
E = u.EditorAssetLibrary
E.set_metadata_tag(mesh, 'WeaponSurfaceGeometry', VERSION)
if not E.save_loaded_asset(mesh, False):
    raise RuntimeError('save failed (is a FPSGAME-mp game holding the file?)')
receipt = {'version': VERSION, 'backup': str(backup), 'saved': True, 'moved_vertices': len(moved),
           'renormalled_triangles': len(normal_tris), 'replaced_triangles': len(doomed),
           'added_triangles': {slots[k][0]: v for k, v in added.items()},
           'triangles_before': before['triangles'], 'triangles_after': after['triangles'],
           'arm_triangles': after['arm_triangles'], 'uv1_pending_rebake': True, 'game_tested': False, 'rendered': False}
RECEIPT.write_text(json.dumps(receipt, indent=1), encoding='utf-8')
print('A762_GEOMETRY_SAVED', json.dumps(receipt), flush=True)
