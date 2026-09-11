"""Import baked green material variants; preserves mesh/rig/animations/physics."""
import unreal,json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/sculpt_v06')
manifest=json.loads((R/'bake_manifest.json').read_text())
rows=json.loads((R/'material_report.json').read_text())['materials']
dest='/Game/Monsters/HandBrain/SculptV06'
lib=unreal.EditorAssetLibrary;tools=unreal.AssetToolsHelpers.get_asset_tools();mel=unreal.MaterialEditingLibrary
mesh=unreal.load_asset('/Game/Monsters/HandBrain/SculptV06/SK_HandBrain_Sculpt');assert mesh
old=[s.material_interface.get_path_name() for s in mesh.get_editor_property('materials')]
report={'fab_material_used':True,'previous_materials':old,'materials':[],'mesh_changed':False,'animations_changed':False}
materials=[]
for index,row in enumerate(rows):
 name='M_HandBrain_Refined_'+str(index);path=dest+'/'+name
 m=unreal.load_asset(path) if lib.does_asset_exist(path) else tools.create_asset(name,dest,unreal.Material,unreal.MaterialFactoryNew())
 mel.delete_all_material_expressions(m);m.set_editor_property('two_sided',False)
 def expr(cls):return mel.create_material_expression(m,cls)
 for sem,prop in [('BaseColor',unreal.MaterialProperty.MP_BASE_COLOR),('Roughness',unreal.MaterialProperty.MP_ROUGHNESS),('Normal_DirectX',unreal.MaterialProperty.MP_NORMAL)]:
  if False: # V05 lining uses baked tissue maps
   # Authored interior has degenerate UVs; never use its empty bake.
   if sem=='BaseColor':
    value=expr(unreal.MaterialExpressionVectorParameter);value.set_editor_property('parameter_name','MucosaColor');value.set_editor_property('default_value',unreal.LinearColor(.065,.007,.011,1));mel.connect_material_property(value,'RGB',prop)
   elif sem=='Roughness':
    value=expr(unreal.MaterialExpressionScalarParameter);value.set_editor_property('parameter_name','MucosaRoughness');value.set_editor_property('default_value',.28);mel.connect_material_property(value,'',prop)
   continue
  item=next(d for d in manifest if d['object']==row['object'] and d['slot']==row['slot'] and d['semantic']==sem)
  task=unreal.AssetImportTask();task.filename=item['path'];task.destination_path=dest+'/Textures';task.destination_name='T_Refined_'+str(index)+'_'+sem;task.automated=True;task.replace_existing=True;task.save=True
  tools.import_asset_tasks([task]);tex=unreal.load_asset(task.destination_path+'/'+task.destination_name);assert tex
  tex.set_editor_property('srgb',sem=='BaseColor')
  if sem=='Normal_DirectX':tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
  elif sem=='Roughness':tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
  lib.save_loaded_asset(tex,False)
  n=expr(unreal.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name',sem);n.set_editor_property('texture',tex)
  if sem=='Normal_DirectX':n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
  elif sem=='Roughness':n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
  if sem=='BaseColor':
   tint=expr(unreal.MaterialExpressionVectorParameter);tint.set_editor_property('parameter_name','SkinTint');tint.set_editor_property('default_value',unreal.LinearColor(1,1,1,1))
   mul=expr(unreal.MaterialExpressionMultiply);mel.connect_material_expressions(n,'RGB',mul,'A');mel.connect_material_expressions(tint,'RGB',mul,'B');mel.connect_material_property(mul,'',prop)
  else:mel.connect_material_property(n,'R' if sem=='Roughness' else 'RGB',prop)
 spec=expr(unreal.MaterialExpressionScalarParameter);spec.set_editor_property('parameter_name','Specular');spec.set_editor_property('default_value',.32);mel.connect_material_property(spec,'',unreal.MaterialProperty.MP_SPECULAR)
 # Subtle tissue scattering; high opacity avoids a waxy full-volume appearance.
 if row['semantic']!='teeth':
  m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
  ss=expr(unreal.MaterialExpressionConstant3Vector);ss.set_editor_property('constant',unreal.LinearColor(.08,.12,.035,1) if row['semantic']=='skin_wound' else unreal.LinearColor(.15,.018,.024,1));mel.connect_material_property(ss,'',unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
  op=expr(unreal.MaterialExpressionConstant);op.set_editor_property('r',.9);mel.connect_material_property(op,'',unreal.MaterialProperty.MP_OPACITY)
 m.set_editor_property('used_with_skeletal_mesh',True)
 mel.recompile_material(m);lib.save_loaded_asset(m,False);materials.append(m);report['materials'].append(m.get_path_name())
slots=mesh.get_editor_property('materials');assert len(slots)==len(materials)==6
for i,slot in enumerate(slots):slot.material_interface=materials[i];slots[i]=slot
mesh.set_editor_property('materials',slots);assert lib.save_loaded_asset(mesh,False)
assert [s.material_interface.get_path_name() for s in mesh.get_editor_property('materials')]==report['materials']
(R/'ue_import_report.json').write_text(json.dumps(report,indent=2))
unreal.log('HANDBRAIN_REFINED_IMPORT_COMPLETE')
