"""Dump the available GeometryScript helpers for triangle counts (read-only)."""
import unreal as u

G = u.GeometryScript_AssetUtils
MQ = u.GeometryScript_MeshQueries
GM = u.GeometryScript_Materials

mesh = u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7.SK_SVD_BareArmsV7')
dm = u.DynamicMesh()
G.copy_mesh_from_skeletal_mesh(mesh, dm, u.GeometryScriptCopyMeshFromAssetOptions(),
                               u.GeometryScriptMeshReadLOD())
print('MQ', sorted(n for n in dir(MQ) if not n.startswith('_')))
print('GM', sorted(n for n in dir(GM) if not n.startswith('_')))
print('DM', sorted(n for n in dir(dm) if 'tri' in n.lower() or 'poly' in n.lower() or 'vert' in n.lower()))
print('API_DUMP_DONE', flush=True)
