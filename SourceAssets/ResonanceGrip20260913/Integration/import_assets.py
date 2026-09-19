import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/ResonanceGrip20260913'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={}
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
def import_file(file,name,dest,options=None):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=dest;task.destination_name=name;task.options=options;task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);asset=u.load_asset(dest+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+name)
    return asset
textures={}
for key in ['BaseColor','MetalRough']:
 t=import_file(P/('T_Resonance_'+key+'.png'),'T_Resonance_'+key,D);t.srgb=key=='BaseColor';t.compression_settings=u.TextureCompressionSettings.TC_DEFAULT if key=='BaseColor' else u.TextureCompressionSettings.TC_MASKS;save(t);textures[key]=t
def sample(m,tex,uv,sampler):
 n=M.create_material_expression(m,u.MaterialExpressionTextureSample);n.texture=tex;n.sampler_type=sampler;M.connect_material_expressions(uv,'',n,'UVs');return n

def coating(family):
 dest=D+'/'+family;name='M_Resonance_'+family
 m=u.load_asset(dest+'/'+name) or A.create_asset(name,dest,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(m)
 uv=M.create_material_expression(m,u.MaterialExpressionTextureCoordinate);uv.coordinate_index=1
 if family=='M4':
  root='/Game/Weapons/AttachmentFinish20260913/M4/Textures/T_M4_Receiver_'
  base=sample(m,u.load_asset(root+'BaseColor'),uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  rough=sample(m,u.load_asset(root+'Roughness'),uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  fn=M.create_material_expression(m,u.MaterialExpressionMaterialFunctionCall);fn.set_editor_property('material_function',u.load_asset('/InterchangeAssets/Functions/MF_PhongToMetalRoughness'))
  M.connect_material_expressions(base,'RGB',fn,'DiffuseColor');M.connect_material_expressions(rough,'R',fn,'Shininess')
  for pin,value in [('SpecularColor',.2),('AmbientColor',0.)]:
   c=M.create_material_expression(m,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(value,value,value,1);M.connect_material_expressions(c,'',fn,pin)
  for pin,prop in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('Metallic',u.MaterialProperty.MP_METALLIC),('Specular',u.MaterialProperty.MP_SPECULAR)]:M.connect_material_property(fn,pin,prop)
 elif family=='AKM':
  for label,prop in [('Base_color',u.MaterialProperty.MP_BASE_COLOR),('Metallic',u.MaterialProperty.MP_METALLIC),('Roughness',u.MaterialProperty.MP_ROUGHNESS)]:
   tex=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/Textures/T_AKM_Mount_'+label)
   n=sample(m,tex,uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR if label=='Base_color' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE);M.connect_material_property(n,'RGB' if label=='Base_color' else 'R',prop)
 else:
  for label in ['BaseColor','ORM']:
   name='T_QBZ191_StableCollar_'+label;tex=import_file(Path('D:/FPS3D/FPSGAME/SourceAssets/StableAntiSlipRearGrip20260913/Selected91727/Textures')/(name+'.png'),name,dest)
   tex.srgb=label=='BaseColor';tex.compression_settings=u.TextureCompressionSettings.TC_DEFAULT if label=='BaseColor' else u.TextureCompressionSettings.TC_MASKS;save(tex)
   n=sample(m,tex,uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR if label=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
   if label=='BaseColor':M.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR)
   else:M.connect_material_property(n,'G',u.MaterialProperty.MP_ROUGHNESS);M.connect_material_property(n,'B',u.MaterialProperty.MP_METALLIC)
 E.set_metadata_tag(m,'ReceiverReference',{'M4':'/Game/Weapons/M4InfimaV3/Body_001','AKM':'/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR','QBZ191':'QBZ191MetalCoat20260913/bake_coating.py current receiver coating'}[family])

 # GLTF metallic blue channel is the material-region source, not luminance.
 uv0=M.create_material_expression(m,u.MaterialExpressionTextureCoordinate);uv0.coordinate_index=0
 bc=sample(m,textures['BaseColor'],uv0,u.MaterialSamplerType.SAMPLERTYPE_COLOR)
 mr=sample(m,textures['MetalRough'],uv0,u.MaterialSamplerType.SAMPLERTYPE_MASKS)
 mask=M.create_material_expression(m,u.MaterialExpressionSmoothStep);mask.set_editor_property('const_min',.2);mask.set_editor_property('const_max',.6);M.connect_material_expressions(mr,'B',mask,'Value')
 for prop,old,out in [(u.MaterialProperty.MP_BASE_COLOR,bc,'RGB'),(u.MaterialProperty.MP_ROUGHNESS,mr,'G'),(u.MaterialProperty.MP_METALLIC,mr,'B')]:
  coated=M.get_material_property_input_node(m,prop);co=M.get_material_property_input_node_output_name(m,prop)
  blend=M.create_material_expression(m,u.MaterialExpressionLinearInterpolate);M.connect_material_expressions(old,out,blend,'A');M.connect_material_expressions(coated,co,blend,'B');M.connect_material_expressions(mask,'',blend,'Alpha');M.connect_material_property(blend,'',prop)
 E.set_metadata_tag(m,'Regions','UV0 GLTF metallic mask: coated metal frame, original polymer inserts; UV1 receiver finish')
 M.recompile_material(m);save(m);return m

for key in ['M4','AKM','QBZ191']:
 mat=coating(key)
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False;options.import_animations=False
 data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
 mesh=import_file(P/key/'SM_ResonanceGrip.fbx','SM_ResonanceGrip',D+'/'+key,options)
 for i in range(len(mesh.static_materials)):mesh.set_material(i,mat)
 E.set_metadata_tag(mesh,'SelectedSeed','91813');save(mesh);report[key]=mesh.get_path_name()
(P/'import_results.json').write_text(json.dumps(report,indent=2));u.log('RESONANCE_IMPORT_COMPLETE')
