"""Read current rear-grip material graphs only; no writes to UE assets."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;L=u.MaterialEditingLibrary;out={'meshes':{},'materials':{}}
paths=['/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10']+['/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_'+n+'_reargrip' for n in ['stable_antislip','balanced','phantom']]
for path in paths:
 a=u.load_asset(path);slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials;out['meshes'][path]={}
 for s in slots:
  name=str(s.material_slot_name)
  if isinstance(a,u.SkeletalMesh) and not ('FactoryRearGrip' in name or name=='M_LMG201_G43_EdgeCoat'):continue
  m=s.material_interface
  if m:out['meshes'][path][name]=m.get_path_name()
for path in {m for slots in out['meshes'].values() for m in slots.values()}:
 a=u.load_asset(path);m=a.get_base_material();r={'nodes':[],'outputs':{}};out['materials'][path]=r
 for p in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_ROUGHNESS]:
  n=L.get_material_property_input_node(m,p);r['outputs'][str(p)]=n.get_name() if n else None
 for n in L.get_material_expressions(m):
  d={'name':n.get_name(),'class':n.get_class().get_name()};r['nodes'].append(d)
  for key in ['parameter_name','default_value','description','code','texture','u_tiling','v_tiling','coordinate_index']:
   try:
    v=n.get_editor_property(key);d[key]=v.get_path_name() if isinstance(v,u.Object) else str(v)
   except Exception:pass
  try:d['input_nodes']=[x.get_name() if x else None for x in L.get_inputs_for_material_expression(m,n)]
  except Exception:pass
(O/'materials.json').write_text(json.dumps(out,indent=2));print('GRIP_JUNCTION_MATERIALS',len(out['materials']),flush=True)
