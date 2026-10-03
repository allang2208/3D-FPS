import json
from pathlib import Path
import unreal as u
root=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonPlayer20261003')
for key in ('NativeSkin','Jason','ue_field_gloves_skin','ue_field_sweater','ue_field_sweater_charcoal','ue_chainmail_shirt'):
    path=root/(key+'.json');d=json.loads(path.read_text())
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(u.load_asset(d['source']),u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    mids=[]
    for i in range(len(d['triangles'])):
        result=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
        mids.append(int(result[0] if isinstance(result,tuple) else result))
    d['triangle_materials']=mids;path.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
print('JASON_REGION_INPUTS_SAVED')
