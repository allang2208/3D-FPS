import unreal,json
from pathlib import Path
lib=unreal.EditorAssetLibrary;mel=unreal.MaterialEditingLibrary
out={}
for name in ['M_PoisonMaggot_Skin','M_PoisonMaggot_Venom']:
 m=unreal.load_asset('/Game/Monsters/PoisonMaggot/Materials/'+name);r={}
 for prop in [unreal.MaterialProperty.MP_BASE_COLOR,unreal.MaterialProperty.MP_NORMAL,unreal.MaterialProperty.MP_ROUGHNESS]:
  n=mel.get_material_property_input_node(m,prop);r[str(prop)]=str(n)
  if n and isinstance(n,unreal.MaterialExpressionTextureSample):r[str(prop)+'_texture']=str(n.texture)
  if n and isinstance(n,unreal.MaterialExpressionConstant3Vector):r[str(prop)+'_constant']=str(n.constant)
 out[name]=r
Path('D:/FPS3D/FPSGAME/Saved/PoisonMaggot/material_inspection.json').write_text(json.dumps(out,indent=2));unreal.log('MAGGOT_MATERIAL_INSPECTION '+json.dumps(out))
