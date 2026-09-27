"""Install V82 Inspect only, with the current closer idle restored before saving."""
import ast,hashlib,json,math,shutil
from pathlib import Path
import unreal as u

P=Path(__file__).parent
ROOT=Path(u.Paths.project_dir()).resolve()
IDLE_SOURCE=ROOT/'SourceAssets/SwordIdleClose20260926'
NAME='A_RuneSword_Inspect'
REVISION='InspectFollowThroughV82'
tree=ast.parse((IDLE_SOURCE/'author_idle_close.py').read_text(encoding='utf-8'))
helpers=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name not in ('sample','asset_path')]
exec(compile(ast.Module(body=helpers,type_ignores=[]),'supported_idle_math','exec'),globals())
IDENTITY={'p':(0,0,0),'q':(0,0,0,1),'s':(1,1,1)}
TARGETS=[('Standard','/Game/Weapons/AzureRunesword20260913',P/'ExportV82'/f'{NAME}.fbx'),
         ('LongGrip','/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations',P/'ExportV82/LongGrip'/f'{NAME}.fbx')]
baseline={row['variant']:row['after_sha256'] for row in
    json.loads((P.parent/'InspectDownstrokeV81/import_receipt_v81.json').read_text())['assets']}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
mesh=u.load_asset('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
names=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
parents={n:str(component.get_parent_bone(n)) for n in names}
edited=[n for n in names if n=='WPN_root' or any(n==stem+'_'+side for side in ('r','l') for stem in
        ('upperarm','lowerarm','hand','upperarm_twist_01','upperarm_twist_02','lowerarm_twist_01','lowerarm_twist_02'))]
needed=list(dict.fromkeys(edited+[parents[n] for n in edited if parents[n]!='None']))
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE
options.optional_skeletal_mesh=mesh

def sample(sequence,t):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(sequence,t,options)
    world={n:unpack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in needed}
    local={n:unpack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in edited}
    return world,local

def restore_idle(sequence,idle,variant):
    source_idle,_=sample(sequence,0)
    target_idle,target_keys=sample(idle,0)
    offset=sub(target_idle['WPN_root']['p'],source_idle['WPN_root']['p'])
    frames=sequence.get_editor_property('data_model_interface').get_number_of_frames()
    seconds=sequence.get_play_length()
    end_world,_=sample(sequence,seconds)
    start_gate=1.;end_gate=proximity(end_world,source_idle)
    rows=[];previous={}
    for frame in range(frames+1):
        t=frame*seconds/frames
        world,local=sample(sequence,t)
        boundary=max(start_gate*(1-smooth(t/.20)),end_gate*smooth((t-(seconds-.28))/.28))
        weight=boundary*proximity(world,source_idle)
        keys={n:dict(k) for n,k in local.items()}
        if weight>1e-6:
            desired,_=solve_pose(world,mul(offset,weight),weight,parents,edited)
            for n in edited:
                keys[n]=relative(desired[n],desired.get(parents[n],IDENTITY))
                keys[n]['s']=local[n]['s']
        if frame in (0,frames):
            # Exact current-family endpoint, including its supported elbow pose.
            keys={n:dict(k) for n,k in target_keys.items()}
        for n,k in keys.items():
            if n in previous and dot(k['q'],previous[n])<0:k['q']=mul(k['q'],-1)
            previous[n]=k['q']
        rows.append({'seconds':t,'posture_weight':weight,'bones':keys})
    controller=sequence.get_editor_property('controller')
    controller.open_bracket('V82 Inspect handoff to the installed supported idle',False)
    try:
        for n in edited:
            keys=[r['bones'][n] for r in rows]
            if not controller.set_bone_track_keys(n,[u.Vector(*k['p']) for k in keys],
                    [u.Quat(*k['q']) for k in keys],[u.Vector(*k['s']) for k in keys],False):
                raise RuntimeError('Could not write handoff track '+n)
    finally:controller.close_bracket(False)
    out=P/'Final'/variant;out.mkdir(parents=True,exist_ok=True)
    keys_file=out/'Inspect_idle_handoff_keys.json'
    keys_file.write_text(json.dumps({'asset':sequence.get_path_name(),'revision':REVISION,'frames':frames,
        'seconds':seconds,'offset_cm':offset,'edited_bones':edited,'samples':rows},separators=(',',':')),encoding='utf-8')
    export=u.AssetExportTask();export.object=sequence;export.filename=str(out/f'{NAME}.fbx')
    export.automated=True;export.prompt=False;export.replace_identical=True;export.options=u.FbxExportOption()
    if not u.Exporter.run_asset_export_task(export):raise RuntimeError('Final FBX export failed')
    import_data=sequence.get_editor_property('asset_import_data')
    if import_data:import_data.scripted_add_filename(export.filename,0,'V82 with current idle handoff')
    # Source provenance is recorded below and in AssetImportData. The generic
    # metadata API is unavailable during PIE; no play-session change is needed.
    return {'frames':frames,'seconds':seconds,'idle_offset_cm':offset,'full_fbx':export.filename,'handoff_keys':str(keys_file)}

receipt_path=P/'import_receipt_v82.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {
    'revision':REVISION,'spin_speed_relative_to_v80':1.25,'spin_window_seconds':[.4,.8224],
    'assets':[],'runtime_tested':False,'post_change_rendered':False}
