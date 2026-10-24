from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV3'
def install_screens():
 L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
 for key in ('OfficeUI','WorkoutUI'):
  task=u.AssetImportTask();task.filename=str(ROOT/'Textures'/('T_AP_'+key+'.png'))
  task.destination_path=BASE+'/Textures';task.destination_name='T_AP_'+key
  task.automated=True;task.replace_existing=True;task.save=False
  A.import_asset_tasks([task]);tex=u.load_asset(BASE+'/Textures/T_AP_'+key)
  tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
  tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',False)
  tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
  if not E.save_loaded_asset(tex,False):raise RuntimeError('Screen texture save failed')
  path=BASE+'/Materials/M_AP_'+key
  mat=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset('M_AP_'+key,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
  for old in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,old)
  mat.set_editor_property('used_with_nanite',True)
  slab=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
  sample=L.create_material_expression(mat,u.MaterialExpressionTextureSample);sample.set_editor_property('texture',tex)
  sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  rough=L.create_material_expression(mat,u.MaterialExpressionConstant);rough.set_editor_property('r',.27)
  for src,out,pin in ((sample,'RGB','BaseColor'),(sample,'RGB','Emissive Color'),(rough,'','Roughness')):
   if not L.connect_material_expressions(src,out,slab,pin):raise RuntimeError('Screen pin '+pin)
  L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
  errors=L.recompile_material(mat)
  if errors:raise RuntimeError(str(errors))
  if not E.save_loaded_asset(mat,False):raise RuntimeError('Screen material save failed')
