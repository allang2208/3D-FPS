import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent;L=u.MaterialEditingLibrary
inputs=json.loads((O/'inputs.json').read_text());out={}
for path in inputs['materials']:
 if any(x in path for x in ('Arms','Glove','Sleeve')):continue
 m=u.load_asset(path);base=m.get_base_material();row={'parameters':{},'codes':[]}
 for kind in ('scalar','vector','texture'):
  values={}
  for name in getattr(L,'get_'+kind+'_parameter_names')(base):
   v=getattr(L,'get_material_instance_'+kind+'_parameter_value')(m,name)
   values[str(name)]=v.get_path_name() if isinstance(v,u.Object) else [v.r,v.g,v.b,v.a] if isinstance(v,u.LinearColor) else v
  row['parameters'][kind]=values
 for n in L.get_material_expressions(base):
  if isinstance(n,u.MaterialExpressionCustom):row['codes'].append({'description':str(n.get_editor_property('description')),'code':n.get_editor_property('code')})
 out[path]=row
(O/'material_sources.json').write_text(json.dumps(out,indent=2))
print('M24_MATERIAL_SOURCES_READ',len(out),flush=True)
