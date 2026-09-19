import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;E=u.MaterialEditingLibrary
r={}
for key,path in [('m4','/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'),('akm','/Game/Weapons/AKMIntegration/SovietFab/StockV2/SK_AKM_MannyNative')]:
 mesh=u.load_asset(path);assert mesh;rows=[]
 for s in mesh.materials:
  m=s.material_interface
  if not m:continue
  row={'slot':str(s.material_slot_name),'material':m.get_path_name()};base=m
  while isinstance(base,u.MaterialInstanceConstant):base=base.parent
  row['parent']=base.get_path_name();row['textures']=[t.get_path_name() for t in E.get_used_textures(base)];row['outputs']={}
  for prop in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_METALLIC,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_NORMAL]:
   n=E.get_material_property_input_node(base,prop);row['outputs'][str(prop)]={'node':n.get_class().get_name() if n else None,'output':E.get_material_property_input_node_output_name(base,prop)}
  rows.append(row)
 r[key]=rows
(P/'current_materials.json').write_text(json.dumps(r,indent=2));u.log('STOCK_CURRENT_MATERIALS_PASS')
