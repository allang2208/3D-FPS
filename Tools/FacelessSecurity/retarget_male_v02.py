"""Prepare native male action retargets and pose inputs for offline authoring."""
import unreal as u,json,shutil
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V02')
for d in ['Native','Motion','Logs','Before']:(ROOT/d).mkdir(parents=True,exist_ok=True)
DEST='/Game/Monsters/FacelessSecurity';RIG=DEST+'/Rig/V02';RAW=DEST+'/Animations/V02Raw'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; preserve session')
bp=u.load_asset(DEST+'/BP_FacelessSecurity');u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class());target=cdo.get_editor_property('visual_mesh')
previous={p:(cdo.get_editor_property(p).get_path_name() if p.endswith('_clip') else cdo.get_editor_property(p)) for p in ['idle_clip','walk_clip','attack_clip','walk_speed','contact_time','contact_end','recovery_time']}
(ROOT/'Before/previous_state.json').write_text(json.dumps(previous,indent=2),encoding='utf-8')
backup=ROOT/'Before/BP_FacelessSecurity.uasset'
if not backup.exists():shutil.copy2('D:/FPS3D/FPSGAME/Content/Monsters/FacelessSecurity/BP_FacelessSecurity.uasset',backup)
chains={'Spine':('spine_01','spine_05'),'Neck':('neck_01','neck_02'),'Head':('head','head')}
for side,label in [('l','Left'),('r','Right')]:
    for chain,start,end in [('Clavicle','clavicle','clavicle'),('Arm','upperarm','hand'),('Leg','thigh','foot'),('Toe','ball','ball')]:
        chains[chain+label]=(start+'_'+side,end+'_'+side)
    for finger in ['thumb','index','middle','ring','pinky']:chains[finger+label]=(finger+'_01_'+side,finger+'_03_'+side)
def save(a):
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def create(name,cls,factory):
    return u.load_asset(RIG+'/'+name) if LIB.does_asset_exist(RIG+'/'+name) else AT.create_asset(name,RIG,cls,factory)
def rig(name,mesh):
    a=create(name,u.IKRigDefinition,u.IKRigDefinitionFactory());ctl=u.IKRigController.get_controller(a)
    ctl.set_skeletal_mesh(mesh);ctl.set_retarget_root('pelvis');existing={str(c.chain_name) for c in ctl.get_retarget_chains()}
    for chain,(start,end) in chains.items():
        if chain not in existing:ctl.add_retarget_chain(chain,start,end,'')
    save(a);return a
dst=rig('IK_Security_V02',target)
sources={
    'Jason':('/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body',{'idle':'/Game/AsianMale_Jason/Demo/Animation/AS_Jason_Idle','walk':'/Game/AsianMale_Jason/Demo/Animation/AS_Jason_Walk_Fwd'}),
    'Manny':('/Game/ZombieAnimationPack/Demo/EpicContent/Mannequin_UE5/Meshes/SK_Manny_Simple',{'attack':'/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Attack_D'})}
component=u.new_object(u.SkeletalMeshComponent);component.set_skeletal_mesh_asset(target)
bones=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.RAW;options.optional_skeletal_mesh=target
def pack(t):return {'translation_cm':[t.translation.x,t.translation.y,t.translation.z],'rotation_xyzw':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w]}
report={'version':'V02','target_mesh':target.get_path_name(),'target_skeleton':target.get_editor_property('skeleton').get_path_name(),'clips':{},'tested':False,'rendered':False}
for family,(mesh_path,clips) in sources.items():
    source=u.load_asset(mesh_path)
    if not source:raise RuntimeError('Missing male source mesh '+mesh_path)
    src=rig('IK_'+family+'_SecuritySource',source)
    rtg=create('RTG_'+family+'_Security_V02',u.IKRetargeter,u.IKRetargetFactory());ctl=u.IKRetargeterController.get_controller(rtg)
    ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,src);ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET,dst)
    ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source);ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
    if ctl.get_num_retarget_ops()==0:ctl.add_default_ops()
    ctl.auto_map_chains(u.AutoMapChainType.EXACT,True)
    for i in range(ctl.get_num_retarget_ops()):
        op=ctl.get_op_controller(i)
        if isinstance(op,u.IKRetargetFKChainsController):
            settings=op.get_settings();rows=list(settings.chains_to_retarget)
            for row in rows:
                if str(row.target_chain_name).startswith(('Arm','Leg','thumb','index','middle','ring','pinky')):row.rotation_mode=u.FKChainRotationMode.ONE_TO_ONE
            settings.chains_to_retarget=rows;op.set_settings(settings)
    pose=ctl.create_retarget_pose('Security_MaleAligned',u.RetargetSourceOrTarget.TARGET)
    ctl.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET);ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET);save(rtg)
    for role,path in clips.items():
        clip=u.load_asset(path)
        if not clip:raise RuntimeError('Missing male animation '+path)
        params=u.IKRetargetBatchOperationInputs();params.assets_to_retarget=[LIB.find_asset_data(path)]
        params.source_mesh=source;params.target_mesh=target;params.ik_retarget_asset=rtg
        params.search=clip.get_name();params.replace='A_Security_Raw_V02_'+role;params.target_path=RAW
        params.include_referenced_assets=False;params.overwrite_existing_files=True
        results=u.IKRetargetBatchOperation.run_batch_retarget(params)
        result=next((a.get_asset() for a in results if isinstance(a.get_asset(),u.AnimSequence)),None)
        if not result:raise RuntimeError('Native retarget produced no animation: '+role)
        result.set_preview_skeletal_mesh(target);result.set_editor_property('enable_root_motion',False);result.set_editor_property('force_root_lock',False);save(result)
        duration=result.get_play_length();frames=[]
        for i in range(round(duration*60)+1):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(result,min(i/60,duration),options)
            frames.append({b:pack(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones})
        reference={b:pack(u.AnimPoseExtensions.get_ref_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones}
        dest=ROOT/'Native'/('native_'+role+'.json')
        dest.write_text(json.dumps({'asset':result.get_path_name(),'fps':60,'reference':reference,'frames':frames}),encoding='utf-8')
        task=u.AssetExportTask();task.object=result;task.filename=str(ROOT/'Native'/('A_Security_Raw_V02_'+role+'.fbx'))
        task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.AnimSequenceExporterFBX()
        export_options=u.FbxExportOption();export_options.set_editor_property('export_preview_mesh',False);task.options=export_options
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('FBX export failed '+role)
        report['clips'][role]={'source':path,'source_mesh':mesh_path,'source_duration':clip.get_play_length(),'raw_asset':result.get_path_name(),'duration':duration,'pose_cache':str(dest),'fbx':task.filename,'retargeter':rtg.get_path_name(),'frames':len(frames)}
        (ROOT/'native_retarget.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('SECURITY_MALE_NATIVE_SAVED '+json.dumps({r:{'source':x['source'],'duration':x['duration'],'frames':x['frames']} for r,x in report['clips'].items()}),flush=True)
