"""Read-only snapshot of every skeletal mesh that renders the bare-skin shader.

Scope = meshes named in modular_outfits.json plus any other SkeletalMesh that
references the same skin parent materials (through material instances).
Writes Snapshots/<key>.json and inventory.json; never saves or dirties assets.
Meshes are visited one at a time with periodic garbage collection; finished
snapshots (snap_index.json) and known skin-free meshes (noskin.json) are reused.
"""
import json, hashlib, gc
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareHandAudit20261016'
SNAP = R / globals().get('SNAP_SUBDIR', 'Snapshots'); SNAP.mkdir(exist_ok=True)
ONLY_PATHS = globals().get('ONLY_PATHS')          # read-back mode: explicit meshes, no scope discovery
Q = u.GeometryScript_MeshQueries; G = u.GeometryScript_AssetUtils; Bw = u.GeometryScript_BoneWeights
L = u.MaterialEditingLibrary
AR = u.AssetRegistryHelpers.get_asset_registry()
HARD = u.AssetRegistryDependencyOptions(include_soft_package_references=False, include_hard_package_references=True,
                                        include_searchable_names=False, include_soft_management_references=False,
                                        include_hard_management_references=False)
INDEX = SNAP / 'index.json' if ONLY_PATHS else R / 'snap_index.json'; NOSKIN = R / 'noskin.json'
index = json.loads(INDEX.read_text()) if INDEX.exists() else {}
noskin = set(json.loads(NOSKIN.read_text())) if NOSKIN.exists() else set()


def xyz(v): return [v.x, v.y, v.z]


def object_path(p): return p if '.' in p.split('/')[-1] else p + '.' + p.split('/')[-1]


def file_of(path): return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha_file(f):
    h = hashlib.sha256()
    with open(f, 'rb') as s:
        for block in iter(lambda: s.read(1 << 20), b''): h.update(block)
    return h.hexdigest()


def key_of(path): return hashlib.sha256(path.split('.')[0].encode()).hexdigest()[:12]


def is_mesh(path):
    return any(str(ad.asset_class_path.asset_name) == 'SkeletalMesh' for ad in AR.get_assets_by_package_name(path.split('.')[0]))


base_cache = {}


def base_material(mi):
    seen = 0
    while isinstance(mi, u.MaterialInstance) and seen < 16:
        mi = mi.get_editor_property('parent'); seen += 1
    return mi


def is_skin_base(m):
    if m is None: return False
    path = m.get_path_name()
    if path not in base_cache:
        skin = False
        try:
            node = L.get_material_property_input_node(m, u.MaterialProperty.MP_NORMAL)
            skin = bool(node) and 'SkinFields' in str(node.get_editor_property('code'))
        except Exception:
            pass
        base_cache[path] = skin
    return base_cache[path]


def slots_of(asset):
    out = []
    for s in asset.materials:
        mi = s.material_interface; b = base_material(mi)
        out.append(dict(slot=str(s.material_slot_name), path=mi.get_path_name() if mi else '', base=b.get_path_name() if b else '', skin=is_skin_base(b)))
    return out


visited = [0]
def tick():
    visited[0] += 1
    if visited[0] % 8 == 0:
        gc.collect(); u.SystemLibrary.collect_garbage()


