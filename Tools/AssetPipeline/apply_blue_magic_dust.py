"""Blue powder and mineral grains; preserve the glass, lid and baked surface detail."""
import unreal,json
from pathlib import Path
L=unreal.MaterialEditingLibrary
D='/Game/Items/EnhancementMaterials/magic_dust'
mesh=unreal.load_asset(D+'/SM_magic_dust');assert mesh
changes={}
for suffix,base_index,slot_prefix in [('powder',3,'Fine_silver_mineral_powder'),('grains',1,'Pale_blue_mineral_grains')]:
 name='M_magic_dust_blue_'+suffix
 m=unreal.load_asset(D+'/'+name)
 if not m:m=unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,D,unreal.load_asset(D+'/M_magic_dust_'+str(base_index)))
 for n in list(L.get_material_expressions(m)):
  if str(n.get_editor_property('desc')).startswith('BlueDust:'):L.delete_material_expression(m,n)
 def constant(label,value,prop):
  n=L.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);n.constant=unreal.LinearColor(*value,1);n.set_editor_property('desc','BlueDust: '+label)
  assert L.connect_material_property(n,'',prop)
 if suffix=='powder':
  source=next(n for n in L.get_material_expressions(m) if isinstance(n,unreal.MaterialExpressionTextureSample) and n.texture and n.texture.get_name().endswith('_Base_Color'))
  n=L.create_material_expression(m,unreal.MaterialExpressionCustom);n.set_editor_property('desc','BlueDust: textured powder')
  n.set_editor_property('code','float l=dot(C,float3(0.2126,0.7152,0.0722)); return float3(0.025,0.24,0.95)*max(l*1.65,0.025);')
  n.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
  i=unreal.CustomInput();i.set_editor_property('input_name','C');n.set_editor_property('inputs',[i])
  assert L.connect_material_expressions(source,'RGB',n,'C')
  assert L.connect_material_property(n,'',unreal.MaterialProperty.MP_BASE_COLOR)
  constant('soft blue glow',(.004,.022,.065),unreal.MaterialProperty.MP_EMISSIVE_COLOR)
 else:
  constant('ice blue grains',(.10,.43,.95),unreal.MaterialProperty.MP_BASE_COLOR)
  constant('grain glow',(.01,.05,.14),unreal.MaterialProperty.MP_EMISSIVE_COLOR)
 constant('nonmetallic mineral',(.02,.02,.02),unreal.MaterialProperty.MP_METALLIC)
 L.recompile_material(m);unreal.EditorAssetLibrary.save_loaded_asset(m)
 slots=[i for i,s in enumerate(mesh.static_materials) if str(s.material_slot_name).startswith(slot_prefix)]
 assert len(slots)==1,(slot_prefix,slots)
 mesh.set_material(slots[0],m);changes[str(slots[0])]=m.get_path_name()
unreal.EditorAssetLibrary.save_loaded_asset(mesh)
Path('D:/FPS3D/FPSGAME/Saved/BlueMagicDustMaterial.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'changed_slots':changes,'preserved':['glass','lid','normal','roughness','geometry','collision']},indent=2))
unreal.log('BLUE_MAGIC_DUST_MATERIAL_PASS')
