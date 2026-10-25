"""Save new animation packages, then add only this task's player-body routing keys."""
import json,runpy
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/FurnitureRest20261022/RelaxedSeatV5'
DEST='/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/RefineV2/RelaxedSeatV5'
d=json.loads((OUT/'authored.json').read_text());mesh=u.load_asset(d['mesh'])
factory=u.AnimSequenceFactory();factory.set_editor_property('target_skeleton',mesh.skeleton)
factory.set_editor_property('preview_skeletal_mesh',mesh)
lib=u.EditorAssetLibrary;receipt={}
receipt_path=OUT/'assets_saved.json'
if receipt_path.exists():receipt=json.loads(receipt_path.read_text())
for role,data in d['clips'].items():
    target_dir=DEST
    name='A_'+role.replace('.','_');path=target_dir+'/'+name
    if receipt.get(role)==path+'.'+name:continue
    if lib.does_asset_exist(path):raise RuntimeError('Existing unreceipted output preserved: '+path)
    clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,target_dir,u.AnimSequence,factory)
    ctl=clip.get_editor_property('controller');frames=data['frames']
    ctl.open_bracket('Author native furniture rest',False)
    try:
        ctl.set_frame_rate(u.FrameRate(30,1),False);ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
        for i,bone in enumerate(d['names']):
            ctl.add_bone_curve(bone,False);keys=[f[i] for f in frames]
            if not ctl.set_bone_track_keys(bone,[u.Vector(*k[:3]) for k in keys],[u.Quat(*k[3:7]) for k in keys],[u.Vector(*k[7:]) for k in keys],False):
                raise RuntimeError('Track failed: '+bone)
    finally:ctl.close_bracket(False)
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize failed: '+role)
    if not lib.save_loaded_asset(clip,False):raise RuntimeError('Save failed: '+role)
    receipt[role]=clip.get_path_name();receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('FURNITURE_SAVED '+role)
path=ROOT/'Content/ColdSteelData/player_body.json';before=path.read_bytes();candidate=json.loads(before.decode('utf-8-sig'))
candidate['clips'].update(receipt)
commit=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit']
commit(path,before,candidate,owned_paths=[('clips',role) for role in receipt],producer=__file__)
runpy.run_path(str(ROOT/'Tools/FurnitureRest/publish_relaxed_seat.py'))
print('FURNITURE_REST_INSTALLED '+str(len(receipt)))
