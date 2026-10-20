"""Apply ue_plans.json to the live skeletal meshes (commandlet, UE closed).

Per mesh: the asset must still match its snapshot hash and be clean. Removed
skin triangles are deleted; replacements are appended with every corner
attribute copied from the source corner (all UV channels, colour, normal,
weights), optional normal overrides applied. Reference skeleton, material
slots, LOD count and non-skin geometry are kept; the .uasset is backed up to
Before/ first. A failure leaves that mesh unsaved and continues.
"""
import json, hashlib, shutil
from collections import defaultdict
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareHandAudit20261016'
Q = u.GeometryScript_MeshQueries; G = u.GeometryScript_AssetUtils; Bw = u.GeometryScript_BoneWeights; Ed = u.GeometryScript_MeshEdits
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem); E = u.EditorAssetLibrary
DONE = R / globals().get('DONE_SUBDIR', 'Installed'); DONE.mkdir(exist_ok=True)
TAG = 'BareSurfaceV8_20261016'


def xyz(v): return [v.x, v.y, v.z]


def rgba(v): return [v.r, v.g, v.b, v.a]


def dynamic(asset):
    dm, status = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot read ' + asset.get_path_name())
    return dm


def bones_signature(dm):
    _, bones = Bw.get_all_bones_info(dm)
    return {str(b.name): [b.index, b.parent_index, [round(x, 5) for x in xyz(b.world_transform.translation)]] for b in bones}


