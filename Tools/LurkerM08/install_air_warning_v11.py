"""Import/save the M08 charge warning, retimed action and exact runtime references."""
import ast, hashlib, json, shutil, traceback
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/Monsters/LurkerM08/AirWarningV11_20261005'
BASE='/Game/Monsters/LurkerM08';DEST=BASE+'/AirWarningV11';REV='M08_AirWarningV11_20261005'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools();MAT=u.MaterialEditingLibrary
SOURCE=json.loads((ROOT/'authoring.json').read_text(encoding='utf-8'))
REPORT={'revision':REV,'state':'importing','saved':[],'runtime_tested':False,'rendered':False}

def record():(ROOT/'installation.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    result=u.load_asset(path)
    if result is None:raise RuntimeError('Missing asset '+path)
    return result
def save(asset):
    LIB.set_metadata_tag(asset,'M08.AirWarningRevision',REV)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in REPORT['saved']:REPORT['saved'].append(asset.get_path_name())
    record()
def owned(path):
    asset=load(path) if LIB.does_asset_exist(path) else None
    if asset and LIB.get_metadata_tag(asset,'M08.AirWarningRevision')!=REV:raise RuntimeError('Preserving unrelated asset '+path)
    return asset
def imp(file,name,folder,options=None,factory=None):
    asset=owned(folder+'/'+name);digest=hashlib.sha256(Path(file).read_bytes()).hexdigest()
    if asset and LIB.get_metadata_tag(asset,'M08.SourceHash')==digest:return asset
    task=u.AssetImportTask();task.filename=str(file);task.destination_name=name;task.destination_path=folder
    task.automated=True;task.save=False;task.replace_existing=asset is not None
    if asset:task.replace_existing_settings=True
    if options:task.options=options
    if factory:task.factory=factory
    TOOLS.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('No asset imported '+str(file))
    asset=load(task.imported_object_paths[0]);LIB.set_metadata_tag(asset,'M08.SourceHash',digest)
    if isinstance(asset,u.AnimSequence):LIB.remove_metadata_tag(asset,'M08.RootUnits')
    return asset

module=ast.parse((PROJECT/'Tools/LurkerM08/install_lurker.py').read_text(encoding='utf-8'))
fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='match_root_units')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<M08 root unit adapter>','exec'),globals())

def material():
    name='M_M08_AirWarning_V11'
    m=owned(DEST+'/'+name) or TOOLS.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    MAT.delete_all_material_expressions(m)
    for key,value in {'blend_mode':u.BlendMode.BLEND_TRANSLUCENT,'shading_model':u.MaterialShadingModel.MSM_UNLIT,
        'two_sided':True,'disable_depth_test':False,'refraction_method':u.RefractionMode.RM_NONE}.items():m.set_editor_property(key,value)
    def node(kind,x,y,**props):
        result=MAT.create_material_expression(m,kind,x,y)
        for key,value in props.items():result.set_editor_property(key,value)
        return result
    inputs={'UV':node(u.MaterialExpressionTextureCoordinate,-800,0),
        'Layer':node(u.MaterialExpressionVertexColor,-800,130)}
    for index,name,default in [(0,'Visibility',1.),(1,'Progress',0.),(2,'Locked',0.)]:
        inputs[name]=node(u.MaterialExpressionScalarParameter,-800,260+index*140,
            parameter_name='AirWarning'+name,default_value=default,use_custom_primitive_data=True,primitive_data_index=index)
    custom=node(u.MaterialExpressionCustom,-350,0,description='M08 V11 readable air intake',
        output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,code=(ROOT/'AirWarning.hlsl').read_text(encoding='utf-8'))
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    custom.set_editor_property('inputs',pins)
    for name,n in inputs.items():MAT.connect_material_expressions(n,'',custom,name)
    rgb=node(u.MaterialExpressionComponentMask,20,0,r=True,g=True,b=True,a=False)
    alpha=node(u.MaterialExpressionComponentMask,20,160,r=False,g=False,b=False,a=True)
    MAT.connect_material_expressions(custom,'',rgb,'Input');MAT.connect_material_expressions(custom,'',alpha,'Input')
    MAT.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    MAT.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
    MAT.recompile_material(m);save(m);return m

