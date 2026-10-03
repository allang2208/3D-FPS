"""Extract original face surface inputs to identify the reported material mismatch."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonFaceRepair20261003')
for name in ['T_Jason_head','T_Head_LOD2_N','T_Head_SRMF']:
    tex=u.load_asset('/Game/AsianMale_Jason/Texture/'+name)
    task=u.AssetExportTask();task.object=tex;task.filename=str(ROOT/(name+'.png'))
    task.exporter=u.TextureExporterPNG();task.automated=True;task.prompt=False;task.replace_identical=True
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Texture export failed: '+name)
Q=u.GeometryScript_MeshQueries
for name,source,mat in [('head','/Game/AsianMale_Jason/Mesh/Head/SKM_Jason_head',0),
                        ('body_face','/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body',1)]:
    mesh=u.load_asset(source)
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,plist,_=Q.get_all_vertex_positions(dm,False)
    positions=u.GeometryScript_List.convert_vector_list_to_array(plist)
    _,tlist,_=Q.get_all_triangle_indices(dm,False)
    triangles=u.GeometryScript_List.convert_triangle_list_to_array(tlist)
    samples=[]
    for ti,t in enumerate(triangles):
        material,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
        if not valid or material!=mat:continue
        uv1,uv2,uv3,ok=Q.get_triangle_u_vs(dm,0,ti)
        if not ok:raise RuntimeError('Missing UV')
        for vi,uv in zip([t.x,t.y,t.z],[uv1,uv2,uv3]):
            p=positions[vi];samples.append([p.x,p.y,p.z,uv.x,uv.y])
    (ROOT/(name+'_uv.json')).write_text(json.dumps(samples,separators=(',',':')))
    print(name+' UV samples: '+str(len(samples)))
print('JASON_FACE_SURFACE_EXTRACTED')
