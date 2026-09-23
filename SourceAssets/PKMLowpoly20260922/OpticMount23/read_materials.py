import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/PKMLowpoly20260922';L=u.MaterialEditingLibrary
report={'meshes':{},'materials':{}}
paths=[P+'/Accessories14/SK_PKM_Manny_Modular',P+'/Accessories14/Meshes/SM_PKM_optic_rail']
for path in paths:
 mesh=u.load_asset(path);slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
 report['meshes'][path]=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in slots]
 for s in slots:
  if 'Body' not in str(s.material_slot_name) and 'Interface' not in str(s.material_slot_name):continue
  m=s.material_interface.get_base_material();mp=m.get_path_name()
  if mp in report['materials']:continue
  data={'outputs':{},'nodes':[]}
  for name in ['BASE_COLOR','ROUGHNESS','METALLIC','NORMAL','AMBIENT_OCCLUSION']:
   prop=getattr(u.MaterialProperty,'MP_'+name);n=L.get_material_property_input_node(m,prop)
   data['outputs'][name]=[n.get_name(),L.get_material_property_input_node_output_name(m,prop)] if n else None
  for n in L.get_material_expressions(m):
   row={'name':n.get_name(),'class':n.get_class().get_name(),'inputs':[v.get_name() if v else None for v in L.get_inputs_for_material_expression(m,n)]}
   for key in ['texture','coordinate_index','r','constant','parameter_name','description','code']:
    try:
     v=n.get_editor_property(key);row[key]=v.get_path_name() if isinstance(v,u.Object) else str(v)
    except Exception:pass
   data['nodes'].append(row)
  report['materials'][mp]=data
table=u.load_asset(P+'/Finish20/DA_PKM_WetMaterials')
report['wet_mapping']={str(k):v.get_path_name() for k,v in table.get_editor_property('wet_materials').items() if v}
(O/'materials_before.json').write_text(json.dumps(report,indent=2))
print('PKM23_MATERIALS_READ '+str(len(report['materials'])))
