"""Create standalone skin-only resources without changing the active blueprint."""
import unreal as u, json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ZombieDogSkinOnlyV2')
DEST='/Game/Monsters/ZombieDog/SkinOnlyV2'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary

def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())

textures={}
for semantic in ['BaseColor','ORM','Normal']:
    name='T_ZombieDog_SkinOnly_'+semantic
    path=DEST+'/Textures/'+name
    tex=u.load_asset(path) if LIB.does_asset_exist(path) else None
    if tex is None:
        task=u.AssetImportTask();task.filename=str(ROOT/'Textures'/(name+'.png'))
        task.destination_path=DEST+'/Textures';task.destination_name=name
        task.automated=True;task.save=True;TOOLS.import_asset_tasks([task])
        tex=u.load_asset(path)
        if tex is None:raise RuntimeError('Texture import failed: '+semantic)
        tex.set_editor_property('srgb',semantic=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if semantic=='Normal' else
            u.TextureCompressionSettings.TC_DEFAULT if semantic=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
        save(tex)
    textures[semantic]=tex

material_path=DEST+'/M_ZombieDog_SkinOnly'
mat=u.load_asset(material_path) if LIB.does_asset_exist(material_path) else None
if mat is None:
    mat=TOOLS.create_asset('M_ZombieDog_SkinOnly',DEST,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('used_with_skeletal_mesh',True)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    def node(cls):return MEL.create_material_expression(mat,cls)
    for semantic,tex in textures.items():
        sample=node(u.MaterialExpressionTextureSampleParameter2D)
        sample.set_editor_property('parameter_name',semantic);sample.set_editor_property('texture',tex)
        sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if semantic=='Normal' else
            u.MaterialSamplerType.SAMPLERTYPE_COLOR if semantic=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        if semantic=='ORM':
            for output,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:
                MEL.connect_material_property(sample,output,prop)
        elif semantic=='BaseColor':
            tint=node(u.MaterialExpressionVectorParameter);tint.set_editor_property('parameter_name','SkinTint')
            tint.set_editor_property('default_value',u.LinearColor(1,1,1,1))
            multiply=node(u.MaterialExpressionMultiply)
            MEL.connect_material_expressions(sample,'RGB',multiply,'A');MEL.connect_material_expressions(tint,'RGB',multiply,'B')
            MEL.connect_material_property(multiply,'',u.MaterialProperty.MP_BASE_COLOR)
        else:MEL.connect_material_property(sample,'RGB',u.MaterialProperty.MP_NORMAL)
    spec=node(u.MaterialExpressionScalarParameter);spec.set_editor_property('parameter_name','Specular');spec.set_editor_property('default_value',.32)
    MEL.connect_material_property(spec,'',u.MaterialProperty.MP_SPECULAR)
    MEL.recompile_material(mat);save(mat)

mesh_path=DEST+'/SK_ZombieDog_SkinOnly'
mesh=u.load_asset(mesh_path) if LIB.does_asset_exist(mesh_path) else None
if mesh is None:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False
    options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
    options.skeleton=u.load_asset('/Game/AnimalVarietyPack/Wolf/Meshes/SK_Wolf_Skeleton')
    options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    options.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
    options.skeletal_mesh_import_data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task=u.AssetImportTask();task.filename=str(ROOT/'SK_ZombieDog_SkinOnly.fbx')
    task.destination_path=DEST;task.destination_name='SK_ZombieDog_SkinOnly'
    task.options=options;task.automated=True;task.save=True
    TOOLS.import_asset_tasks([task]);mesh=u.load_asset(mesh_path)
    if mesh is None:raise RuntimeError('Skin-only mesh import failed')
if LIB.get_metadata_tag(mesh,'ZombieDog.SkinOnly')!='2':
    slots=mesh.get_editor_property('materials')
    for i,slot in enumerate(slots):slot.material_interface=mat;slots[i]=slot
    mesh.set_editor_property('materials',slots)
    mesh.set_editor_property('physics_asset',u.load_asset('/Game/Monsters/ZombieDog/V1/PA_ZombieDog'))
    mesh.set_editor_property('enable_per_poly_collision',False)
    LIB.set_metadata_tag(mesh,'ZombieDog.SkinOnly','2');save(mesh)

dataset_path=DEST+'/DA_ZombieDog_SkinOnly'
dataset=u.load_asset(dataset_path) if LIB.does_asset_exist(dataset_path) else LIB.duplicate_asset(
    '/Game/Monsters/ZombieDog/V1/DA_ZombieDog_AnimationSet',dataset_path)
if LIB.get_metadata_tag(dataset,'ZombieDog.SkinOnly')!='2':
    dataset.set_editor_property('reference_mesh',mesh)
    LIB.set_metadata_tag(dataset,'ZombieDog.SkinOnly','2');save(dataset)
(ROOT/'ue_import.json').write_text(json.dumps({'mesh':mesh_path,'material':material_path,
    'dataset':dataset_path,'blueprint_switched':False,'runtime_tested':False,'preview_rendered':False},indent=2),encoding='utf-8')
u.log('ZOMBIE_DOG_SKIN_ONLY_IMPORTED '+mesh_path)
