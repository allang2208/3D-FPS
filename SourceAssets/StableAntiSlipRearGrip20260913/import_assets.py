import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/StableAntiSlipRearGrip'
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
        M.connect_material_property(node,'G',u.MaterialProperty.MP_ROUGHNESS);M.connect_material_property(node,'B',u.MaterialProperty.MP_METALLIC)
    else:M.connect_material_property(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
M.recompile_material(mat);save(mat)
for key in ['M4','AKM','QBZ191']:
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False;options.import_animations=False
    options.static_mesh_import_data.combine_meshes=True;options.static_mesh_import_data.auto_generate_collision=False;options.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=import_file(P/key/'SM_StableAntiSlipRearGrip.fbx','SM_StableAntiSlipRearGrip',D+'/'+key,options);mesh.set_material(0,mat)
    original=u.load_asset('/Game/Weapons/PhantomRearGrip/'+key+'/ReceiverFit/SM_PhantomRearGrip')
    if len(mesh.static_materials)>1:mesh.set_material(1,original.get_material(1) if original and len(original.static_materials)>1 else mat)
    save(mesh)
    report[key]={'grip':mesh.get_path_name()}

(P/'import_results.json').write_text(json.dumps(report,indent=2));u.log('STABLE_GRIP_IMPORT_COMPLETE')
