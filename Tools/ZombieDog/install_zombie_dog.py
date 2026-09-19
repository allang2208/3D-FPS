"""Import the authored zombie dog and bind the existing wolf gameplay system."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ZombieDogV1')
DEST='/Game/Monsters/ZombieDog/V1'
LIB=u.EditorAssetLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()
MEL=u.MaterialEditingLibrary
VERSION='2'

def save(asset):
    if not LIB.save_loaded_asset(asset,False):
        raise RuntimeError('Save failed: '+asset.get_path_name())

def duplicate(source,name):
    path=DEST+'/'+name
    return u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(source,path)

def texture(semantic):
    path=DEST+'/Textures/T_ZombieDog_'+semantic
    previous=u.load_asset(path) if LIB.does_asset_exist(path) else None
    if previous and LIB.get_metadata_tag(previous,'ZombieDog.TextureRevision')==VERSION:return previous
    task=u.AssetImportTask()
    task.filename=str(ROOT/'Textures'/('T_ZombieDog_'+semantic+'.png'))
    task.destination_name='T_ZombieDog_'+semantic
    task.destination_path=DEST+'/Textures'
    task.automated=True;task.save=True;task.replace_existing=previous is not None
    TOOLS.import_asset_tasks([task])
    tex=u.load_asset(path)
    if tex is None:raise RuntimeError('Texture import failed: '+semantic)
    tex.set_editor_property('srgb',semantic=='BaseColor')
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if semantic=='Normal' else
        u.TextureCompressionSettings.TC_DEFAULT if semantic=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
    LIB.set_metadata_tag(tex,'ZombieDog.TextureRevision',VERSION)
    save(tex)
    return tex

textures={s:texture(s) for s in ['BaseColor','ORM','Opacity','Normal']}

def material(name,fur=False):
    path=DEST+'/Materials/'+name
    if LIB.does_asset_exist(path):return u.load_asset(path)
    mat=TOOLS.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('used_with_skeletal_mesh',True)
    mat.set_editor_property('two_sided',fur)
    if fur:
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
        mat.set_editor_property('opacity_mask_clip_value',.33)
    def node(cls):return MEL.create_material_expression(mat,cls)
    def link(a,pin,b,input):MEL.connect_material_expressions(a,pin,b,input)
    samples={}
    for sem,tex in textures.items():
        s=node(u.MaterialExpressionTextureSampleParameter2D)
        s.set_editor_property('parameter_name',sem)
        s.set_editor_property('texture',tex)
        s.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if sem=='Normal' else
            u.MaterialSamplerType.SAMPLERTYPE_COLOR if sem=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        samples[sem]=s
    tint=node(u.MaterialExpressionVectorParameter)
    tint.set_editor_property('parameter_name','SkinTint')
    tint.set_editor_property('default_value',u.LinearColor(1,1,1,1))
    color=node(u.MaterialExpressionMultiply);link(samples['BaseColor'],'RGB',color,'A');link(tint,'RGB',color,'B')
    MEL.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(samples['Normal'],'RGB',u.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(samples['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    scale=node(u.MaterialExpressionScalarParameter);scale.set_editor_property('parameter_name','RoughnessScale');scale.set_editor_property('default_value',1.)
    rough=node(u.MaterialExpressionMultiply);link(samples['ORM'],'G',rough,'A');link(scale,'',rough,'B')
    MEL.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    metal=node(u.MaterialExpressionConstant);metal.set_editor_property('r',0.)
    MEL.connect_material_property(metal,'',u.MaterialProperty.MP_METALLIC)
    spec=node(u.MaterialExpressionScalarParameter);spec.set_editor_property('parameter_name','Specular');spec.set_editor_property('default_value',.32)
    MEL.connect_material_property(spec,'',u.MaterialProperty.MP_SPECULAR)
    if fur:MEL.connect_material_property(samples['Opacity'],'R',u.MaterialProperty.MP_OPACITY_MASK)
    MEL.recompile_material(mat);save(mat)
    return mat

skin=material('M_ZombieDog_Skin')
fur=material('M_ZombieDog_RemainingFur',True)
mesh_path=DEST+'/SK_ZombieDog'
mesh=u.load_asset(mesh_path) if LIB.does_asset_exist(mesh_path) else None
if mesh is None or LIB.get_metadata_tag(mesh,'ZombieDog.Version')!=VERSION:
    # Use legacy FBX importer and the original wolf skeleton without updating its bind pose.
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    options=u.FbxImportUI()
    options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False
    options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
    options.skeleton=u.load_asset('/Game/AnimalVarietyPack/Wolf/Meshes/SK_Wolf_Skeleton')
    options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    options.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
    options.skeletal_mesh_import_data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task=u.AssetImportTask();task.filename=str(ROOT/'SK_ZombieDog.fbx')
    task.destination_path=DEST;task.destination_name='SK_ZombieDog'
    task.options=options;task.automated=True;task.save=True;task.replace_existing=mesh is not None
    TOOLS.import_asset_tasks([task]);mesh=u.load_asset(mesh_path)
    if mesh is None:raise RuntimeError('Zombie dog mesh import failed')

if LIB.get_metadata_tag(mesh,'ZombieDog.Version')!=VERSION:
    slots=mesh.get_editor_property('materials')
    for i,slot in enumerate(slots):
        slot.material_interface=fur if 'Fur' in str(slot.material_slot_name) else skin
        slots[i]=slot
    mesh.set_editor_property('materials',slots)
    physics=duplicate('/Game/Monsters/Wolf/PA_Wolf_Gameplay','PA_ZombieDog')
    mesh.set_editor_property('physics_asset',physics)
    mesh.set_editor_property('enable_per_poly_collision',False)
    LIB.set_metadata_tag(mesh,'ZombieDog.Version',VERSION)
    LIB.set_metadata_tag(mesh,'Source','PROTOFACTOR wolf; user library ZombiSkinMaterial; local sculpt and rest-space texture bake')
    save(physics);save(mesh)

dataset=duplicate('/Game/Monsters/Wolf/DA_Wolf_AnimationSet','DA_ZombieDog_AnimationSet')
if LIB.get_metadata_tag(dataset,'ZombieDog.Version')!=VERSION:
    dataset.set_editor_property('reference_mesh',mesh)
    LIB.set_metadata_tag(dataset,'ZombieDog.Version',VERSION)
    save(dataset)

bp_path=DEST+'/BP_ZombieDog'
if LIB.does_asset_exist(bp_path):blueprint=u.load_asset(bp_path)
else:
    parent=u.load_asset('/Game/Monsters/Wolf/BP_WolfMonster')
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',parent.generated_class())
    blueprint=TOOLS.create_asset('BP_ZombieDog',DEST,u.Blueprint,factory)
if LIB.get_metadata_tag(blueprint,'ZombieDog.Version')!=VERSION:
    u.BlueprintEditorLibrary.compile_blueprint(blueprint)
    defaults=u.get_default_object(blueprint.generated_class())
    defaults.set_editor_property('animation_set',dataset)
    defaults.set_editor_property('monster_display_name',u.Text('僵尸犬'))
    tags=list(defaults.get_editor_property('tags'))
    defaults.set_editor_property('tags',tags+['ZombieDog','Undead'])
    component=defaults.get_editor_property('mesh')
    component.set_skeletal_mesh_asset(mesh)
    component.set_anim_instance_class(u.QuadrupedTemplateAnimInstance.static_class())
    LIB.set_metadata_tag(blueprint,'ZombieDog.Version',VERSION)
    save(blueprint)

(ROOT/'ue_delivery.json').write_text(json.dumps({
    'blueprint':bp_path,'parent':'/Game/Monsters/Wolf/BP_WolfMonster',
    'mesh':mesh.get_path_name(),'animation_set':dataset.get_path_name(),
    'materials':[skin.get_path_name(),fur.get_path_name()],
    'f6_id':'ZombieDog','display_name':'僵尸犬',
    'gameplay':'Inherited wolf AI, combat clock, hit reactions, locomotion V2, bite V2, pounce and ragdoll',
    'balance':'Inherited wolf defaults: no gameplay rebalance in this visual variant',
    'runtime_tested':False,'preview_rendered':False,
},ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ZOMBIE_DOG_IMPORTED_AND_BOUND '+bp_path)
