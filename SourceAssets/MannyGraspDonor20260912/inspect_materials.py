import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
report={}
for p in ['/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416','/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative']:
 mesh=u.load_asset(p);rows=[]
 for slot in mesh.materials:
  mat=slot.material_interface
  row={'slot':str(slot.material_slot_name),'material':mat.get_path_name() if mat else None}
  if mat:
   row['base']=mat.get_base_material().get_path_name()
   if isinstance(mat,u.MaterialInstanceConstant):
    row['textures']=[str(x) for x in mat.get_editor_property('texture_parameter_values')]
  rows.append(row)
 report[p]=rows
(O/'material_readback.json').write_text(json.dumps(report,indent=2));u.log('MATERIAL_READBACK '+json.dumps(report))
