"""Save the three Jason body adaptations of the CC0 UAL2 Consume take."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/Consume20261006'
DEST='/Game/Characters/JasonPlayer20261003/Consume20261006/Animations'
data=json.loads((OUT/'authored-body.json').read_text())
lib=u.EditorAssetLibrary
assets=u.AssetToolsHelpers.get_asset_tools()
mesh=u.load_asset(data['mesh'])
factory=u.AnimSequenceFactory()
factory.set_editor_property('target_skeleton',mesh.skeleton)
factory.set_editor_property('preview_skeletal_mesh',mesh)
receipt=dict(runtime_clips={},clips={},mouth_in_head=data['mouth_in_head'],
             provenance=data['provenance'],source_url=data['source_url'])
for label,authored in data['clips'].items():
    name='J_UAL2_Consume_'+label
    path=DEST+'/'+name
    if lib.does_asset_exist(path):
        raise RuntimeError('Refusing to overwrite saved animation: '+path)
    clip=assets.create_asset(name,DEST,u.AnimSequence,factory)
    frames=authored['frames']
    controller=clip.get_editor_property('controller')
    controller.open_bracket('Fit UAL2 Consume '+label,False)
    try:
        controller.set_frame_rate(u.FrameRate(authored['rate'],1),False)
        controller.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
        for j,bone in enumerate(data['names']):
            controller.add_bone_curve(bone,False)
            keys=[f[j] for f in frames]
            if not controller.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],
                    [u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):
                raise RuntimeError('Could not set '+bone)
    finally:
        controller.close_bracket(False)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
    u.AnimationLibrary.add_animation_notify_track(clip,'ConsumeTiming')
    for marker,fraction in [('Contact',authored['contact']),('Release',authored['release'])]:
        u.AnimationLibrary.add_animation_sync_marker(clip,marker,fraction*clip.get_play_length(),'ConsumeTiming')
    lib.set_metadata_tag(clip,'ThirdPersonSource',data['provenance'])
    lib.set_metadata_tag(clip,'SourceAsset',data['source_asset'])
    lib.set_metadata_tag(clip,'AuthoringScript','SourceAssets/Consume20261006/author_body.py')
    if not lib.save_loaded_asset(clip,False):
        raise RuntimeError('Could not save '+path)
    receipt['runtime_clips']['Consume.'+label]=clip.get_path_name()
    receipt['clips'][label]=dict(asset=clip.get_path_name(),keys=len(frames),duration=clip.get_play_length())
    print('CONSUME_BODY_SAVED '+clip.get_path_name())
(OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
