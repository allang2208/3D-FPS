"""Inspect actual compiled RenderData bases, rather than trusting import warnings."""
import json
import math
from pathlib import Path
import unreal as u

root=Path('D:/FPS3D/FPSGAME/SourceAssets/CropsV3_20261022')
manifest=json.loads((root/'Source/variant_manifest.json').read_text())
rows=[]
for asset in manifest['assets']:
    mesh=u.load_asset('/Game/Props/Crops/V3/Meshes/SM_'+asset['id'])
    for lod in range(3):
        dynamic,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
            mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),
            u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=lod))
        assert dynamic.get_triangle_count()==mesh.get_num_triangles(lod)
        _,normal_list,valid_n,gaps_n=u.GeometryScript_Normals.get_mesh_per_vertex_normals(dynamic,False)
        _,tangent_list,bitangent_list,valid_t,gaps_t=u.GeometryScript_Normals.get_mesh_per_vertex_tangents(dynamic,False)
        assert valid_n and valid_t and not gaps_n and not gaps_t
        stats={}
        bad_vertex_ids=set()
        for name,values in [('normals',normal_list),('tangents',tangent_list),('bitangents',bitangent_list)]:
            vectors=u.GeometryScript_List.convert_vector_list_to_array(values)
            lengths=[math.sqrt(v.x*v.x+v.y*v.y+v.z*v.z) for v in vectors]
            bad_vertex_ids.update(i for i,v in enumerate(lengths) if v<1e-4 or not math.isfinite(v))
            stats[name]={'count':len(lengths),'nonfinite':sum(not math.isfinite(v) for v in lengths),
                         'near_zero':sum(v<1e-4 for v in lengths),'min_length':min(lengths)}
        bad_positions=[]
        for vertex_id in sorted(bad_vertex_ids):
            position,valid=u.GeometryScript_MeshQueries.get_vertex_position(dynamic,vertex_id)
            assert valid
            bad_positions.append([position.x,position.y,position.z])
        rows.append({'id':asset['id'],'lod':lod,'triangles':dynamic.get_triangle_count(),'basis':stats,
                     'invalid_vertices_cm':bad_positions})
    print('CROPS_RENDER_BASIS',asset['id'])
errors=[r for r in rows if any(s['nonfinite'] or s['near_zero'] for s in r['basis'].values())]
(root/'Receipts/ue-render-basis.json').write_text(json.dumps({'lods':rows,'errors':errors,
    'method':'Compiled RenderData copied with GeometryScript; all split render vertices inspected.',
    'gpu_rendered':False},indent=2))
print('CROPS_RENDER_BASIS_COMPLETE',len(rows),'errors',len(errors))
if errors:raise RuntimeError('Invalid compiled render bases; see ue-render-basis.json')