saved={row['variant']:row for row in receipt['assets'] if row.get('saved')}
for variant,dest,source in TARGETS:
    path=dest+'/'+NAME
    if path in dirty:raise RuntimeError('Unsaved target retained: '+path)
    if not source.exists():raise RuntimeError('Missing authored FBX '+str(source))
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Installed Inspect missing: '+path)
    disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    if variant in saved:
        if hashlib.sha256(disk.read_bytes()).hexdigest()!=saved[variant]['after_sha256']:
            raise RuntimeError('Previously saved Inspect changed; retained: '+path)
        continue
    if hashlib.sha256(disk.read_bytes()).hexdigest()!=baseline[variant]:
        raise RuntimeError('Inspect changed since the V81 save; retained: '+path)

flag='Interchange.FeatureFlags.Import.FBX'
previous_flag=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    for variant,dest,source in TARGETS:
        path=dest+'/'+NAME;current=u.load_asset(path)
        if variant in saved:continue
        disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        before_hash=hashlib.sha256(disk.read_bytes()).hexdigest()
        backup=P/'BeforeV82'/variant/(NAME+'.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(disk,backup)
        compression=current.get_editor_property('bone_compression_settings')
        ui=u.FbxImportUI();ui.automated_import_should_detect_type=False
        ui.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        ui.import_mesh=False;ui.import_animations=True;ui.import_materials=False;ui.import_textures=False
        ui.skeleton=mesh.skeleton
        ui.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        ui.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
        task=u.AssetImportTask();task.filename=str(source);task.destination_path=dest;task.destination_name=NAME
        task.automated=True;task.replace_existing=True;task.save=False;task.options=ui
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        sequence=u.load_asset(path)
        if not task.imported_object_paths or not sequence:raise RuntimeError('Import failed '+path)
        if compression:sequence.set_editor_property('bone_compression_settings',compression)
        authored=restore_idle(sequence,u.load_asset(dest+'/A_RuneSword_Idle'),variant)
        sequence.modify()
        if not u.EditorLoadingAndSavingUtils.save_packages([sequence.get_package()],False):
            raise RuntimeError('Could not save '+path)
        receipt['assets'].append({'variant':variant,'asset':path,'author_fbx':str(source),'backup':str(backup),
            'saved':True,'before_sha256':before_hash,'after_sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),**authored})
        receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        print('INSPECT_V82_SAVED',variant,path,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous_flag))
receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('INSPECT_V82_COMPLETE',len(receipt['assets']),flush=True)
