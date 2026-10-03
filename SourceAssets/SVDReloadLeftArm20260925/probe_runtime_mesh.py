"""Read-only probe: dump the runtime SVD viewmodel mesh (geometry, weights, materials).

No asset is modified or saved. The dump is compared offline against the authoring
JSON so a baked-bare-arm regression can be told apart from an animation problem.
"""
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
OUT = PROJECT / 'SourceAssets/SVDReloadLeftArm20260925/runtime'
OUT.mkdir(parents=True, exist_ok=True)

G = u.GeometryScript_AssetUtils
B = u.GeometryScript_BoneWeights
MQ = u.GeometryScript_MeshQueries
GM = u.GeometryScript_Materials

TARGETS = {
    'svd_modular_stock': '/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock.SK_SVD_ModularStock',
    'svd_gloved_source': '/Game/Characters/ModularOutfit20260924/BarePalmV7/OriginalSources/SK_SVD_GlovedSource.SK_SVD_GlovedSource',
    'svd_bare_arms_v7': '/Game/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7.SK_SVD_BareArmsV7',
    'm4_viewmodel': '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.SK_M4_FoldingSights_HK416',
}


def vec(p):
    return [round(float(p.x), 5), round(float(p.y), 5), round(float(p.z), 5)]


def first_iterable(result):
    """GeometryScript functions return (out_value, bool) tuples or bare lists."""
    candidates = list(result) if isinstance(result, tuple) else [result]
    for item in candidates:
        if not isinstance(item, (bool, int, float)) and hasattr(item, '__iter__'):
            return item
    return []


def pairs_of(result):
    out = []
    for q in first_iterable(result):
        if hasattr(q, 'bone_index'):
            out.append((int(q.bone_index), float(q.weight)))
        else:
            out.append((int(q[0]), float(q[1])))
    return out


for key, path in TARGETS.items():
    mesh = u.load_asset(path)
    if not mesh:
        print('MISSING', key, path, flush=True)
        continue
    dm = u.DynamicMesh()
    read, status = G.copy_mesh_from_skeletal_mesh(
        mesh, dm, u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        print('READ_FAIL', key, status, flush=True)
        continue
    _, bones = B.get_all_bones_info(dm)
    names = [str(b.name) for b in bones]
    count = MQ.get_vertex_count(dm)
    positions = []
    weights = []
    for vid in range(count):
        p = MQ.get_vertex_position(dm, vid)
        positions.append(vec(p[0]))
        pairs = pairs_of(B.get_vertex_bone_weights(dm, vid))
        weights.append([[names[i], round(w, 5)] for i, w in pairs])
    tri_materials = [int(v) for v in first_iterable(GM.get_all_triangle_material_i_ds(dm))]
    tri_count = len(tri_materials)
    slots = [str(s.material_slot_name) for s in mesh.materials]
    data = dict(key=key, path=path,
                skeleton=mesh.skeleton.get_path_name() if mesh.skeleton else '',
                slots=slots, bones=names, positions=positions, weights=weights,
                triangle_materials=tri_materials)
    (OUT / f'{key}.json').write_text(json.dumps(data))
    print('RUNTIME_MESH', key, 'verts', count, 'tris', tri_count, 'slots', slots, flush=True)
print('RUNTIME_PROBE_DONE', flush=True)
