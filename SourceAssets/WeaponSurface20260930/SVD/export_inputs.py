import array
import json
import sys
import unreal as u
from pathlib import Path

O = Path(__file__).parent
OUT = O / 'Input'
OUT.mkdir(parents=True, exist_ok=True)
MESHES={'SVD':'/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock'}
for key in ('vertical','tactical_vertical','canted','prism','angled','holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring','optic_bridge','suppressor','tactical_suppressor','brake','titanium_brake','flashlight','laser'):
 MESHES[key]='/Game/Weapons/SVDDragunov20260922/Accessories20260923/Meshes/SM_SVD_'+key
for key in ('skeleton','core_stock','qr_performance','tactical_telescopic'):
 MESHES[key]='/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/Meshes/SM_SVD_'+key
MESHES['ext_mag']='/Game/Weapons/SVDDragunov20260922/ExtendedMagazine20260927/SM_SVD_ext_mag'
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
              'vertices': len(positions), 'triangles': len(tris), 'compact': compact, 'uv_sets': Q.get_num_uv_sets(dm)}
    with open(target, 'wb') as f:
        f.write((json.dumps(header) + '\n').encode('utf-8'))
        for arr in (pos, ind, mid, uvs, nrm):
            arr.tofile(f)
    summary[key] = [header['vertices'], header['triangles'], len(uvs) // 6, len(nrm) // 9]
    print('WEAPON_SURFACE_GEOMETRY', key, summary[key], flush=True)
print('WEAPON_SURFACE_GEOMETRY_DONE', json.dumps(summary), flush=True)

# Material identities are input to the production plan; no asset edits.
ns={'__file__': str(O.parent/'A762'/'inspect_accessories.py')}
source=(O.parent/'A762'/'inspect_accessories.py').read_text(encoding='utf-8')
exec(source[:source.index('out = {}')],ns)
materials={}
for key,path in MESHES.items():
    mesh=u.load_asset(path)
    prop='materials' if isinstance(mesh,u.SkeletalMesh) else 'static_materials'
    materials[key]={'path':path,'slots':[{'slot':str(s.material_slot_name),'material':ns['describe'](s.material_interface)} for s in mesh.get_editor_property(prop)]}
(O/'Input'/'materials.json').write_text(json.dumps(materials,indent=1),encoding='utf-8')
print('SVD_SURFACE_INPUT_READY',len(materials),flush=True)
