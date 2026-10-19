"""Save the requested grip repair to the two existing runtime animations."""
import json,shutil,math
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
L=u.EditorAssetLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('End PIE before replacing its loaded hand animations')
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
receipt={'revision':'ChixiaoGripV2','animations':{},'gameplay_tested':False,'offline_hand_check':True}
names=['WPN_root','hand_l','hand_r','lowerarm_l','lowerarm_r','index_03_l','middle_03_l','index_03_r','middle_03_r']
for variant in ('Standard','LongGrip'):
    target='/Game/Weapons/Zhanmadao20261018/ChixiaoDoubleHeavyV1/A_Chixiao_DoubleHeavy_'+variant
    if target in dirty:raise RuntimeError('Preserving unsaved animation edits: '+target)
    asset=u.load_asset(target)
    if not asset:raise RuntimeError('Missing installed motion '+target)
    keys=P/variant/'editable_keys.json';patch=json.loads(keys.read_text('utf-8'));samples=patch['samples']
    if asset.get_editor_property('skeleton').get_path_name()!=patch['skeleton']:raise RuntimeError('Native skeleton differs: '+target)
    disk=ROOT/'Content'/target[6:]
    for suffix in ('.uasset','.uexp','.ubulk'):
        source=disk.with_suffix(suffix);backup=P/'Before'/variant/source.name
        if source.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
    ctrl=asset.get_editor_property('controller');ctrl.open_bracket('Chixiao rigid grasp and supported wrist V2',False)
    try:
        ctrl.remove_all_bone_tracks(False);ctrl.set_frame_rate(u.FrameRate(patch['fps'],1),False)
        ctrl.set_number_of_frames(u.FrameNumber(len(samples)-1),False)
        for bone in samples[0]['bones']:
            ctrl.add_bone_curve(bone,False);rows=[s['bones'][bone] for s in samples]
            if not ctrl.set_bone_track_keys(bone,[u.Vector(*r['p']) for r in rows],
                [u.Quat(r['q'][1],r['q'][2],r['q'][3],r['q'][0]) for r in rows],
                [u.Vector(*r['s']) for r in rows],False):raise RuntimeError('Failed bone track '+bone)
    finally:ctrl.close_bracket(False)
    rate=asset.get_editor_property('platform_target_frame_rate')
    previous_rate=str(rate.get_editor_property('default'))
    rate.set_editor_property('default',u.FrameRate(patch['fps'],1))
    compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    if not compression:raise RuntimeError('Missing native viewmodel compression settings')
    asset.set_editor_property('bone_compression_settings',compression)
    L.set_metadata_tag(asset,'Chixiao.AuthorSource',str(keys));L.set_metadata_tag(asset,'Chixiao.HandRevision','ChixiaoGripV2')
    L.set_metadata_tag(asset,'Chixiao.GripMethod','Rigid full-finger grasp; shaft-circle return; supported shoulder/elbow and distributed forearm twist; blade path and clocks retained')
    if not L.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+target)
    task=u.AssetExportTask();task.object=asset;task.filename=str(P/variant/(target.rsplit('/',1)[1]+'_GripV2.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('FBX export failed '+target)
    # Read only the requested hands in the saved source and compressed poses.
    max_position=0.;max_angle=0.
    for t in (.12,.15,.18,.21,.24,.27,.30,.38,.5,.7,.9,1.):
        poses=[]
        for kind in (u.AnimDataEvalType.SOURCE,u.AnimDataEvalType.COMPRESSED):
            options=u.AnimPoseEvaluationOptions();options.evaluation_type=kind
            poses.append(u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,options))
        for bone in names:
            a,b=[u.AnimPoseExtensions.get_bone_pose(p,bone,u.AnimPoseSpaces.WORLD) for p in poses]
            pa,pb=a.translation,b.translation
            max_position=max(max_position,math.sqrt((pa.x-pb.x)**2+(pa.y-pb.y)**2+(pa.z-pb.z)**2))
            qa,qb=a.rotation,b.rotation;dot=abs(qa.x*qb.x+qa.y*qb.y+qa.z*qb.z+qa.w*qb.w)
            max_angle=max(max_angle,math.degrees(2*math.acos(min(1.,dot))))
    receipt['animations'][variant]={'asset':asset.get_path_name(),'saved':True,'author_keys':str(keys),
        'source_compressed_max_position_cm':max_position,'source_compressed_max_angle_degrees':max_angle,
        'platform_rate':str(asset.get_editor_property('platform_target_frame_rate').get_editor_property('default')),
        'previous_platform_rate':previous_rate,
        'compression':compression.get_path_name()}
    (P/'install-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('CHIXIAO_GRIP_SAVED',variant,max_position,max_angle,flush=True)
    if max_position>.1 or max_angle>1.:raise RuntimeError('Saved hand compression differs from source: '+variant)
receipt['complete']=True
(P/'install-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
