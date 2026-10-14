import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;L=u.MaterialEditingLibrary
C=json.loads((O/'Input/current.json').read_text());F=json.loads((O/'Input/factory.json').read_text())
paths={k:v['materials'][0] for k,v in C.items()}
paths['factory']=next(v['path'] for k,v in F['factory_materials'].items() if 'Interior' not in k)
out={}
for kind,path in paths.items():
 base=u.load_asset(path).get_base_material();row={'base':base.get_path_name(),'properties':{},'custom':[]}
 for prop in ('MP_AMBIENT_OCCLUSION','MP_NORMAL','MP_BASE_COLOR','MP_ROUGHNESS'):
  e=getattr(u.MaterialProperty,prop);n=L.get_material_property_input_node(base,e)
  row['properties'][prop]={'node':n.get_name() if n else None,'class':n.get_class().get_name() if n else None,'output':L.get_material_property_input_node_output_name(base,e)}
 for n in L.get_material_expressions(base):
  if isinstance(n,u.MaterialExpressionCustom):
   inputs=[]
   for pin in n.get_editor_property('inputs'):
    inputs.append({'name':str(pin.get_editor_property('input_name'))})
   row.setdefault('coordinates',[])
   row['custom'].append({'name':n.get_name(),'description':str(n.get_editor_property('description')),'code':n.get_editor_property('code'),'inputs':inputs})
 row['coordinates']=[{'node':n.get_name(),'channel':n.get_editor_property('coordinate_index')} for n in L.get_material_expressions(base) if isinstance(n,u.MaterialExpressionTextureCoordinate)]
 out[kind]=row
(O/'Input/material_graph.json').write_text(json.dumps(out,indent=2))
print('JUNCTION_MATERIAL_READ',flush=True)
