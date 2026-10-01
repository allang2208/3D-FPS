"""Dump the dominant bone of every ASH12 LOD0 vertex (read-only). Run through run_ue.ps1.

Writes inspect/geometry/<KEY>_bones.json: bone names by index and, per vertex in the
same order as the geometry dump of the same mesh state (dump_mesh_geometry.py key KEY),
the index of its largest-weight bone plus its full weights. Needed because parts bound to
non-root bones (magazine, bolt, trigger, sights) are stored in bind pose and render
elsewhere at runtime. The first dump (surface install state) is ASH12_bones.json.
"""
import json
from pathlib import Path
import unreal as u

KEY = 'SVD'
AU, Q, LU, BW = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries, u.GeometryScript_List, u.GeometryScript_BoneWeights
OUT = Path(u.Paths.project_dir()).resolve() / 'SourceAssets' / 'WeaponSurface20260930' / 'SVD' / 'Input' / (KEY + '_bones.json')


def pick(result, cls):
    if isinstance(result, tuple):
        for item in result:
            if isinstance(item, cls):
                return item
        raise RuntimeError('No %s in result' % cls.__name__)
    return result


mesh = u.load_asset('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
dm = u.DynamicMesh()
lod = u.GeometryScriptMeshReadLOD()
lod.set_editor_property('lod_type', u.GeometryScriptLODType.SOURCE_MODEL)
AU.copy_mesh_from_skeletal_mesh(mesh, dm, u.GeometryScriptCopyMeshFromAssetOptions(), lod)
if Q.get_has_vertex_id_gaps(dm):
    raise RuntimeError('vertex id gaps; order would not match the geometry dump')
info = next(x for x in BW.get_all_bones_info(dm) if isinstance(x, (list, u.Array)))
names = [''] * len(info)
for b in info:
    names[b.index] = str(b.name)
v_ids = LU.convert_index_list_to_array(pick(Q.get_all_vertex_i_ds(dm), u.GeometryScriptIndexList))
dominant, weights = [], []
for v in v_ids:
    r = BW.get_vertex_bone_weights(dm, v)
    ws = next((x for x in r if isinstance(x, (list, u.Array))), []) if isinstance(r, tuple) else []
    pairs = sorted(((int(w.bone_index), round(float(w.weight), 5)) for w in ws), key=lambda x: -x[1])
    dominant.append(pairs[0][0] if pairs else -1)
    weights.append(pairs)
OUT.write_text(json.dumps({'bones': names, 'dominant': dominant, 'weights': weights,
                           'vertices': len(v_ids)}), encoding='utf-8')
print('SVD_BONES_WRITTEN', len(dominant), len(names), flush=True)
