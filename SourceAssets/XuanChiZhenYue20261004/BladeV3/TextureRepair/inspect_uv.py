import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/BladeV3/Meshes/SM_XuanChi_Blade_V3')
vertices,triangles,normals,uvs,tangents=u.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,0)
out={'vertices':[[float(p.x),float(p.y),float(p.z)] for p in vertices],
    'triangles':list(triangles),'uv':[[float(p.x),float(p.y)] for p in uvs]}
(P/'blade_imported_uv.json').write_text(json.dumps(out))
print('BLADE_UV_DIAG '+json.dumps({'vertices':len(vertices),'triangles':len(triangles)//3,
    'uv_count':len(uvs),'uv_min':[min(t.x for t in uvs),min(t.y for t in uvs)] if uvs else None,
    'uv_max':[max(t.x for t in uvs),max(t.y for t in uvs)] if uvs else None}))