def run():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if package.get_name().startswith(BASE):raise RuntimeError('Preserving unsaved M08 asset '+package.get_name())
    bp=load(BASE+'/BP_LurkerM08');dataset=load(BASE+'/DA_M08_AnimationSet');mesh=load(SOURCE['mesh_asset'])
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    # These reflected fields exist only after the regular V11 native build.
    cdo.get_editor_property('air_charge_mesh');cdo.get_editor_property('air_charge_material')
    backup=ROOT/'Before';backup.mkdir(exist_ok=True)
    for name in ('BP_LurkerM08.uasset','DA_M08_AnimationSet.uasset'):
        if not (backup/name).exists():shutil.copy2(PROJECT/'Content/Monsters/LurkerM08'/name,backup/name)
    actions={str(k):v for k,v in dataset.get_editor_property('actions').items()}
    before=ROOT/'before_references.json'
    if not before.exists():before.write_text(json.dumps({
        'actions':{k:v.sequence.get_path_name() if v.sequence else None for k,v in actions.items()},
        'air_charge_sound':cdo.get_editor_property('air_charge_sound').get_path_name()},indent=2),encoding='utf-8')
    cvar='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None,cvar+' 0')
    try:
        row=SOURCE['clips']['AttackAirCannon']
        op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True
        op.import_materials=False;op.import_textures=False;op.skeleton=mesh.get_editor_property('skeleton')
        ad=op.anim_sequence_import_data
        ad.set_editor_property('use_default_sample_rate',False);ad.set_editor_property('custom_sample_rate',120)
        ad.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        ad.set_editor_property('remove_redundant_keys',False)
        clip=imp(row['file'],'A_M08_AttackAirCannon_AirWarningV11',DEST+'/Animations',op)
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.ANIM_FIRST_FRAME)
        clip.set_editor_property('rate_scale',1.);clip.set_preview_skeletal_mesh(mesh)
        if LIB.get_metadata_tag(clip,'M08.RootUnits')!='matched':
            REPORT['root_units']=match_root_units(clip,mesh);LIB.set_metadata_tag(clip,'M08.RootUnits','matched')
        save(clip)
        op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        op.import_mesh=True;op.import_as_skeletal=False;op.import_animations=False;op.import_materials=False;op.import_textures=False
        op.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
        op.static_mesh_import_data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
        warning=imp(SOURCE['warning_mesh'],'SM_M08_AirWarning_V11',DEST,op)
    finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(previous))
    warning_material=material();warning.set_material(0,warning_material);save(warning)
    sound=imp(SOURCE['charge_audio'],'S_M08_AirWarning_Charge_V11',DEST+'/Audio',factory=u.SoundFactory())
    sound.set_editor_property('looping',False);save(sound)
    entry=actions['AttackAirCannon']
    for key,value in {'sequence':clip,'play_rate':1.,'blend_seconds':.08,
        'contact_start_seconds':1.50,'contact_end_seconds':1.50}.items():entry.set_editor_property(key,value)
    actions['AttackAirCannon']=entry;dataset.set_editor_property('actions',actions)
    for key,value in {'air_charge_mesh':warning,'air_charge_material':warning_material,'air_charge_sound':sound}.items():cdo.set_editor_property(key,value)
    save(dataset);save(bp)
    REPORT.update(state='air_warning_v11_saved_and_bound',blueprint=bp.get_path_name(),animation_set=dataset.get_path_name(),
        action=clip.get_path_name(),warning_mesh=warning.get_path_name(),warning_material=warning_material.get_path_name(),
        charge_sound=sound.get_path_name(),windup_seconds=1.5,aim_lock_seconds=1.2,aim_lock_before_release=.30,
        warning_triangles=SOURCE['warning_triangles'],source_duration_seconds=row['seconds'],
        preserved_actions=[k for k in actions if k!='AttackAirCannon'],f6_id='LurkerM08')
    record();u.log('M08_AIR_WARNING_V11_SAVED '+bp.get_path_name())
try:run()
except Exception:
    REPORT['state']='failed';REPORT['error']=traceback.format_exc();record();raise
