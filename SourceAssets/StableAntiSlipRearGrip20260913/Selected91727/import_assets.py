import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/StableAntiSlipRearGrip/Selected91727'
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
    texture=import_file(P/('T_StableAntiSlipRearGrip_'+key+'.png'),'T_StableAntiSlipRearGrip_'+key,D)
    if key=='MetalRough':texture.srgb=False;texture.compression_settings=u.TextureCompressionSettings.TC_MASKS
    save(texture);textures[key]=texture
mat=u.load_asset(D+'/M_StableAntiSlipRearGrip') or A.create_asset('M_StableAntiSlipRearGrip',D,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(mat)
for key,texture in textures.items():
    node=M.create_material_expression(mat,u.MaterialExpressionTextureSample);node.texture=texture
    if key=='MetalRough':
        node.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS
        rough=M.create_material_expression(mat,u.MaterialExpressionClamp);rough.set_editor_property('min_default',.55);rough.set_editor_property('max_default',.95);M.connect_material_expressions(node,'G',rough,'Input');M.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    else:M.connect_material_property(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
metal=M.create_material_expression(mat,u.MaterialExpressionConstant);metal.r=0.;M.connect_material_property(metal,'',u.MaterialProperty.MP_METALLIC)
M.recompile_material(mat);save(mat)

def sample(m,tex,uv,sampler):
 n=M.create_material_expression(m,u.MaterialExpressionTextureSample);n.texture=tex;n.sampler_type=sampler;M.connect_material_expressions(uv,'',n,'UVs');return n

def coating(family):
 dest=D+'/'+family;name='M_StableGrip_Collar_'+family
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
   name='T_QBZ191_StableCollar_'+label;tex=import_file(P/'Textures'/(name+'.png'),name,dest)
   tex.srgb=label=='BaseColor';tex.compression_settings=u.TextureCompressionSettings.TC_DEFAULT if label=='BaseColor' else u.TextureCompressionSettings.TC_MASKS;save(tex)
   n=sample(m,tex,uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR if label=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
   if label=='BaseColor':M.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR)
   else:M.connect_material_property(n,'G',u.MaterialProperty.MP_ROUGHNESS);M.connect_material_property(n,'B',u.MaterialProperty.MP_METALLIC)
 E.set_metadata_tag(m,'ReceiverReference',{'M4':'/Game/Weapons/M4InfimaV3/Body_001','AKM':'/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR','QBZ191':'QBZ191MetalCoat20260913/bake_coating.py current receiver coating'}[family])
 M.recompile_material(m);save(m);return m
for key in ['M4','AKM','QBZ191']:
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False;options.import_animations=False
    options.static_mesh_import_data.generate_lightmap_u_vs=False;options.static_mesh_import_data.combine_meshes=True;options.static_mesh_import_data.auto_generate_collision=False;options.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=import_file(P/key/'SM_StableAntiSlipRearGrip.fbx','SM_StableAntiSlipRearGrip',D+'/'+key,options);mesh.set_material(0,mat)
    collar=coating(key)
    for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,collar if 'Collar' in str(slot.material_slot_name) else mat)
    E.set_metadata_tag(mesh,'SelectedSeed','91727');E.set_metadata_tag(mesh,'CoatingUV','UV1; M4 12x5cm, AKM 12x2.5cm, QBZ191 10x10cm; UV0 preserved')
    save(mesh)
    report[key]={'grip':mesh.get_path_name()}

(P/'import_results.json').write_text(json.dumps(report,indent=2));u.log('STABLE_GRIP_IMPORT_COMPLETE')


