"""Probe GeometryScript return types for vertex positions (read-only)."""
import unreal as u

G = u.GeometryScript_AssetUtils
MQ = u.GeometryScript_MeshQueries

mesh = u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7.SK_SVD_BareArmsV7')
dm = u.DynamicMesh()
read, status = G.copy_mesh_from_skeletal_mesh(mesh, dm, u.GeometryScriptCopyMeshFromAssetOptions(),
                                              u.GeometryScriptMeshReadLOD())
print('STATUS', status, flush=True)
print('COUNT', MQ.get_vertex_count(dm), flush=True)
p = MQ.get_vertex_position(dm, 0)
print('TYPE', type(p), 'REPR', repr(p), flush=True)
allp = MQ.get_all_vertex_positions(dm)
print('ALL TYPE', type(allp), 'LEN', len(allp) if hasattr(allp, '__len__') else 'n/a', flush=True)
if hasattr(allp, '__len__') and len(allp):
    print('ALL[0]', type(allp[0]), repr(allp[0]), flush=True)
B = u.GeometryScript_BoneWeights
w = B.get_vertex_bone_weights(dm, 0)
print('W TYPE', type(w), 'LEN', len(w), 'REPR', repr(w)[:300], flush=True)
if len(w):
    print('W0', type(w[0]), repr(w[0]), [a for a in dir(w[0]) if not a.startswith('_')], flush=True)
_, bones = B.get_all_bones_info(dm)
print('BONE0', type(bones[0]), repr(bones[0]), flush=True)
print('PROBE_TYPES_DONE', flush=True)
