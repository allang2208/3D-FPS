import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;S=O.parents[1]
src=json.loads((S/'A762Meshy20260920/Accessories05/sources.json').read_text())
src['meshes'].pop('drum',None)
L=u.MaterialEditingLibrary
materials={}
for key,info in src['meshes'].items():
 a=u.load_asset(info['asset'])
 if not a:raise RuntimeError(info['asset'])
 info['source']=list(a.get_editor_property('asset_import_data').extract_filenames())
 info['materials']=[{'slot':str(m.material_slot_name),'path':m.material_interface.get_path_name()} for m in a.static_materials]
 for slot in info['materials']:
  m=u.load_asset(slot['path']);base=m.get_base_material()
  if base.get_path_name() in materials:continue
  record={'class':m.get_class().get_name(),'base':base.get_path_name(),'outputs':{},'nodes':[]}
  for name in ['BASE_COLOR','ROUGHNESS','METALLIC','SPECULAR','NORMAL','AMBIENT_OCCLUSION','EMISSIVE_COLOR']:
   p=getattr(u.MaterialProperty,'MP_'+name);n=L.get_material_property_input_node(base,p)
   record['outputs'][name]=n.get_name() if n else None
  for n in L.get_material_expressions(base):
   row={'name':n.get_name(),'class':n.get_class().get_name(),'inputs':[x.get_name() if x else None for x in L.get_inputs_for_material_expression(base,n)]}
   for p in ['parameter_name','texture','desc','coordinate_index','material_function']:
    try:
     v=n.get_editor_property(p);row[p]=v.get_path_name() if hasattr(v,'get_path_name') else str(v)
    except Exception:pass
   record['nodes'].append(row)
  materials[base.get_path_name()]=record
mesh=u.load_asset('/Game/Weapons/PKMLowpoly20260922/SK_PKM_Manny')
src['pkm_materials']={str(m.material_slot_name):m.material_interface.get_path_name() for m in mesh.materials}
src['material_graphs']=materials
(O/'sources.json').write_text(json.dumps(src,indent=2),encoding='utf-8')
print('PKM14_SOURCES_READY',len(src['meshes']))
