"""Wire the authored PBR inputs into UE 5.8's active Substrate surface output."""
import unreal

def connect_surface(material, skin=False):
 mel=unreal.MaterialEditingLibrary
 front=mel.get_material_property_input_node(material,unreal.MaterialProperty.MP_FRONT_MATERIAL)
 if front:mel.delete_material_expression(material,front)
 node=mel.create_material_expression(material,unreal.MaterialExpressionSubstrateShadingModels)
 # The source's dark mouth and legs need the measured albedo preserved. The
 # full-volume subsurface shading model washed them into the pale tissue color.
 node.set_editor_property('shading_model_override',unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
 for prop,pin,out in [
  (unreal.MaterialProperty.MP_BASE_COLOR,'BaseColor','RGB'),
  (unreal.MaterialProperty.MP_NORMAL,'Normal','RGB'),
  (unreal.MaterialProperty.MP_ROUGHNESS,'Roughness','R'),
  (unreal.MaterialProperty.MP_SPECULAR,'Specular',''),
  (unreal.MaterialProperty.MP_EMISSIVE_COLOR,'Emissive Color','')]:
  source=mel.get_material_property_input_node(material,prop)
  if source:
   output=out if isinstance(source,unreal.MaterialExpressionTextureSample) else ''
   assert mel.connect_material_expressions(source,output,node,pin),(material.get_name(),pin)
 assert mel.connect_material_property(node,'',unreal.MaterialProperty.MP_FRONT_MATERIAL)
 errors=mel.recompile_material(material)
 assert not errors,(material.get_name(),list(errors))
 unreal.EditorAssetLibrary.save_loaded_asset(material,False)

if __name__=='__main__':
 for name in ['M_PoisonMaggot_Skin','M_PoisonMaggot_Venom','M_AuditGround']:
  connect_surface(unreal.load_asset('/Game/Monsters/PoisonMaggot/Materials/'+name),name.endswith('_Skin'))
 unreal.log('MAGGOT_SUBSTRATE_COMPLETE')