def discover_scope():
    # 1. Named candidates (paths only).
    cfg = json.loads((P / 'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
    named = set()
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(k, str) and k.startswith('/Game/'): named.add(object_path(k.split('.')[0]))
                walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
        elif isinstance(x, str) and x.startswith('/Game/'):
            named.add(object_path(x.split('.')[0]))
    walk(cfg)
    named = {p for p in named if is_mesh(p)}
    # 2. Skin parents: from finished snapshots plus named meshes not yet visited.
    parents = set()
    for k in index:
        snap = json.loads((SNAP / (k + '.json')).read_text())
        for s in snap.get('slots', []):
            if s.get('skin') and s.get('base'): parents.add(s['base'].split('.')[0])
    for p in sorted(named):
        if key_of(p) in index or p in noskin: continue
        a = u.load_asset(p)
        for s in slots_of(a):
            if s['skin']: parents.add(s['base'].split('.')[0])
        a = None; tick()
    scope = set(named)
    todo = list(parents); seen_pk = set(todo)
    while todo:
        pk = todo.pop()
        for ref in AR.get_referencers(pk, HARD) or []:
            ref = str(ref)
            if ref in seen_pk or not ref.startswith('/Game/'): continue
            seen_pk.add(ref)
            for ad in AR.get_assets_by_package_name(ref):
                cls = str(ad.asset_class_path.asset_name)
                if cls in ('MaterialInstanceConstant', 'Material'): todo.append(ref)
                elif cls == 'SkeletalMesh': scope.add(object_path(ref))
    return parents, scope


if ONLY_PATHS:
    parents, scope = set(), set(ONLY_PATHS)
else:
    parents, scope = discover_scope()
print('BARE_AUDIT_SCOPE', len(scope), 'meshes', len(parents), 'skin parents', flush=True)

# 3. Snapshot one mesh at a time.
inventory = []
for path in sorted(scope):
    key = key_of(path); file = file_of(path)
    if not file.exists(): continue
    sha = sha_file(file)
    if path in noskin:
        inventory.append(dict(path=path, key=key, skin=False)); continue
    if index.get(key, {}).get('sha') == sha:
        inventory.append(dict(path=path, key=key, skin=True, source_sha256=sha)); continue
    asset = u.load_asset(path)
    slots = slots_of(asset)
    skin = {i for i, s in enumerate(slots) if s['skin']}
    if not skin:
        noskin.add(path); inventory.append(dict(path=path, key=key, skin=False))
        print('BARE_AUDIT_NOSKIN', path, flush=True); asset = None; tick(); continue
    lods = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(asset)
    dm, status = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Read failed ' + path)
    _, positions, _ = Q.get_all_vertex_positions(dm, False); ps = u.GeometryScript_List.convert_vector_list_to_array(positions)
    _, triangles, _ = Q.get_all_triangle_indices(dm, False); ts = u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    _, bones = Bw.get_all_bones_info(dm); names = {b.index: str(b.name) for b in bones}
    tri_ids, mats = [], []
    for ti in range(len(ts)):
        m, valid = u.GeometryScript_Materials.get_triangle_material_id(dm, ti)
        if valid and m in skin: tri_ids.append(ti); mats.append(m)
    vids = sorted({int(v) for ti in tri_ids for v in xyz(ts[ti])}); remap = {v: i for i, v in enumerate(vids)}
    weights = []
    for vi in vids:
        _, ws, valid = Bw.get_vertex_bone_weights(dm, vi)
        weights.append({names[w.bone_index]: w.weight for w in ws if w.weight > 0} if valid else {})
    ns, uv = [], []
    for ti in tri_ids:
        _, a, b, c, _ = Q.get_triangle_normals(dm, ti); ns.append([xyz(v) for v in (a, b, c)])
        a, b, c, _ = Q.get_triangle_u_vs(dm, 0, ti); uv.append([[v.x, v.y] for v in (a, b, c)])
    d = dict(path=path, key=key, slots=slots, lods=lods, source_sha256=sha,
             positions=[xyz(ps[i]) for i in vids], triangles=[[remap[int(v)] for v in xyz(ts[i])] for i in tri_ids],
             normals=ns, uv=uv, triangle_materials=mats, weights=weights, vertex_ids=vids, triangle_ids=tri_ids,
             materials=[dict(slot=s['slot'], path=s['path']) for s in slots], uv_sets=Q.get_num_uv_sets(dm))
    (SNAP / (key + '.json')).write_text(json.dumps(d, separators=(',', ':')))
    index[key] = dict(path=path, sha=sha); INDEX.write_text(json.dumps(index, indent=0))
    inventory.append(dict(path=path, key=key, skin=True, source_sha256=sha))
    print('BARE_AUDIT_SNAPSHOT', path, len(vids), len(tri_ids), flush=True)
    d = dm = ps = ts = asset = None; tick()
if not ONLY_PATHS:
    NOSKIN.write_text(json.dumps(sorted(noskin), indent=0))
    (R / 'inventory.json').write_text(json.dumps(dict(skin_parents=sorted(parents), meshes=inventory), indent=1))
print('BARE_AUDIT_SNAPSHOT_COMPLETE', len(inventory), 'skin', sum(r['skin'] for r in inventory), flush=True)
