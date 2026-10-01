import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;L=u.MaterialEditingLibrary
paths={k:v['path'] for k,v in json.loads((O/'Input'/'materials.json').read_text()).items()}
out={'meshes':{},'materials':{}}
for key,path in paths.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing current SVD mesh '+path)
 skeletal=isinstance(mesh,u.SkeletalMesh);slots=mesh.get_editor_property('materials' if skeletal else 'static_materials')
 out['meshes'][key]={'asset':path,'skeletal':skeletal,'source':list(mesh.get_editor_property('asset_import_data').extract_filenames()),
 'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]}
 for s in slots:
  m=s.material_interface
  if not m or m.get_path_name() in out['materials']:continue
  base=m.get_base_material();custom=[];parameters={}
  for n in L.get_material_expressions(base):
   if isinstance(n,u.MaterialExpressionCustom):custom.append({'name':n.get_name(),'description':str(n.get_editor_property('description')),'inputs':[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')], 'code':str(n.get_editor_property('code'))})
  for kind in ['scalar','vector','texture']:
   parameters[kind]={}
   for name in getattr(L,'get_'+kind+'_parameter_names')(base):
    v=getattr(L,'get_material_instance_'+kind+'_parameter_value')(m,name) if isinstance(m,u.MaterialInstanceConstant) else getattr(L,'get_material_default_'+kind+'_parameter_value')(base,name)
    parameters[kind][str(name)]=v.get_path_name() if kind=='texture' and v else [v.r,v.g,v.b,v.a] if kind=='vector' else v
  out['materials'][m.get_path_name()]={'base':base.get_path_name(),'blend':str(base.blend_mode),'custom':custom,'parameters':parameters}

(O/'Input'/'effective.json').write_text(json.dumps(out,indent=1))
print('SVD_SOURCE_GRAPHS_READ',len(out['materials']),flush=True)
