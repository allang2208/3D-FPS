import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/PhantomRearGrip'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
sources=json.loads((P/'sources.json').read_text());auth=json.loads((P/'authoring.json').read_text());report={}
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
def import_file(file,name,dest,options=None):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=dest;task.destination_name=name;task.options=options;task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);asset=u.load_asset(dest+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+name)
    return asset
textures={}
for key in ['BaseColor','MetalRough']:
    texture=import_file(P/('T_PhantomRearGrip_'+key+'.png'),'T_PhantomRearGrip_'+key,D)
    if key=='MetalRough':texture.srgb=False;texture.compression_settings=u.TextureCompressionSettings.TC_MASKS
    save(texture);textures[key]=texture
mat=u.load_asset(D+'/M_PhantomRearGrip') or A.create_asset('M_PhantomRearGrip',D,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(mat)
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
    mesh=import_file(P/key/'SM_PhantomRearGrip.fbx','SM_PhantomRearGrip',D+'/'+key,options);mesh.set_material(0,mat);save(mesh)
    report[key]={'grip':mesh.get_path_name()}
for key,dest,name in [('AKM','/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913','SK_AKM_MannyNative'),('QBZ191','/Game/Weapons/QBZ191/RearGrip20260913','SK_QBZ191_Manny')]:
    original=u.load_asset(sources[key]['asset']);bindings={str(x.material_slot_name):x.material_interface for x in original.materials}
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=original.skeleton
    options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=import_file(P/key/(name+'.fbx'),name,dest,options);slots=mesh.materials
    for i,slot in enumerate(slots):
        name0=str(slot.material_slot_name);source=auth['factory_bindings'][key].get(name0,name0)
        slot.material_interface=bindings[source];slots[i]=slot
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',original.get_editor_property('physics_asset'));save(mesh)
    report[key]['sectioned_gun']=mesh.get_path_name()
report['status']='Authored and imported. No runtime tests performed.'
(P/'import_results.json').write_text(json.dumps(report,indent=2));u.log('PHANTOM_REAR_GRIP_IMPORT_COMPLETE')
