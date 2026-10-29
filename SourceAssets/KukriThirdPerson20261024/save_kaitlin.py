"""Save only the new Kukri roles for the enabled native female body."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/KukriThirdPerson20261024'
DEST='/Game/Characters/JasonPlayer20261003/Kukri20261024/Kaitlin/Animations'
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
roles=json.loads((OUT/'assets-saved.json').read_text())['clips']
authored=json.loads((OUT/'adapted-actions.json').read_text())['clips']
source=u.load_asset(cfg['body_mesh']);target=u.load_asset(cfg['body_variants']['kaitlin']['body_mesh'])
rtg=u.load_asset('/Game/Characters/KaitlinPlayer20261023/Motion/Rig/RTG_Jason_Kaitlin')
if not source or not target or not rtg:raise RuntimeError('Native Kaitlin retarget inputs are unavailable')
lib=u.EditorAssetLibrary;receipt=dict(complete=False,clips={},body=target.get_path_name(),runtime_tested=False)
receipt_path=OUT/'kaitlin-assets-saved.json'
if receipt_path.exists():receipt=json.loads(receipt_path.read_text());receipt['complete']=False
for role,path in roles.items():
    if role in receipt['clips'] and lib.does_asset_exist(receipt['clips'][role]):continue
    name='K_'+path.split('.')[-1];output_path=DEST+'/'+name
    if not lib.does_asset_exist(output_path):
        inputs=u.IKRetargetBatchOperationInputs();inputs.assets_to_retarget=[lib.find_asset_data(path)]
        inputs.source_mesh=source;inputs.target_mesh=target;inputs.ik_retarget_asset=rtg
        inputs.prefix='K_';inputs.target_path=DEST;inputs.include_referenced_assets=False;inputs.overwrite_existing_files=False
        u.IKRetargetBatchOperation.run_batch_retarget(inputs)
    clip=u.load_asset(output_path);original=u.load_asset(path)
    if not isinstance(clip,u.AnimSequence):raise RuntimeError('Retarget failed: '+role)
    clip.set_preview_skeletal_mesh(target)
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
    u.AnimationLibrary.remove_all_animation_sync_markers(clip)
    u.AnimationLibrary.add_animation_notify_track(clip,'KukriNativeTiming')
    timing=authored[role.removeprefix('Kukri.FullBody.')]
    for marker,key in [('Contact','contact'),('Release','release')]:
        u.AnimationLibrary.add_animation_sync_marker(clip,marker,timing[key]*clip.get_play_length(),'KukriNativeTiming')
    lib.set_metadata_tag(clip,'KukriJasonSource',path)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize failed: '+role)
    if not lib.save_loaded_asset(clip,False):raise RuntimeError('Save failed: '+role)
    receipt['clips'][role]=clip.get_path_name();receipt_path.write_text(json.dumps(receipt,indent=2))
    print('KUKRI_KAITLIN_SAVED '+role,flush=True)
receipt['complete']=True;receipt_path.write_text(json.dumps(receipt,indent=2))
print('KUKRI_KAITLIN_SAVE_COMPLETE',flush=True)
