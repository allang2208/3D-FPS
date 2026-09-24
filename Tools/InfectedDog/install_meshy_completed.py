"""Import/save the completed Meshy canine and all existing-action retargets.

Designed for a background UE Python commandlet. No game, tests or rendering.
Only the new MeshyV2 asset subtree and BP_InfectedDog appearance are changed.
"""
import json, shutil, sys
from pathlib import Path
import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meshy_animation_units import match_bind_root_scale

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/InfectedDogMeshy20260924/CompletionV2'
DEST='/Game/Monsters/InfectedDog/MeshyV2'
BP_PATH='/Game/Monsters/InfectedDog/BP_InfectedDog'
REVISION='MeshyCanineMouthMotionV2-20260924'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
ANIMS=json.loads((ROOT/'animation_authoring.json').read_text(encoding='utf-8'))
report={'state':'importing','revision':REVISION,'saved':[], 'animations':{},
        'gameplay_changed':False,'runtime_tested':False,'preview_rendered':False}
def record():(ROOT/'installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if asset is None:raise RuntimeError('Required asset missing: '+path)
    return asset
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    name=asset.get_path_name()
    if name not in report['saved']:report['saved'].append(name)
    record()
def create(name,cls,factory):
    path=DEST+'/'+name
    if LIB.does_asset_exist(path):
        asset=load(path)
        if LIB.get_metadata_tag(asset,'InfectedDog.MeshyRevision')!=REVISION:
            raise RuntimeError('Preserving independent asset '+path)
        return asset,False
    asset=TOOLS.create_asset(name,DEST,cls,factory)
    if asset is None:raise RuntimeError('Could not create '+path)
    LIB.set_metadata_tag(asset,'InfectedDog.MeshyRevision',REVISION)
    return asset,True
def marked(asset):LIB.set_metadata_tag(asset,'InfectedDog.MeshyRevision',REVISION)

if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
bp=u.load_asset(BP_PATH)
bp_existed=bp is not None
if bp is None:
    factory=u.BlueprintFactory()
    factory.set_editor_property('parent_class',u.InfectedDogMonster.static_class())
    bp=TOOLS.create_asset('BP_InfectedDog','/Game/Monsters/InfectedDog',u.Blueprint,factory)
    if bp is None:raise RuntimeError('Could not create infected-dog entry Blueprint')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class())
