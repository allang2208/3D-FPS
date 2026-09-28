import json
from pathlib import Path
import unreal as u
root=Path(__file__).parent
L=u.MaterialEditingLibrary
r={'meshes':{},'materials':{}}
paths=['/Game/Props/RomanFountain20260917/SM_RomanFountain_WaterWaves','/Game/Props/GodSpaceLayout20260927/Meshes/SM_GodSpaceDistantOcean']
queue=[]
for path in paths:
    mesh=u.load_asset(path)
    mats=[s.get_editor_property('material_interface') for s in mesh.get_editor_property('static_materials')]
    r['meshes'][path]={'materials':[m.get_path_name() if m else None for m in mats],'bounds':str(mesh.get_bounding_box()),'nanite':str(mesh.get_editor_property('nanite_settings'))}
    queue.extend(m for m in mats if m)
while queue:
    mat=queue.pop()
    if mat.get_path_name() in r['materials']:continue
    d={'class':mat.get_class().get_name()}
    if isinstance(mat,u.MaterialInstanceConstant):
        parent=mat.get_editor_property('parent');queue.append(parent);d['parent']=parent.get_path_name()
        d['scalars']={str(n):L.get_material_instance_scalar_parameter_value(mat,n) for n in L.get_scalar_parameter_names(mat)}
        d['vectors']={str(n):str(L.get_material_instance_vector_parameter_value(mat,n)) for n in L.get_vector_parameter_names(mat)}
    if isinstance(mat,u.Material):
        d['expressions']=[]
        for node in L.get_material_expressions(mat):
            e={'class':node.get_class().get_name(),'name':node.get_name(),'desc':str(node.get_editor_property('desc'))}
            for p in ['code','parameter_name','default_value','texture']:
                try:e[p]=str(node.get_editor_property(p))
                except Exception:pass
            if isinstance(node,u.MaterialExpressionCustom):e['inputs']=[str(p.get_editor_property('input_name')) for p in node.get_editor_property('inputs')]
            d['expressions'].append(e)
    r['materials'][mat.get_path_name()]=d
(root/'Receipts/water-reuse-inputs.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print('REUSE_INPUTS_SAVED '+json.dumps(r['meshes']))
