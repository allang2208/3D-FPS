"""Write the baked ASH12 gun-only UV1 through Geometry Script and save its runtime mesh.
Backs up the original package and preserves hand UVs, normals, weights, colors and slots.
Texture and material binding is handled separately by install_surface.py. No PIE or tests.
"""
import hashlib
import json
import shutil
import unreal as u
from pathlib import Path

HERE = Path(__file__).parent
E, L, A = u.EditorAssetLibrary, u.MaterialEditingLibrary, u.AssetToolsHelpers.get_asset_tools()
AU, Q, UVS, LU = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries, u.GeometryScript_UVs, u.GeometryScript_List
MESH = '/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface'
DEST = '/Game/Weapons/ASH12/SurfaceStandard20260930'
PRESET = '/Game/Weapons/WeaponSurface/Presets/MI_WS_'
VERSION = 'WS1-20260930'


RECEIPT = HERE / 'uv_install_receipt.json'
receipt = json.loads(RECEIPT.read_text(encoding='utf-8')) if RECEIPT.exists() else {
    'version': VERSION, 'backups': {}, 'uv1': None, 'textures': {}, 'materials': {}, 'bindings': {},
    'complete': False, 'game_tested': False, 'rendered': False}


def record():
    RECEIPT.write_text(json.dumps(receipt, indent=1, ensure_ascii=False), encoding='utf-8')


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed ' + asset.get_path_name())


def pick(result, cls):
    if isinstance(result, tuple):
        for item in result:
            if isinstance(item, cls):
                return item
        raise RuntimeError('No %s in result' % cls.__name__)
    return result


commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
targets = [MESH]
if not commandlet:
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('ASH12 surface: PIE is running; nothing changed')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty & set(targets):
        raise RuntimeError('ASH12 surface: target packages have unsaved edits ' + str(sorted(dirty & set(targets))))

# 1. Backups of the exact packages this script rewrites.
content = Path(u.Paths.project_dir()).resolve() / 'Content'
for package in targets:
    if package in receipt['backups']:
        continue
    rel = package.removeprefix('/Game/') + '.uasset'
    dst = HERE / 'Before' / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(content / rel, dst)
    receipt['backups'][package] = str(dst)
record()

# 2. UV1 layout.
mesh = u.load_asset(MESH)
with open(HERE / 'Bake' / 'ASH12_uv1.bin', 'rb') as f:
    header = json.loads(f.readline().decode('utf-8'))
    raw = f.read()
