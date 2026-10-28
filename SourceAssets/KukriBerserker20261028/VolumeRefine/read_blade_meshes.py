import unreal as u,json
from pathlib import Path
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriBerserker20261028/VolumeRefine')
root=json.loads((P.parents[2]/'Content/ColdSteelData/kukri-modules.json').read_text('utf-8-sig'))
result=[]
for key,value in root['slots']['blade_1'].items():
    path=value.get('mesh')
    if not path:continue
    mesh=u.load_asset(path)
    vertices,triangles,normals,uvs,tangents=u.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,0)
    result.append({'id':key,'mesh':path,'vertices':[[v.x,v.y,v.z] for v in vertices],
        'triangles':list(triangles),'uvs':[[v.x,v.y] for v in uvs]})
(P/'runtime-blade-geometry.json').write_text(json.dumps(result),encoding='utf-8')
print('RUNTIME_BLADE_GEOMETRY',[(r['id'],len(r['vertices'])) for r in result])