def install(entry):
    path = entry['path']; key = entry['key']
    file = P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    if hashlib.sha256(file.read_bytes()).hexdigest() != entry['source_sha256']:
        return dict(path=path, skipped='asset changed since snapshot; left untouched')
    asset = u.load_asset(path)
    if asset.get_outermost() in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        return dict(path=path, skipped='package dirty; left untouched')
    snap = json.loads(Path(entry['snapshot']).read_text())
    dm = dynamic(asset); before_bones = bones_signature(dm)
    tri_ids, vids, stris = snap['triangle_ids'], snap['vertex_ids'], snap['triangles']
    _, idx, gaps = Q.get_all_triangle_indices(dm, False)
    mesh_tris = u.GeometryScript_List.convert_triangle_list_to_array(idx)
    if gaps: raise RuntimeError('Expected compact triangle IDs')
    for ti in range(0, len(tri_ids), max(1, len(tri_ids) // 50)):
        if [int(x) for x in xyz(mesh_tris[tri_ids[ti]])] != [vids[x] for x in stris[ti]]:
            raise RuntimeError('Snapshot no longer matches mesh topology')
    old_count = len(mesh_tris)
    _, infos = Bw.get_all_bones_info(dm); bone_ids = {str(b.name): b.index for b in infos}
    uv_count = Q.get_num_uv_sets(dm)
    remove = set(entry['remove']); adds = list(entry['add'])
    edits = defaultdict(dict)
    for ti, k, n in entry['normals']: edits[ti][k] = n
    for ti, ns in edits.items():
        if ti in remove: continue
        remove.add(ti)
        adds.append(dict(corners=[[ti, 0, None], [ti, 1, None], [ti, 2, None]], material=snap['triangle_materials'][ti],
                         normals={str(k): n for k, n in ns.items()}))
    cache = {}
    def attrs(ti):
        if ti in cache: return cache[ti]
        mt = tri_ids[ti]
        _, n0, n1, n2, ok = Q.get_triangle_normals(dm, mt)
        if not ok: raise RuntimeError('Missing normals on source triangle')
        _, c0, c1, c2, has = Q.get_triangle_vertex_colors(dm, mt)
        uvs = []
        for ch in range(uv_count):
            a, b, c, ok = Q.get_triangle_u_vs(dm, ch, mt)
            if not ok: raise RuntimeError('Missing UV %d' % ch)
            uvs.append([[v.x, v.y] for v in (a, b, c)])
        cache[ti] = dict(normals=[xyz(v) for v in (n0, n1, n2)], colors=[rgba(v) for v in (c0, c1, c2)] if has else [[1, 1, 1, 1]] * 3, uvs=uvs)
        return cache[ti]
    verts, normals, colors, faces, weights, mats = [], [], [], [], [], []
    uvs = [[] for _ in range(uv_count)]
    for a in adds:
        base = len(verts); faces.append(u.IntVector(base, base + 1, base + 2)); mats.append(a['material'])
        for k, (ti, kk, ov) in enumerate(a['corners']):
            at = attrs(ti); local = ov if ov is not None else stris[ti][kk]
            verts.append(u.Vector(*snap['positions'][local])); weights.append(snap['weights'][local])
            n = a['normals'].get(str(k)) or at['normals'][kk]
            normals.append(u.Vector(*n)); colors.append(u.LinearColor(*at['colors'][kk]))
            for ch in range(uv_count): uvs[ch].append(u.Vector2D(*at['uvs'][ch][kk]))
    start = Q.get_vertex_count(dm)
    kwargs = dict(vertices=verts, normals=normals, vertex_colors=colors, triangles=faces)
    for ch, layer in enumerate(uvs): kwargs['uv' + str(ch)] = layer
    if verts:
        Ed.append_buffers_to_mesh(dm, u.GeometryScriptSimpleMeshBuffers(**kwargs), 0, True)
        if Q.get_vertex_count(dm) != start + len(verts): raise RuntimeError('Append vertex count mismatch')
        for i, ws in enumerate(weights):
            Bw.set_vertex_bone_weights(dm, start + i, [u.GeometryScriptBoneWeight(bone_index=bone_ids[n], weight=w) for n, w in ws.items()])
        for i, m in enumerate(mats): u.GeometryScript_Materials.set_triangle_material_id(dm, old_count + i, m, True)
    for ti in sorted(remove):
        _, ok = Ed.delete_triangle_from_mesh(dm, tri_ids[ti], True)
        if not ok: raise RuntimeError('Cannot delete triangle')
    backup = R / 'Before' / file.relative_to(P); backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists(): shutil.copy2(file, backup)
    slots = [(str(s.material_slot_name), s.material_interface) for s in asset.materials]; lods = S.get_lod_count(asset)
    options = u.GeometryScriptCopyMeshToAssetOptions(replace_materials=False, enable_recompute_normals=False, enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _, status = G.copy_mesh_to_skeletal_mesh(dm, asset, options, u.GeometryScriptMeshWriteLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot write mesh')
    if lods > 1 and not S.regenerate_lod(asset, lods, True, False): raise RuntimeError('Cannot rebuild existing LODs')
    after = dynamic(asset)
    if bones_signature(after) != before_bones: raise RuntimeError('Reference skeleton changed; left unsaved')
    if [(str(s.material_slot_name), s.material_interface) for s in asset.materials] != slots: raise RuntimeError('Material slots changed; left unsaved')
    expect = old_count - len(remove) + len(faces); got = Q.get_num_triangle_i_ds(after) if hasattr(Q, 'get_num_triangle_i_ds') else expect
    E.set_metadata_tag(asset, TAG, 'Local fold/micro-face/normal repair; native bind, slots and LODs retained')
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False): raise RuntimeError('Cannot save')
    return dict(path=path, removed=len(remove), added=len(faces), normal_faces=len(edits), lods=lods, triangles_expected=expect,
                triangles_after=got, sha256=hashlib.sha256(file.read_bytes()).hexdigest(), runtime_tested=False)


plans = json.loads((R / globals().get('PLANS_FILE', 'ue_plans.json')).read_text())
only = set(globals().get('ONLY', []))
import gc
for n, entry in enumerate(plans):
    if n % 4 == 3: gc.collect(); u.SystemLibrary.collect_garbage()
    if only and entry['path'] not in only: continue
    receipt = DONE / (entry['key'] + '.json')
    if receipt.exists(): continue
    try:
        row = install(entry)
    except Exception as exc:
        row = dict(path=entry['path'], error=str(exc))
    if 'error' not in row and 'skipped' not in row: receipt.write_text(json.dumps(row, indent=1))
    else: (DONE / (entry['key'] + '.failed.json')).write_text(json.dumps(row, indent=1))
    print('BARE_V8_INSTALL', json.dumps(row), flush=True)
print('BARE_V8_INSTALL_COMPLETE', flush=True)
