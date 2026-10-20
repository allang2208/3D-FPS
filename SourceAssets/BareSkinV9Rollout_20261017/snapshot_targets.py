"""Read-only commandlet: current state of every in-scope first-person skin mesh for the V9 rollout.

Per mesh (Snapshots/<key>.json): skin triangles only (slots whose base material is a bare-skin parent),
positions, triangles, corner normals, UV0, weights, dynamic-mesh vertex/triangle IDs, slots, LOD count,
asset hash, and the mesh's own reference skeleton (component space, from the dynamic mesh bone info).
Never saves or dirties assets. Already-snapshotted meshes with an unchanged hash are skipped.
"""
import json, hashlib, gc
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareSkinV9Rollout_20261017'
SNAP = R / 'Snapshots'; SNAP.mkdir(exist_ok=True)
Q = u.GeometryScript_MeshQueries; G = u.GeometryScript_AssetUtils; Bw = u.GeometryScript_BoneWeights
SKIN_PARENTS = {'/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials/M_BareFamily_Arms',
                '/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials/M_BareFamily_Hands',
                '/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials/M_BareNative_Default',
                '/Game/Characters/ModularOutfit20260924/ThumbSurfaceContactV9_20261002/M16/M_M16ThumbHands',
                '/Game/Characters/ModularOutfit20260924/ThumbSurfaceContactV9_20261002/M16/M_M16ThumbNative',
                '/Game/Weapons/Super90/JointSurface20261012/Materials/M_Super90JointSkin_Arms',
                '/Game/Weapons/Super90/JointSurface20261012/Materials/M_Super90JointSkin_Hands',
                '/Game/Characters/ModularOutfit20260924/BareSkinV9M4/M_M4SkinV9'}
import os
targets = json.loads((R / 'scope_candidates.json').read_text())['used']
if os.environ.get('V9R_ONLY'):                      # restrict to one batch (keeps installed batches' V8 snapshots)
    targets = [m['mesh'] for b in os.environ['V9R_ONLY'].split(',') for m in json.loads((R / (b + '.json')).read_text())['meshes']]
index_file = R / 'snap_index.json'
index = json.loads(index_file.read_text()) if index_file.exists() else {}


def xyz(v): return [v.x, v.y, v.z]
def file_of(path): return P / 'Content' / (path.removeprefix('/Game/') + '.uasset')
def key_of(path): return hashlib.sha256(path.encode()).hexdigest()[:12]


def sha_file(f):
    h = hashlib.sha256()
    with open(f, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def base_of(mi):
    for _ in range(16):
        if not isinstance(mi, u.MaterialInstance): break
        mi = mi.get_editor_property('parent')
    return mi


count = 0
for pk in targets:
    path = pk + '.' + pk.split('/')[-1]; key = key_of(pk); f = file_of(pk)
    if not f.exists(): print('V9R_MISSING', pk, flush=True); continue
    sha = sha_file(f)
    if index.get(key, {}).get('sha') == sha: continue
    asset = u.load_asset(path)
    slots = []
    for s in asset.materials:
        mi = s.material_interface; b = base_of(mi)
        bp = b.get_path_name().split('.')[0] if b else ''
        # skin slots left without any material (SteelWarhammer bare arms) are skin too
        unset_skin = mi is None and str(s.material_slot_name).startswith('Skin_')
        slots.append(dict(slot=str(s.material_slot_name), imported=str(s.get_editor_property('imported_material_slot_name')),
                          path=mi.get_path_name() if mi else '', base=bp, skin=bp in SKIN_PARENTS or unset_skin))
    skin = {i for i, s in enumerate(slots) if s['skin']}
    lods = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(asset)
    dm, status = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Read failed ' + pk)
    _, ps, _ = Q.get_all_vertex_positions(dm, False); ps = u.GeometryScript_List.convert_vector_list_to_array(ps)
    _, ts, _ = Q.get_all_triangle_indices(dm, False); ts = u.GeometryScript_List.convert_triangle_list_to_array(ts)
    _, bones = Bw.get_all_bones_info(dm); names = {b.index: str(b.name) for b in bones}
    tri_ids, mats = [], []
    for ti in range(len(ts)):
        mid, ok = u.GeometryScript_Materials.get_triangle_material_id(dm, ti)
        if ok and mid in skin: tri_ids.append(ti); mats.append(mid)
    vids = sorted({int(v) for ti in tri_ids for v in xyz(ts[ti])}); remap = {v: i for i, v in enumerate(vids)}
    weights = []
    for vi in vids:
        _, ws, ok = Bw.get_vertex_bone_weights(dm, vi)
        weights.append({names[w.bone_index]: w.weight for w in ws if w.weight > 0} if ok else {})
    ns, uv = [], []
    for ti in tri_ids:
        _, a, b, c, _ = Q.get_triangle_normals(dm, ti); ns.append([xyz(v) for v in (a, b, c)])
        a, b, c, _ = Q.get_triangle_u_vs(dm, 0, ti); uv.append([[v.x, v.y] for v in (a, b, c)])
    bone_rows = {}
    for b in bones:
        tr = b.world_transform; q = tr.rotation
        bone_rows[str(b.name)] = dict(index=b.index, parent=b.parent_index, t=xyz(tr.translation), q=[q.x, q.y, q.z, q.w])
    skel = asset.get_editor_property('skeleton')
    d = dict(path=pk, key=key, sha=sha, lods=lods, slots=slots, skeleton=skel.get_path_name() if skel else '',
             morphs=[m.get_name() for m in (asset.get_editor_property('morph_targets') or [])],
             positions=[xyz(ps[i]) for i in vids], triangles=[[remap[int(v)] for v in xyz(ts[i])] for i in tri_ids],
             normals=ns, uv0=uv, triangle_materials=mats, weights=weights, vertex_ids=vids, triangle_ids=tri_ids,
             bones=bone_rows, uv_sets=Q.get_num_uv_sets(dm))
    (SNAP / (key + '.json')).write_text(json.dumps(d, separators=(',', ':')))
    index[key] = dict(path=pk, sha=sha, skin_triangles=len(tri_ids)); index_file.write_text(json.dumps(index, indent=0))
    print('V9R_SNAPSHOT', pk, len(vids), len(tri_ids), flush=True)
    d = dm = ps = ts = asset = None; count += 1
    if count % 6 == 0: gc.collect(); u.SystemLibrary.collect_garbage()
print('V9R_SNAPSHOT_COMPLETE', len(index), flush=True)
