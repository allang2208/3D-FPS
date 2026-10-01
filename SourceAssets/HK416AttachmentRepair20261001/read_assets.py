import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;H='/Game/Weapons/HK416/Reworked20260930';D='/Game/Weapons/HK416/CommonAttachments20260930'
models=json.loads((O.parent/'HK416CommonAttachments20260930/models.json').read_text())
report={'meshes':{},'materials':{}}
def mat_info(m):
 if not m:return None
 path=m.get_path_name()
 if path in report['materials']:return path
 base=m.get_base_material();row={'class':m.get_class().get_name(),'base':base.get_path_name(),'properties':{},'expressions':[]}
 for prop in ('BASE_COLOR','ROUGHNESS','METALLIC','NORMAL','AMBIENT_OCCLUSION'):
  p=getattr(u.MaterialProperty,'MP_'+prop);n=u.MaterialEditingLibrary.get_material_property_input_node(base,p)
  row['properties'][prop]={'node':n.get_name() if n else None,'out':u.MaterialEditingLibrary.get_material_property_input_node_output_name(base,p)}
 for n in u.MaterialEditingLibrary.get_material_expressions(base):
  e={'name':n.get_name(),'class':n.get_class().get_name()}
  for field in ('texture','sampler_type','coordinate_index','u_tiling','v_tiling','default_value','parameter_name','code','r','constant','used_with_skeletal_mesh'):
   try:
    v=n.get_editor_property(field);e[field]=v.get_path_name() if isinstance(v,u.Object) else str(v)
   except Exception:pass
  row['expressions'].append(e)
 report['materials'][path]=row;return path
mesh=u.load_asset(H+'/SK_HK416_Manny');report['skeletal']={'path':mesh.get_path_name(),'slots':[{'name':str(s.material_slot_name),'material':mat_info(s.material_interface)} for s in mesh.materials]}
for key in models['parts']:
 mesh=u.load_asset(D+'/Meshes/SM_HK416_'+key)
 report['meshes'][key]={'slots':[{'name':str(s.material_slot_name),'material':mat_info(s.material_interface)} for s in mesh.static_materials]}
wet=u.load_asset(H+'/DA_HK416_WetMaterials');report['wet']={str(k):v.get_path_name() for k,v in wet.get_editor_property('wet_materials').items()}
(O/'actual_assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('HK416_CURRENT_ASSETS_READ',len(report['meshes']),len(report['materials']))
