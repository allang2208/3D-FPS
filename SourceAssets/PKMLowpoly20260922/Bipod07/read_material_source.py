import unreal as u, json
from pathlib import Path
O=Path(__file__).parent
L=u.MaterialEditingLibrary
mesh=u.load_asset('/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny')
report={'mesh':mesh.get_path_name(),'slots':[],'materials':{}}
for slot in mesh.materials:
 m=slot.material_interface
 if not m:continue
 report['slots'].append({'slot':str(slot.material_slot_name),'material':m.get_path_name()})
 if m.get_path_name() in report['materials']:continue
 info={'class':m.get_class().get_name()}
 if isinstance(m,u.MaterialInstanceConstant):
  info['parent']=m.parent.get_path_name()
  info['scalar']={str(p.parameter_info.name):p.parameter_value for p in m.scalar_parameter_values}
  info['textures']={str(p.parameter_info.name):p.parameter_value.get_path_name() for p in m.texture_parameter_values if p.parameter_value}
  info['vectors']={str(p.parameter_info.name):str(p.parameter_value) for p in m.vector_parameter_values}
 else:
  info['textures']=[t.get_path_name() for t in L.get_used_textures(m)]
  info['inputs']={str(p):str(L.get_material_property_input_node(m,p)) for p in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_METALLIC,u.MaterialProperty.MP_NORMAL]}
 report['materials'][m.get_path_name()]=info
(O/'qbz_live_materials.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