old_set=cdo.get_editor_property('animation_set')
old_mesh=old_set.get_editor_property('reference_mesh') if old_set else None
dirty={p.get_name().casefold() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if (bp_existed and BP_PATH.casefold() in dirty) or any(p.startswith(DEST.casefold()) for p in dirty):
    raise RuntimeError('Preserving unsaved target edits')
backup=ROOT/'Before';backup.mkdir(exist_ok=True)
original=PROJECT/'Content/Monsters/InfectedDog/BP_InfectedDog.uasset'
if original.exists() and not (backup/'BP_InfectedDog.uasset').exists():shutil.copy2(original,backup/'BP_InfectedDog.uasset')
if not (ROOT/'appearance_before.json').exists():
    (ROOT/'appearance_before.json').write_text(json.dumps({'blueprint':BP_PATH,
        'animation_set':old_set.get_path_name() if old_set else None,'mesh':old_mesh.get_path_name() if old_mesh else None,
        'materials':[m.get_path_name() if m else None for m in cdo.get_editor_property('mesh').get_editor_property('override_materials')]},indent=2),encoding='utf-8')
record()

textures={}
files={'BaseColor':'texture_0.png','Normal':'normal.png','MetallicRoughness':'texture_0_metallic_roughness.png'}
for semantic,filename in files.items():
    name='T_InfectedDogMeshy_'+semantic
    task=u.AssetImportTask();task.filename=str(ROOT/'Textures'/filename)
    task.destination_name=name;task.destination_path=DEST+'/Textures'
    task.automated=True;task.save=False;task.replace_existing=True
    TOOLS.import_asset_tasks([task]);texture=load(task.destination_path+'/'+name)
    texture.set_editor_property('srgb',semantic=='BaseColor')
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if semantic=='Normal'
        else u.TextureCompressionSettings.TC_DEFAULT if semantic=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('max_texture_size',4096 if semantic in ('BaseColor','Normal') else 2048)
    texture.set_editor_property('never_stream',False)
    if semantic=='Normal':texture.set_editor_property('flip_green_channel',True) # glTF/OpenGL normal map.
    marked(texture);save(texture);textures[semantic]=texture

profile,new=create('SSP_InfectedDogMeshy',u.SubsurfaceProfile,u.SubsurfaceProfileFactory())
if new:
    settings=profile.get_editor_property('settings')
    settings.set_editor_property('surface_albedo',u.LinearColor(.22,.28,.13,1))
    settings.set_editor_property('mean_free_path_color',u.LinearColor(1,.55,.3,1))
    settings.set_editor_property('mean_free_path_distance',.12)
    settings.set_editor_property('world_unit_scale',1.)
    settings.set_editor_property('enable_burley',True)
    profile.set_editor_property('settings',settings);save(profile)

def material_graph(name,oral=None):
    mat,new=create(name,u.Material,u.MaterialFactoryNew())
    if not new:return mat
    mat.set_editor_property('used_with_skeletal_mesh',True)
    mat.set_editor_property('two_sided',False)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    shading=u.MaterialShadingModel.MSM_SUBSURFACE_PROFILE if oral is None else u.MaterialShadingModel.MSM_DEFAULT_LIT
    mat.set_editor_property('shading_model',shading)
    if oral is None:mat.set_editor_property('subsurface_profile',profile)
    def node(cls,**kw):
        n=MEL.create_material_expression(mat,cls)
        for k,v in kw.items():n.set_editor_property(k,v)
        return n
    def wire(a,out,b,pin):
        if not MEL.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material wire '+pin)
    if oral is None:
        samples={}
        for sem,tex in textures.items():
            samples[sem]=node(u.MaterialExpressionTextureSampleParameter2D,parameter_name=sem,texture=tex,
                sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if sem=='Normal' else
                u.MaterialSamplerType.SAMPLERTYPE_COLOR if sem=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        base=(samples['BaseColor'],'RGB');normal=(samples['Normal'],'RGB')
        rough=(samples['MetallicRoughness'],'G')
        mask=node(u.MaterialExpressionCustom,code='return saturate((C.g-C.r*0.78)*12.0)*saturate((C.g-0.045)*10.0)*0.45;',output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
        pin=u.CustomInput();pin.set_editor_property('input_name','C');mask.set_editor_property('inputs',[pin]);wire(*base,mask,'C')
        opacity=(mask,'')
    else:
        color,roughness=oral
        base=(node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*color,1)), '')
        normal=None;rough=(node(u.MaterialExpressionConstant,r=roughness),'')
        opacity=None
    zero=(node(u.MaterialExpressionConstant,r=0.),'')
    spec=(node(u.MaterialExpressionConstant,r=.3 if oral is None else .4),'')
    substrate=node(u.MaterialExpressionSubstrateShadingModels,shading_model_override=shading)
    if oral is None:substrate.set_editor_property('subsurface_profile',profile)
    inputs=[(base,u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),(rough,u.MaterialProperty.MP_ROUGHNESS,'Roughness'),
            (zero,u.MaterialProperty.MP_METALLIC,'Metallic'),(spec,u.MaterialProperty.MP_SPECULAR,'Specular')]
    if normal:inputs.append((normal,u.MaterialProperty.MP_NORMAL,'Normal'))
    if opacity:
        inputs.append((opacity,u.MaterialProperty.MP_OPACITY,'Opacity'))
        inputs.append(((node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.6,.32,.18,1)),''),u.MaterialProperty.MP_SUBSURFACE_COLOR,'Subsurface Color'))
    for (n,out),prop,pin in inputs:
        if not MEL.connect_material_property(n,out,prop):raise RuntimeError('Material property '+str(prop))
        wire(n,out,substrate,pin)
    if not MEL.connect_material_property(substrate,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate front material')
    MEL.layout_material_expressions(mat)
    errors=MEL.recompile_material(mat)
    if errors:raise RuntimeError('Material compile '+str(errors))
    save(mat);return mat

materials=[material_graph('M_InfectedDogMeshy_Skin'),
           material_graph('M_InfectedDogMeshy_Oral',((.11,.018,.023),.32)),
           material_graph('M_InfectedDogMeshy_Teeth',((.68,.60,.44),.3))]

options=u.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False
options.import_materials=False;options.import_textures=False;options.create_physics_asset=True
data=options.skeletal_mesh_import_data
data.set_editor_property('update_skeleton_reference_pose',False)
data.set_editor_property('use_t0_as_ref_pose',False)
data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
data.set_editor_property('normal_generation_method',u.FBXNormalGenerationMethod.MIKK_T_SPACE)
task=u.AssetImportTask();task.filename=str(ROOT/'SK_InfectedDog_MeshyV2.fbx')
task.destination_path=DEST;task.destination_name='SK_InfectedDog_MeshyV2'
task.options=options;task.automated=True;task.save=False;task.replace_existing=True
cvar='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(cvar)
u.SystemLibrary.execute_console_command(None,cvar+' 0')
try:
    TOOLS.import_asset_tasks([task])
    mesh=load(DEST+'/SK_InfectedDog_MeshyV2');skeleton=mesh.get_editor_property('skeleton')
    slots=list(mesh.get_editor_property('materials'))
    for i,slot in enumerate(slots):slot.material_interface=materials[i];slots[i]=slot
    mesh.set_editor_property('materials',slots)
    mesh.set_editor_property('enable_per_poly_collision',False)
    subsystem=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    settings=subsystem.get_lod_build_settings(mesh,0)
    settings.set_editor_property('recompute_normals',False)
    settings.set_editor_property('recompute_tangents',True)
    settings.set_editor_property('use_mikk_t_space',True)
    settings.set_editor_property('use_full_precision_u_vs',True)
    subsystem.set_lod_build_settings(mesh,0,settings)
    # Generate two distant LODs; keep the authored close-up surface intact.
    lod_factory=u.DataAssetFactory()
    lod_factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings.static_class())
    lod_settings,lod_new=create('LOD_InfectedDogMeshy',u.SkeletalMeshLODSettings,lod_factory)
    infos=[]
    for percent,screen in [(1.,1.),(.45,.45),(.16,.18)]:
        info=u.SkeletalMeshLODGroupSettings()
        reduction=info.get_editor_property('reduction_settings')
        reduction.set_editor_property('num_of_triangles_percentage',percent)
        reduction.set_editor_property('base_lod',0)
        reduction.set_editor_property('max_bones_per_vertex',4)
        info.set_editor_property('reduction_settings',reduction)
        value=info.get_editor_property('screen_size');value.set_editor_property('default',screen)
        info.set_editor_property('screen_size',value);infos.append(info)
    lod_settings.set_editor_property('lod_groups',infos)
    save(lod_settings)
    mesh.set_editor_property('lod_settings',lod_settings)
    if not subsystem.regenerate_lod(mesh,3,False,False):raise RuntimeError('Could not generate canine LODs')
    physics=mesh.get_editor_property('physics_asset')
    if physics is None:physics=subsystem.create_physics_asset(mesh,True,0)
    if physics is None:raise RuntimeError('No target physics asset was generated')
    marked(mesh);marked(skeleton);marked(physics)
    save(physics);save(skeleton);save(mesh)
    report.update(mesh=mesh.get_path_name(),skeleton=skeleton.get_path_name(),physics=physics.get_path_name(),lod_count=3)
    record()
    for role,row in ANIMS['clips'].items():
        name='A_InfectedDogMeshy_'+role
        op=u.FbxImportUI();op.automated_import_should_detect_type=False
        op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True
        op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
        ad=op.anim_sequence_import_data
        ad.set_editor_property('use_default_sample_rate',False)
        ad.set_editor_property('custom_sample_rate',60)
        ad.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        ad.set_editor_property('remove_redundant_keys',False)
        t=u.AssetImportTask();t.filename=row['file'];t.destination_name=name;t.destination_path=DEST+'/Animations'
        t.options=op;t.automated=True;t.save=False;t.replace_existing=True
        TOOLS.import_asset_tasks([t])
        imported=[u.load_asset(p) for p in t.imported_object_paths]
        clip=next((a for a in imported if isinstance(a,u.AnimSequence)),None)
        if clip is None:raise RuntimeError('Animation import failed '+role)
        clip.set_editor_property('enable_root_motion',False)
        clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.ANIM_FIRST_FRAME)
        clip.set_editor_property('rate_scale',1.)
        clip.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(numerator=60,denominator=1))
        clip.set_preview_skeletal_mesh(mesh)
        # Animation-only FBX import strips Blender's Armature container but
        # omits its unit scale from the root keys. Match the existing bind root.
        report.setdefault('animation_root_units', {})[role]=match_bind_root_scale(clip,mesh)
        marked(clip);save(clip);report['animations'][role]=clip.get_path_name();record()
finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(previous))

path=DEST+'/DA_InfectedDogMeshy_AnimationSet'
reference_set=load('/Game/Monsters/Wolf/DA_Wolf_AnimationSet')
dataset=load(path) if LIB.does_asset_exist(path) else TOOLS.duplicate_asset('DA_InfectedDogMeshy_AnimationSet',DEST,reference_set)
if dataset is None:raise RuntimeError('Could not copy current canine action contracts')
actions=dataset.get_editor_property('actions')
for role,clip_path in report['animations'].items():
    action=actions[role];action.set_editor_property('sequence',load(clip_path));actions[role]=action
dataset.set_editor_property('actions',actions);dataset.set_editor_property('reference_mesh',mesh)
# Re-running the installer must not compound the authored stride multiplier.
dataset.set_editor_property('walk_speed',reference_set.get_editor_property('walk_speed')*ANIMS['stride_scale'])
dataset.set_editor_property('run_speed',reference_set.get_editor_property('run_speed')*ANIMS['stride_scale'])
marked(dataset);save(dataset)
# Only activate after the complete saved dependency set is available.
u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class());cdo.set_editor_property('animation_set',dataset)
component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh)
component.set_editor_property('override_materials',materials)
component.set_anim_instance_class(u.QuadrupedTemplateAnimInstance.static_class())
cdo.get_editor_property('wound_appearance').set_editor_property('enabled',False)
marked(bp);save(bp)
report.update(state='assets_saved_and_infected_dog_bound',blueprint=BP_PATH,
    animation_set=dataset.get_path_name(),head_attack_anchor='Wolf_-Head',
    original_run_preserved=True,source_actions_retargeted=len(report['animations']),
    six_attributes_and_infection_unchanged=True,preview_rendered=False,runtime_tested=False)
record();u.log('MESHY_CANINE_COMPLETED_SAVED '+BP_PATH)