# Write UV1 on first install and again whenever the bake was made on different geometry
# (e.g. after apply_a762_geometry.py and a full re-bake).
if receipt['uv1'] is None or receipt['uv1'].get('bake_position_checksum') != header['position_checksum']:
    import array
    uv1 = array.array('f')
    uv1.frombytes(raw)
    dm = u.DynamicMesh()
    lod = u.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', u.GeometryScriptLODType.SOURCE_MODEL)
    AU.copy_mesh_from_skeletal_mesh(mesh, dm, u.GeometryScriptCopyMeshFromAssetOptions(), lod)
    tri_ids = LU.convert_index_list_to_array(pick(Q.get_all_triangle_i_ds(dm), u.GeometryScriptIndexList))
    positions = LU.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm, True), u.GeometryScriptVectorList))
    checksum = sum(abs(p.x) + abs(p.y) + abs(p.z) for p in positions)
    if len(tri_ids) != header['triangles'] or len(uv1) != header['triangles'] * 6:
        raise RuntimeError('ASH12 triangle count changed since the bake: %d vs %d' % (len(tri_ids), header['triangles']))
    if abs(checksum - header['position_checksum']) > 1e-4 * header['position_checksum']:
        raise RuntimeError('ASH12 geometry changed since the bake (checksum %.3f vs %.3f)' % (checksum, header['position_checksum']))
    def fingerprint(mesh_dm, arm_ids):
        """Order-independent sums: every UV channel (UV1 split arm/gun), normals, bone weights."""
        t_ids = LU.convert_index_list_to_array(pick(Q.get_all_triangle_i_ds(mesh_dm), u.GeometryScriptIndexList))
        m_ids = LU.convert_index_list_to_array(pick(u.GeometryScript_Materials.get_all_triangle_material_i_ds(mesh_dm), u.GeometryScriptIndexList))
        sets = Q.get_num_uv_sets(mesh_dm)
        fp = {'triangles': len(t_ids), 'uv_sets': sets, 'uv': [0.0] * sets, 'uv1_arms': 0.0, 'normals': 0.0, 'colors': [0.0,0.0,0.0,0.0]}
        for k, t in enumerate(t_ids):
            arm = m_ids[t if len(m_ids) > t else k] in arm_ids
            for c in range(sets):
                r = Q.get_triangle_u_vs(mesh_dm, c, t)
                s = r[0].x + r[0].y + r[1].x + r[1].y + r[2].x + r[2].y
                if c == 1 and arm:
                    fp['uv1_arms'] += s
                elif c != 1 or not arm:
                    fp['uv'][c] += s
            colors = [x for x in Q.get_triangle_vertex_colors(mesh_dm,t) if isinstance(x,u.LinearColor)]
            for col in colors:
                for j,value in enumerate((col.r,col.g,col.b,col.a)):fp['colors'][j] += value
            n = [x for x in Q.get_triangle_normals(mesh_dm, t) if isinstance(x, u.Vector)]
            fp['normals'] += sum(abs(v.x) + 2 * abs(v.y) + 3 * abs(v.z) for v in n[:3])
        v_ids = LU.convert_index_list_to_array(pick(Q.get_all_vertex_i_ds(mesh_dm), u.GeometryScriptIndexList))
        weights = {}
        for v in v_ids:
            r = u.GeometryScript_BoneWeights.get_vertex_bone_weights(mesh_dm, v)
            for w in next((x for x in r if isinstance(x, (list, u.Array))), []):
                weights[w.bone_index] = weights.get(w.bone_index, 0.0) + w.weight
        fp['bone_weight_sums'] = {str(k): round(v, 3) for k, v in sorted(weights.items())}
        return fp

    had = Q.get_num_uv_sets(dm)
    mats0 = [s.material_interface.get_path_name() if s.material_interface else '' for s in mesh.get_editor_property('materials')]
    arm_ids0 = {i for i, p in enumerate(mats0) if any(k in p for k in ('Manny', 'BarePalm', 'BareNative', 'BareFamily'))}
    before_fp = fingerprint(dm, arm_ids0)
    UVS.set_num_uv_sets(dm, max(2, had))
    # The V7 bare-arm material reads UV1-3 on the arm sections: only gun triangles get the
    # mask layout. Degenerate triangles that Blender could not project get a finite corner.
    ids = LU.convert_index_list_to_array(pick(u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm), u.GeometryScriptIndexList))
    finite = lambda x: x == x and abs(x) < 4.0
    written = skipped_arms = repaired = 0
    gun_uv1 = 0.0
    for k, t in enumerate(tri_ids):
        if ids[t if len(ids) > t else k] in arm_ids0:
            skipped_arms += 1
            continue
        o = k * 6
        vals = [uv1[o + j] for j in range(6)]
        if not all(finite(v) for v in vals):
            vals = [0.0005] * 6
            repaired += 1
        gun_uv1 += sum(vals)
        tri = u.GeometryScriptUVTriangle()
        tri.uv0 = u.Vector2D(vals[0], vals[1])
        tri.uv1 = u.Vector2D(vals[2], vals[3])
        tri.uv2 = u.Vector2D(vals[4], vals[5])
        UVS.set_mesh_triangle_u_vs(dm, 1, t, tri, True)
        written += 1
    opts = u.GeometryScriptCopyMeshToAssetOptions()
    opts.set_editor_property('enable_recompute_normals', False)
    opts.set_editor_property('enable_recompute_tangents', False)
    opts.set_editor_property('enable_remove_degenerates', False)
    opts.set_editor_property('use_original_vertex_order', True)
    opts.set_editor_property('replace_materials', False)
    wlod = u.GeometryScriptMeshWriteLOD()
    wlod.set_editor_property('lod_index', 0)
    slots_before = [(str(s.material_slot_name), s.material_interface.get_path_name() if s.material_interface else None)
                    for s in mesh.get_editor_property('materials')]
    result = AU.copy_mesh_to_skeletal_mesh(dm, mesh, opts, wlod)
    outcome = [x for x in result if isinstance(x, u.GeometryScriptOutcomePins)] if isinstance(result, tuple) else []
    if outcome and outcome[0] != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('CopyMeshToSkeletalMesh failed')
    # Read back and compare order-independent fingerprints (the build may regroup triangles):
    # UV0/UV2/UV3 and arm UV1 unchanged, gun UV1 as written, normals, bone weights, positions, slots.
    check = u.DynamicMesh()
    AU.copy_mesh_from_skeletal_mesh(mesh, check, u.GeometryScriptCopyMeshFromAssetOptions(), lod)
    after_fp = fingerprint(check, arm_ids0)
    back_pos = LU.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(check, True), u.GeometryScriptVectorList))
    back_sum = sum(abs(p.x) + abs(p.y) + abs(p.z) for p in back_pos)
    slots_after = [(str(s.material_slot_name), s.material_interface.get_path_name() if s.material_interface else None)
                   for s in mesh.get_editor_property('materials')]
    close = lambda a, b, tol=1e-4: abs(a - b) <= tol * max(abs(a), abs(b), 1.0)
    problems = []
    if after_fp['triangles'] != before_fp['triangles'] or after_fp['uv_sets'] != before_fp['uv_sets']:
        problems.append('topology/uv sets')
    for c in range(before_fp['uv_sets']):
        if c != 1 and not close(after_fp['uv'][c], before_fp['uv'][c]):
            problems.append('uv%d changed' % c)
    if not close(after_fp['uv1_arms'], before_fp['uv1_arms']):
        problems.append('arm uv1 changed')
    if not close(after_fp['uv'][1], gun_uv1):
        problems.append('gun uv1 %.3f vs %.3f' % (after_fp['uv'][1], gun_uv1))
    if not close(after_fp['normals'], before_fp['normals']):
        problems.append('normals changed')
    if any(not close(a,b) for a,b in zip(before_fp['colors'],after_fp['colors'])):
        problems.append('authored region vertex colors changed')
    bw0, bw1 = before_fp['bone_weight_sums'], after_fp['bone_weight_sums']
    if set(bw0) != set(bw1) or any(not close(bw0[k], bw1[k], 1e-3) for k in bw0):
        problems.append('bone weights changed')
    if not close(back_sum, checksum) or slots_after != slots_before:
        problems.append('positions/slots changed')
    if problems:
        raise RuntimeError('UV1 write verification failed, mesh NOT saved: ' + '; '.join(problems))
    E.set_metadata_tag(mesh, 'WeaponSurfaceUV1', VERSION)
    save(mesh)
    receipt.setdefault('history', []).append({k: v for k, v in (receipt['uv1'] or {}).items() if 'fingerprint' not in k})
    receipt['uv1'] = {'bake_position_checksum': header['position_checksum'],
                      'triangles': after_fp['triangles'], 'uv_sets': after_fp['uv_sets'], 'gun_triangles_written': written,
                      'arm_triangles_preserved': skipped_arms, 'degenerate_repaired': repaired,
                      'fingerprint_before': before_fp, 'fingerprint_after': after_fp, 'slots_unchanged': True}
    record()
    print('ASH12_SURFACE_UV1_SAVED', json.dumps({k: v for k, v in receipt['uv1'].items() if 'fingerprint' not in k}), flush=True)

print('ASH12_WS_UV1_INSTALL_FINISHED',flush=True)
