"""Save M08's new dorsal air-cannon action, VFX/audio and native defaults."""
import ast, json, shutil, traceback, hashlib
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/Monsters/LurkerM08/AirCannonV06_20261004'
BASE='/Game/Monsters/LurkerM08';DEST=BASE+'/AirCannonV06';REV='M08_AirCannonV06_20261004'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools();MAT=u.MaterialEditingLibrary
SOURCE=json.loads((ROOT/'authoring.json').read_text(encoding='utf-8'))
REPORT={'revision':REV,'state':'importing','saved':[],'runtime_tested':False,'rendered':False}
def record():(ROOT/'installation.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if asset is None:raise RuntimeError('Missing asset '+path)
    return asset
def save(asset):
    LIB.set_metadata_tag(asset,'M08.AirCannonRevision',REV)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in REPORT['saved']:REPORT['saved'].append(asset.get_path_name())
    record()
def owned(path):
    asset=load(path) if LIB.does_asset_exist(path) else None
    if asset and LIB.get_metadata_tag(asset,'M08.AirCannonRevision')!=REV:raise RuntimeError('Preserving unrelated asset '+path)
    return asset
def create(name,kind,factory):
    return owned(DEST+'/'+name) or TOOLS.create_asset(name,DEST,kind,factory)
def imp(file,name,folder,options=None,factory=None):
    old=owned(folder+'/'+name)
    digest=hashlib.sha256(Path(file).read_bytes()).hexdigest()
    if old and LIB.get_metadata_tag(old,'M08.SourceHash')==digest:return old
    task=u.AssetImportTask();task.filename=str(file);task.destination_name=name;task.destination_path=folder
    task.automated=True;task.save=False;task.replace_existing=old is not None
    if old:task.replace_existing_settings=True
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

def pressure_material():
    m=create('M_M08_AirPressure',u.Material,u.MaterialFactoryNew())
    # This revision owns the whole new material; no existing monster skin edits.
    MAT.delete_all_material_expressions(m)
    for key,value in {'blend_mode':u.BlendMode.BLEND_TRANSLUCENT,'shading_model':u.MaterialShadingModel.MSM_UNLIT,
        'two_sided':False,'disable_depth_test':False,'refraction_method':u.RefractionMode.RM_NONE}.items():m.set_editor_property(key,value)
    def node(kind,x,y):return MAT.create_material_expression(m,kind,x,y)
    uv=node(u.MaterialExpressionTextureCoordinate,-800,0)
    time=node(u.MaterialExpressionTime,-800,180)
    strength=node(u.MaterialExpressionScalarParameter,-800,360)
    for key,value in {'parameter_name':'PressureVisibility','default_value':1.,'use_custom_primitive_data':True,'primitive_data_index':0}.items():strength.set_editor_property(key,value)
    opacity=node(u.MaterialExpressionCustom,-400,0)
    opacity.set_editor_property('description','M08 Air V06 pressure breakup')
    opacity.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    opacity.set_editor_property('code',
        'float a=UV.x*6.2831853; float eddy=.68+.20*sin(a*7+Clock*13)+.12*sin(a*13-Clock*19); '
        'float rim=.32+.68*pow(abs(cos(UV.y*6.2831853)),.7); return saturate(Strength*eddy*rim*.62);')
    inputs=[]
    for name in ('UV','Clock','Strength'):
        row=u.CustomInput();row.set_editor_property('input_name',name);inputs.append(row)
    opacity.set_editor_property('inputs',inputs)
    for n,pin in ((uv,'UV'),(time,'Clock'),(strength,'Strength')):MAT.connect_material_expressions(n,'',opacity,pin)
    color=node(u.MaterialExpressionConstant3Vector,-250,250);color.set_editor_property('constant',u.LinearColor(.58,.67,.70,1.))
    MAT.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    MAT.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
    MAT.recompile_material(m);save(m);return m

def run():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if u.load_class(None,'/Script/FPSGAME.M08AirCannonProjectile') is None:raise RuntimeError('Build M08 air-cannon native code first')
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if package.get_name().startswith(BASE):raise RuntimeError('Preserving unsaved M08 asset '+package.get_name())
    bp=load(BASE+'/BP_LurkerM08');dataset=load(BASE+'/DA_M08_AnimationSet');mesh=load(SOURCE['mesh_asset'])
    skeleton=mesh.get_editor_property('skeleton')
    backup=ROOT/'Before';backup.mkdir(exist_ok=True)
    for name in ('BP_LurkerM08.uasset','DA_M08_AnimationSet.uasset'):
        if not (backup/name).exists():shutil.copy2(PROJECT/'Content/Monsters/LurkerM08'/name,backup/name)
    before=ROOT/'before_references.json'
    if not before.exists():before.write_text(json.dumps({'mesh':dataset.reference_mesh.get_path_name(),
        'actions':{str(k):v.sequence.get_path_name() if v.sequence else None for k,v in dataset.actions.items()}},ensure_ascii=False,indent=2),encoding='utf-8')
    cvar='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None,cvar+' 0')
    try:
        row=SOURCE['clips']['AttackAirCannon']
        op=u.FbxImportUI();op.automated_import_should_detect_type=False
        op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True
        op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
        ad=op.anim_sequence_import_data
        ad.set_editor_property('use_default_sample_rate',False);ad.set_editor_property('custom_sample_rate',120)
        ad.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        ad.set_editor_property('remove_redundant_keys',False)
        clip=imp(row['file'],'A_M08_AttackAirCannon_AirV06',DEST+'/Animations',op)
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.ANIM_FIRST_FRAME)
        clip.set_editor_property('rate_scale',1.);clip.set_preview_skeletal_mesh(mesh)
        # Root repair is done only once for an unchanged imported source.
        if LIB.get_metadata_tag(clip,'M08.RootUnits')!='matched':
            REPORT['root_units']=match_root_units(clip,mesh);LIB.set_metadata_tag(clip,'M08.RootUnits','matched')
        save(clip)
        op=u.FbxImportUI();op.automated_import_should_detect_type=False
        op.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        op.import_mesh=True;op.import_as_skeletal=False;op.import_animations=False
        op.import_materials=False;op.import_textures=False
        op.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
        ring=imp(SOURCE['pressure_ring'],'SM_M08_PressureRing',DEST,op);save(ring)
    finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(old))
    material=pressure_material()
    attenuation=create('ATT_M08_AirCannon',u.SoundAttenuation,u.SoundAttenuationFactory())
    settings=attenuation.get_editor_property('attenuation')
    for key,value in {'attenuate':True,'spatialize':True,'attenuation_shape_extents':u.Vector(150,0,0),'falloff_distance':2200.}.items():settings.set_editor_property(key,value)
    attenuation.set_editor_property('attenuation',settings);save(attenuation)
    sounds={}
    for role,file in SOURCE['audio'].items():
        sounds[role]=imp(file,Path(file).stem,DEST+'/Audio',factory=u.SoundFactory())
        sounds[role].set_editor_property('looping',False);save(sounds[role])
    actions=dict(dataset.get_editor_property('actions'))
    entry=u.QuadrupedTemplateAction()
    for key,value in {'sequence':clip,'loop':False,'hold_last_pose':True,'terminal':False,
        'play_rate':1.,'blend_seconds':.12,'contact_start_seconds':.92,'contact_end_seconds':.92}.items():entry.set_editor_property(key,value)
    actions['AttackAirCannon']=entry;dataset.set_editor_property('actions',actions);save(dataset)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    defaults={'air_cannon_damage':48.,'air_cannon_stun_seconds':3.,'air_cannon_cooldown':20.,
        'air_cannon_min_range':280.,'air_cannon_range':1800.,'air_cannon_speed':1600.,
        'air_ring_mesh':ring,'air_ring_material':material,'air_charge_sound':sounds['charge'],
        'air_release_sound':sounds['release'],'air_sound_attenuation':attenuation,'animation_set':dataset}
    for key,value in defaults.items():cdo.set_editor_property(key,value)
    save(bp)
    REPORT.update(state='air_cannon_v06_saved_and_bound',blueprint=bp.get_path_name(),animation_set=dataset.get_path_name(),
        action=clip.get_path_name(),f6_id='LurkerM08',preserved_actions=[str(k) for k in actions if str(k)!='AttackAirCannon'],
        damage=48,damage_type='Physical / UEnemyRangedDamage',stun_seconds=3,cooldown_seconds=20,
        range_cm=[280,1800],speed_cm_per_second=1600,collision_radius_cm=34,
        source_release_seconds=.92,source_duration_seconds=1.85,aim_lock_before_release=.10,
        authoring_source=str(ROOT/'M08_AirCannon_Animated_V06.blend'))
    record();u.log('M08_AIR_CANNON_V06_SAVED '+bp.get_path_name())
try:run()
except Exception:
    REPORT['state']='failed';REPORT['error']=traceback.format_exc();record();raise
