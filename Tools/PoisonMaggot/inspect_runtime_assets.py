import unreal,json
from pathlib import Path
mel=unreal.MaterialEditingLibrary;out={}
for name in ['M_PoisonMaggot_Skin','M_PoisonMaggot_Venom','M_AuditGround']:
 m=unreal.load_asset('/Game/Monsters/PoisonMaggot/Materials/'+name);r={}
 for prop in [p for p in unreal.MaterialProperty if 'FRONT' in str(p) or 'BASE_COLOR' in str(p) or 'OPACITY' in str(p)]:
  n=mel.get_material_property_input_node(m,prop);r[str(prop)]=str(n)
  if n:r[str(prop)+'_inputs']=str(mel.get_material_expression_input_names(n))
 r['expressions']=[str(x) for x in unreal.get_objects_with_outer(m,False)] if hasattr(unreal,'get_objects_with_outer') else []
 out[name]=r
mesh=unreal.load_asset('/Game/Monsters/PoisonMaggot/SK_PoisonMaggot');out['mesh_materials']=[str(s.material_interface) for s in mesh.materials]
Path('D:/FPS3D/FPSGAME/Saved/PoisonMaggot/runtime_assets.json').write_text(json.dumps(out,indent=2));unreal.log('MAGGOT_ASSET_DIAG '+json.dumps(out))
