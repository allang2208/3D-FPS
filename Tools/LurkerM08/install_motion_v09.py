"""Import the two M08 V09 actions, bind oral support samples and save speed."""
import ast, json, shutil, traceback, hashlib
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/Monsters/LurkerM08/MotionV09_20261005'
BASE='/Game/Monsters/LurkerM08';DEST=BASE+'/MotionV09';REV='M08_MotionV09_20261005'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
SOURCE=json.loads((ROOT/'authoring.json').read_text(encoding='utf-8'))
MOUTH=json.loads((ROOT/'mouth_binding.json').read_text(encoding='utf-8'))
REPORT={'revision':REV,'state':'importing','saved':[],'animations':{},'runtime_tested':False,'rendered':False}

def record():(ROOT/'installation.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    value=u.load_asset(path)
    if value is None:raise RuntimeError('Missing asset '+path)
    return value
def save(asset):
    LIB.set_metadata_tag(asset,'M08.MotionRevision',REV)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in REPORT['saved']:REPORT['saved'].append(asset.get_path_name())
    record()

module=ast.parse((PROJECT/'Tools/LurkerM08/install_lurker.py').read_text(encoding='utf-8'))
fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='match_root_units')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<M08 root unit adapter>','exec'),globals())

def bind_samples(cdo,mesh,clip):
    def vec(v):return (v.x,v.y,v.z)
    def sub(a,b):return tuple(x-y for x,y in zip(a,b))
    def dot(a,b):return sum(x*y for x,y in zip(a,b))
    def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    def ue_name(name):return name.replace('.','_')
    options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,options)
    source_bones=MOUTH['calibration_bones']
    names=set(source_bones)|{w['bone'] for p in MOUTH['landmarks'] for w in p['weights']}
    refs={n:u.AnimPoseExtensions.get_ref_bone_pose(pose,ue_name(n),u.AnimPoseSpaces.WORLD) for n in names}
    src_origin=source_bones['pelvis'];dst_origin=vec(refs['pelvis'].translation)
    a=sub(source_bones['hand.L'],source_bones['hand.R']);b=sub(source_bones['chest'],src_origin);c=sub(source_bones['arch_crown'],src_origin)
    aa=sub(vec(refs['hand.L'].translation),vec(refs['hand.R'].translation));bb=sub(vec(refs['chest'].translation),dst_origin);cc=sub(vec(refs['arch_crown'].translation),dst_origin)
    determinant=dot(a,cross(b,c))
    if abs(determinant)<1e-9:raise RuntimeError('Degenerate imported reference basis')
    def imported_position(position):
        q=sub(position,src_origin)
        x=dot(q,cross(b,c))/determinant;y=dot(a,cross(q,c))/determinant;z=dot(a,cross(b,q))/determinant
        return u.Vector(*(dst_origin[i]+x*aa[i]+y*bb[i]+z*cc[i] for i in range(3)))
    samples=[]
    for row in MOUTH['landmarks']:
        vertex=u.LurkerM08RimVertex();influences=[];point=imported_position(row['position_m'])
        for weight in row['weights']:
            influence=u.LurkerM08RimInfluence()
            influence.set_editor_property('bone',ue_name(weight['bone']))
            influence.set_editor_property('bone_local_position',u.MathLibrary.inverse_transform_location(refs[weight['bone']],point))
            influence.set_editor_property('weight',weight['weight']);influences.append(influence)
        vertex.set_editor_property('influences',influences);samples.append(vertex)
    cdo.set_editor_property('mouth_support_samples',samples)
    REPORT['mouth_sample_count']=len(samples)

def run():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if package.get_name().startswith(BASE):raise RuntimeError('Preserving unsaved M08 asset '+package.get_name())
    bp=load(BASE+'/BP_LurkerM08');dataset=load(BASE+'/DA_M08_AnimationSet');mesh=load(SOURCE['mesh_asset'])
    skeleton=mesh.get_editor_property('skeleton')
    backup=ROOT/'Before';backup.mkdir(exist_ok=True)
    for name in ('BP_LurkerM08.uasset','DA_M08_AnimationSet.uasset'):
        if not (backup/name).exists():shutil.copy2(PROJECT/'Content/Monsters/LurkerM08'/name,backup/name)
    actions={str(k):v for k,v in dataset.get_editor_property('actions').items()}
    before=ROOT/'before_references.json'
    if not before.exists():before.write_text(json.dumps({'actions':{k:v.sequence.get_path_name() if v.sequence else None for k,v in actions.items()}},indent=2),encoding='utf-8')
    cvar='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None,cvar+' 0')
    try:
        for role,row in SOURCE['clips'].items():
            name='A_M08_'+role+'_MotionV09';path=DEST+'/Animations/'+name
            clip=u.load_asset(path) if LIB.does_asset_exist(path) else None
            if clip and LIB.get_metadata_tag(clip,'M08.MotionRevision')!=REV:raise RuntimeError('Preserving unrelated asset '+path)
            digest=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()
            if clip is None or LIB.get_metadata_tag(clip,'M08.SourceFBXHash')!=digest:
                op=u.FbxImportUI();op.automated_import_should_detect_type=False
                op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
                op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True
                op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
                ad=op.anim_sequence_import_data
                ad.set_editor_property('use_default_sample_rate',False);ad.set_editor_property('custom_sample_rate',120)
                ad.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
                ad.set_editor_property('remove_redundant_keys',False)
                task=u.AssetImportTask();task.filename=row['file'];task.destination_name=name;task.destination_path=DEST+'/Animations'
                task.automated=True;task.save=False;task.replace_existing=clip is not None;task.options=op
                if clip:task.replace_existing_settings=True
                TOOLS.import_asset_tasks([task])
                clip=next((load(p) for p in task.imported_object_paths if isinstance(load(p),u.AnimSequence)),None)
                if clip is None:raise RuntimeError('Animation import did not return '+role)
                clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
                clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.ANIM_FIRST_FRAME)
                clip.set_editor_property('rate_scale',1.);clip.set_preview_skeletal_mesh(mesh)
                REPORT.setdefault('root_units',{})[role]=match_root_units(clip,mesh)
                LIB.set_metadata_tag(clip,'M08.SourceFBXHash',digest);save(clip)
            REPORT['animations'][role]=clip.get_path_name();record()
    finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(old))
    for role,row in SOURCE['clips'].items():
        entry=actions[role]
        for key,value in {'sequence':load(REPORT['animations'][role]),'play_rate':1.,'blend_seconds':.08,
            'contact_start_seconds':row['contact'][0],'contact_end_seconds':row['contact'][1]}.items():entry.set_editor_property(key,value)
        actions[role]=entry
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    bind_samples(cdo,mesh,load(REPORT['animations']['AttackAirCannon']))
    cdo.set_editor_property('pounce_flight_speed_multiplier',3.)
    dataset.set_editor_property('actions',actions);save(dataset);save(bp)
    REPORT.update(state='motion_v09_saved_and_bound',blueprint=bp.get_path_name(),animation_set=dataset.get_path_name(),
        pounce_flight_speed_multiplier=3.,pounce_speed_change_from_v07=1.5,
        pounce_flight_seconds='clamp(distance_cm/760 + 0.16, 0.44, 0.95) / 3',
        preserved_actions=[k for k in actions if k not in SOURCE['clips']],f6_id='LurkerM08')
    record();u.log('M08_MOTION_V09_SAVED '+bp.get_path_name())
try:run()
except Exception:
    REPORT['state']='failed';REPORT['error']=traceback.format_exc();record();raise
