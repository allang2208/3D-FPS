import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;root='/Game/Weapons/CommonHK41620260930/Meshes/SM_'
result={'meshes':{},'materials':{}}
for family in ('HK416','Common','M16','M1911','G18','DW715'):
 mesh=u.load_asset(root+family+'_eoth_holographic')
 result['meshes'][family]=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.static_materials]
 for s in mesh.static_materials:
  if not any(k in str(s.material_slot_name) for k in ('Reticle','Glass')):continue
  m=s.material_interface
  if not m or m.get_path_name() in result['materials']:continue
  m=m.get_base_material();row={'props':{},'expressions':[]}
  for p in ('blend_mode','shading_model','two_sided','disable_depth_test','translucency_pass','enable_responsive_aa'):
   try:row['props'][p]=str(m.get_editor_property(p))
   except Exception:pass
  for n in u.MaterialEditingLibrary.get_material_expressions(m):
   r={'class':n.get_class().get_name()}
   for p in ('texture','coordinate_index','code','r','constant','default_value'):
    try:
     v=n.get_editor_property(p);r[p]=v.get_path_name() if isinstance(v,u.Object) else str(v)
    except Exception:pass
   row['expressions'].append(r)
  result['materials'][m.get_path_name()]=row
(O/'current_materials.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('EOTH_MATERIAL_INPUTS_READ')
