import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/QRPerformanceStock/Meshy20260913'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={}
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
def import_file(file,name,dest,options=None):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=dest;task.destination_name=name;task.options=options;task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);asset=u.load_asset(dest+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+name)
    return asset
def sample(m,tex,uv,sampler):
 n=M.create_material_expression(m,u.MaterialExpressionTextureSample);n.texture=tex;n.sampler_type=sampler;M.connect_material_expressions(uv,'',n,'UVs');return n

def coating(family):
 dest=D+'/'+family;name='M_PerformanceStock_'+family
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

 M.recompile_material(m);save(m);return m


textures={}
for key in ['BaseColor','Normal','Roughness']:
 t=import_file(P/'Textures'/(key+'.png'),'T_Stock_'+key,D+'/Textures');t.set_editor_property('srgb',key=='BaseColor');t.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);t.set_editor_property('lod_bias',0)
 t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if key=='BaseColor' else u.TextureCompressionSettings.TC_MASKS
 if key=='Normal':t.set_editor_property('flip_green_channel',True)
 save(t);textures[key]=t

def source_material(kind):
 name='M_Stock_'+kind;m=u.load_asset(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(m)
 uv=M.create_material_expression(m,u.MaterialExpressionTextureCoordinate);uv.coordinate_index=0
 for key,prop in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Normal',u.MaterialProperty.MP_NORMAL),('Roughness',u.MaterialProperty.MP_ROUGHNESS)]:
  n=sample(m,textures[key],uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
  if key=='Roughness' and kind=='Rubber':
   c=M.create_material_expression(m,u.MaterialExpressionClamp);c.set_editor_property('min_default',.75);c.set_editor_property('max_default',1.);M.connect_material_expressions(n,'R',c,'Input');M.connect_material_property(c,'',prop)
  else:M.connect_material_property(n,'R' if key=='Roughness' else 'RGB',prop)
 M.recompile_material(m);save(m);return m
poly=source_material('Polymer');rubber=source_material('Rubber')
for family in ['M4','AKM','QBZ191']:
 metal=coating(family)
 adapter=A.duplicate_asset('M_StockAdapter_'+family,D+'/'+family,metal) if not E.does_asset_exist(D+'/'+family+'/M_StockAdapter_'+family) else u.load_asset(D+'/'+family+'/M_StockAdapter_'+family)
 uv=M.create_material_expression(metal,u.MaterialExpressionTextureCoordinate);uv.coordinate_index=0;n=sample(metal,textures['Normal'],uv,u.MaterialSamplerType.SAMPLERTYPE_NORMAL);M.connect_material_property(n,'RGB',u.MaterialProperty.MP_NORMAL);M.recompile_material(metal);save(metal);save(adapter)
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
 data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
 mesh=import_file(P/family/'SM_PerformanceStock.fbx','SM_PerformanceStock',D+'/'+family,opt)
 for i,slot in enumerate(mesh.static_materials):
  name=str(slot.material_slot_name);mesh.set_material(i,poly if 'Polymer' in name else rubber if 'Rubber' in name else adapter if 'Adapter' in name else metal)
 save(mesh);report[family]=mesh.get_path_name()
(P/'import_results.json').write_text(json.dumps(report,indent=2));u.log('PERFORMANCE_STOCK_IMPORTED')
