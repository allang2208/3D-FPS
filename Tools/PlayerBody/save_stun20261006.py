"""Save the Jason Dizzy loop and publish its runtime reference, without playback."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/PlayerStun20261006'
data=json.loads((OUT/'authored.json').read_text())
dest='/Game/Characters/JasonPlayer20261003/Stun20261006/Animations';name='J_M2M_Dizzy_Loop'
lib=u.EditorAssetLibrary
if lib.does_asset_exist(dest+'/'+name):raise RuntimeError('Refusing to overwrite saved stun loop')
mesh=u.load_asset(data['mesh']);factory=u.AnimSequenceFactory()
factory.set_editor_property('target_skeleton',mesh.skeleton);factory.set_editor_property('preview_skeletal_mesh',mesh)
clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,dest,u.AnimSequence,factory)
frames=data['frames'];ctl=clip.get_editor_property('controller')
ctl.open_bracket('Adapt Dizzy to Jason',False)
try:
    ctl.set_frame_rate(u.FrameRate(data['rate'],1),False)
    ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
    for j,bone in enumerate(data['names']):
        ctl.add_bone_curve(bone,False);keys=[f[j] for f in frames]
        if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],[u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):
            raise RuntimeError('Cannot save bone '+bone)
finally:ctl.close_bracket(False)
clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('enable_root_motion',False)
clip.set_editor_property('force_root_lock',True);clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
lib.set_metadata_tag(clip,'ThirdPersonSource',data['provenance'])
lib.set_metadata_tag(clip,'SourceManifest',data['source_manifest'])
lib.set_metadata_tag(clip,'AuthoringScript','SourceAssets/PlayerStun20261006/author_stun.py')
if not lib.save_loaded_asset(clip,False):raise RuntimeError('Cannot save Jason Dizzy')
receipt=dict(asset=clip.get_path_name(),duration=clip.get_play_length(),keys=len(frames),provenance=data['provenance'])
(OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
path=ROOT/'Content/ColdSteelData/player_body.json';cfg=json.loads(path.read_text(encoding='utf-8-sig'))
cfg['clips']['Reaction.Stun.Loop']=clip.get_path_name()
path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('STUN_ASSET_SAVED '+clip.get_path_name())
