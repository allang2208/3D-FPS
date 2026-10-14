"""Create and save complete Jason death animations in new task-owned packages."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/PlayerDeath20261006'
DEST='/Game/Characters/JasonPlayer20261003/Death20261006/Animations'
data=json.loads((OUT/'authored-death.json').read_text())
lib=u.EditorAssetLibrary
mesh=u.load_asset(data['mesh'])
factory=u.AnimSequenceFactory()
factory.set_editor_property('target_skeleton',mesh.skeleton)
factory.set_editor_property('preview_skeletal_mesh',mesh)
receipt=dict(runtime_clips={},clips={},source_url=data['source_url'],provenance=data['provenance'])
for label,authored in data['clips'].items():
    name='J_Death_'+label
    path=DEST+'/'+name
    if lib.does_asset_exist(path):
        raise RuntimeError('Refusing to overwrite saved death candidate '+path)
    clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.AnimSequence,factory)
    frames=authored['frames']
    controller=clip.get_editor_property('controller')
    controller.open_bracket('Author complete player death '+label,False)
    try:
        controller.set_frame_rate(u.FrameRate(authored['rate'],1),False)
        controller.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
        for j,bone in enumerate(data['names']):
            controller.add_bone_curve(bone,False)
            keys=[f[j] for f in frames]
            if not controller.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],
                [u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):
                raise RuntimeError('Could not write '+bone)
    finally:
        controller.close_bracket(False)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
    u.AnimationLibrary.add_animation_notify_track(clip,'DeathTiming')
    u.AnimationLibrary.add_animation_sync_marker(clip,'Impact',authored['impact'],'DeathTiming')
    lib.set_metadata_tag(clip,'PlayerDeathSource',data['provenance'])
    lib.set_metadata_tag(clip,'AuthoringScript','SourceAssets/PlayerDeath20261006/author_death.py')
    if not lib.save_loaded_asset(clip,False):raise RuntimeError('Could not save '+path)
    role='Dead' if label=='Standing' else 'Dead.Crouched'
    receipt['runtime_clips'][role]=clip.get_path_name()
    receipt['clips'][label]=dict(asset=clip.get_path_name(),keys=len(frames),duration=clip.get_play_length())
    print('PLAYER_DEATH_SAVED '+clip.get_path_name())
receipt['death_presentation']=dict(standing_camera=data['clips']['Standing']['camera'],
    crouched_camera=data['clips']['Crouched']['camera'],source=data['source_url'])
(OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
