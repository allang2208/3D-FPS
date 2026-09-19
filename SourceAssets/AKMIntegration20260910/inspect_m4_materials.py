import unreal,json
from pathlib import Path
O=Path(__file__).parent
m=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
rows=[]
for slot in m.get_editor_property('materials'):
 mat=slot.material_interface;row={'slot':str(slot.material_slot_name),'material':mat.get_path_name(),'class':mat.get_class().get_name()}
 if isinstance(mat,unreal.MaterialInstance):
  row['parent']=mat.get_editor_property('parent').get_path_name()
  row['textures']=[{'name':str(p.parameter_info.name),'value':p.parameter_value.get_path_name() if p.parameter_value else None} for p in mat.get_editor_property('texture_parameter_values')]
 rows.append(row)
(O/'m4_materials.json').write_text(json.dumps(rows,indent=2))
