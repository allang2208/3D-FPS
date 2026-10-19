"""Save new animation packages in the isolated host, without launching gameplay."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
DEST='/Game/Weapons/Zhanmadao20261018/ChixiaoDoubleHeavyV1'
author=json.loads((P/'authoring.json').read_text('utf-8'))
lib=u.EditorAssetLibrary;tools=u.AssetToolsHelpers.get_asset_tools()
receipt={'assets':[],'runtime_tested':False,'rendered':False,'clips':{}}
for variant,info in author['clips'].items():
    # Keep the current, user-requested hand repair when rebuilding this action.
    revised=P.parent/'ChixiaoGripV2'/variant/'editable_keys.json'
    shoulder=P.parent/'ChixiaoShoulderV3'/variant/'editable_keys.json'
    if shoulder.exists():revised=shoulder
    if variant!='Body' and revised.exists():info=dict(info,keys=str(revised))
    data=json.loads(Path(info['keys']).read_text('utf-8'));samples=data['samples']
    factory=u.AnimSequenceFactory();factory.set_editor_property('target_skeleton',u.load_asset(data['skeleton']))
    name='A_Chixiao_DoubleHeavy_'+variant;path=DEST+'/'+name
    if lib.does_asset_exist(path):raise RuntimeError('Preserving existing candidate '+path)
    asset=tools.create_asset(name,DEST,u.AnimSequence,factory)
    if not asset:raise RuntimeError('Cannot create '+path)
    ctrl=asset.get_editor_property('controller');ctrl.open_bracket('Chixiao double heavy authored motion',False)
    try:
        ctrl.set_frame_rate(u.FrameRate(data['fps'],1),False)
        ctrl.set_number_of_frames(u.FrameNumber(len(samples)-1),False)
        for bone in samples[0]['bones']:
            ctrl.add_bone_curve(bone,False);keys=[s['bones'][bone] for s in samples]
            if not ctrl.set_bone_track_keys(bone,[u.Vector(*k['p']) for k in keys],
                    [u.Quat(k['q'][1],k['q'][2],k['q'][3],k['q'][0]) for k in keys],
                    [u.Vector(*k['s']) for k in keys],False):raise RuntimeError('Cannot write '+bone)
    finally:ctrl.close_bracket(False)
    if variant!='Body':
        asset.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(data['fps'],1))
        asset.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    asset.set_editor_property('enable_root_motion',False)
    asset.set_editor_property('force_root_lock',variant=='Body')
    u.AnimationLibrary.add_animation_notify_track(asset,'ChixiaoTiming')
    for marker,time in [('Contact',.0375),('Release',.30),('SecondCutStart',.18)]:
        u.AnimationLibrary.add_animation_sync_marker(asset,marker,time,'ChixiaoTiming')
    # Both body donors already carry their native two-hand sword grip.
    if variant=='Body':u.AnimationLibrary.add_animation_sync_marker(asset,'NativeSwordGrip',0.,'ChixiaoTiming')
    lib.set_metadata_tag(asset,'Chixiao.AuthorSource',info['keys'])
    lib.set_metadata_tag(asset,'Chixiao.Provenance','Current installed heavy release plus V15 supported uppercut reference; original V7 native binding')
    lib.set_metadata_tag(asset,'Chixiao.Timing','0-.075 first heavy; .18-.30 upward-right heavy; one-second release')
    if not lib.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+path)
    receipt['assets'].append(asset.get_path_name());receipt['clips'][variant]=asset.get_path_name()
    if variant=='Body':receipt['body_asset']=asset.get_path_name()
    # Retain a portable export alongside the editable source and exact native keys.
    task=u.AssetExportTask();task.object=asset;task.filename=str(P/variant/(name+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export '+path)
    print('CHIXIAO_DOUBLE_HEAVY_SAVED',path,flush=True)
receipt['staged_assets_saved']=True
(P/'assets-saved.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
