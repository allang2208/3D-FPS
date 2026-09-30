"""Read-only: dump runtime mesh geometry (reference pose) through Geometry Script.

Skeletal FBX export asserts in a render-less commandlet, so the exact runtime LOD0
source model is read here instead. For each mesh writes inspect/geometry/<Key>.bin:
  header JSON line, then little-endian arrays:
    positions  float32 [V,3]  cm, mesh/component space
    triangles  int32   [T,3]
    material   int32   [T]    slot index
    uv0        float32 [T,3,2] per corner (UE convention: V down)
    normals    float32 [T,3,3] per corner (split normals)
No asset is modified or saved.
"""
import array
import json
import sys
import unreal as u
from pathlib import Path

O = Path(__file__).parent
OUT = O / 'inspect' / 'geometry'
OUT.mkdir(parents=True, exist_ok=True)
MESHES = {
    'M4': '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
    'AKM': '/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
    'HK416': '/Game/Weapons/HK416/Reworked20260930/SK_HK416_Manny',
    'A762': '/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
    'A762_RearSight': '/Game/Weapons/A762/Accessories05/Meshes/SM_A762_RearSight',
    'A762_FrontSight': '/Game/Weapons/A762/Accessories05/Meshes/SM_A762_FrontSight',
    # State after the surface-standard install, compared against the A762 dump taken before it.
    'A762_AfterSurface': '/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
    # After the magwell repair (repair_a762_mesh.py).
    'A762_AfterRepair': '/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
    # After denoise / magazine subdivision / bevels / rivets (apply_a762_geometry.py).
    'A762_Geometry': '/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
}
# A762 accessories (item 2 masks), keyed ACC_<mesh name without SM_A762_>.
for _acc in ('angled', 'balanced_reargrip', 'brake', 'canted', 'core_stock', 'drum', 'ext_mag', 'flashlight',
             'holographic', 'laser', 'lpvo_1_6x', 'lpvo_ring', 'panoramic_red_dot', 'phantom_reargrip', 'prism',
             'prism_scope_2x', 'qr_performance', 'skeleton', 'stable_antislip_reargrip', 'suppressor',
             'tactical_suppressor', 'tactical_telescopic', 'tactical_vertical', 'titanium_brake', 'vertical'):
    MESHES['ACC_' + _acc] = '/Game/Weapons/A762/Accessories05/Meshes/SM_A762_' + _acc
only = [a for a in sys.argv[1:] if a in MESHES]
AU, Q, LU, MAT = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries, u.GeometryScript_List, u.GeometryScript_Materials


def pick(result, cls):
    if isinstance(result, tuple):
        for item in result:
            if isinstance(item, cls):
                return item
        raise RuntimeError('No %s in %s' % (cls.__name__, [type(x).__name__ for x in result]))
    return result


summary = {}
for key, path in MESHES.items():
    if only and key not in only:
        continue
    target = OUT / (key + '.bin')
    if target.exists():
        continue
    mesh = u.load_asset(path)
    dm = u.DynamicMesh()
    opts = u.GeometryScriptCopyMeshFromAssetOptions()
    lod = u.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', u.GeometryScriptLODType.SOURCE_MODEL)
    lod.set_editor_property('lod_index', 0)
    if isinstance(mesh, u.SkeletalMesh):
        AU.copy_mesh_from_skeletal_mesh(mesh, dm, opts, lod)
        slots = [str(s.material_slot_name) for s in mesh.get_editor_property('materials')]
        mats = [s.material_interface.get_path_name() if s.material_interface else None for s in mesh.get_editor_property('materials')]
    else:
        AU.copy_mesh_from_static_mesh(mesh, dm, opts, lod)
        slots = [str(s.material_slot_name) for s in mesh.get_editor_property('static_materials')]
        mats = [s.material_interface.get_path_name() if s.material_interface else None for s in mesh.get_editor_property('static_materials')]
    compact = not Q.get_has_triangle_id_gaps(dm)
    positions = LU.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm, True), u.GeometryScriptVectorList))
    tris = LU.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm, True), u.GeometryScriptTriangleList))
    ids = LU.convert_index_list_to_array(pick(MAT.get_all_triangle_material_i_ds(dm), u.GeometryScriptIndexList))
    tri_ids = LU.convert_index_list_to_array(pick(Q.get_all_triangle_i_ds(dm), u.GeometryScriptIndexList))
    pos = array.array('f')
    for p in positions:
        pos.extend((p.x, p.y, p.z))
    ind = array.array('i')
    for t in tris:
        ind.extend((t.x, t.y, t.z))
    mid = array.array('i', [int(i) for i in ids][:len(tris)] if compact else [int(ids[t]) for t in tri_ids])
    uvs = array.array('f')
    nrm = array.array('f')
    for t in tri_ids:
        r = Q.get_triangle_u_vs(dm, 0, t)
        a, b, c = r[0], r[1], r[2]
        uvs.extend((a.x, a.y, b.x, b.y, c.x, c.y))
        n = Q.get_triangle_normals(dm, t)
        vecs = [x for x in n if isinstance(x, u.Vector)]
        for v in vecs[:3]:
            nrm.extend((v.x, v.y, v.z))
    header = {'key': key, 'path': mesh.get_path_name(), 'slots': slots, 'materials': mats,
              'vertices': len(positions), 'triangles': len(tris), 'compact': compact}
    with open(target, 'wb') as f:
        f.write((json.dumps(header) + '\n').encode('utf-8'))
        for arr in (pos, ind, mid, uvs, nrm):
            arr.tofile(f)
    summary[key] = [header['vertices'], header['triangles'], len(uvs) // 6, len(nrm) // 9]
    print('WEAPON_SURFACE_GEOMETRY', key, summary[key], flush=True)
print('WEAPON_SURFACE_GEOMETRY_DONE', json.dumps(summary), flush=True)
