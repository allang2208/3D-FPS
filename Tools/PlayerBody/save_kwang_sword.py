"""Save Kwang-derived Jason skills; publish only after clean commandlet exit."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ThirdPersonSwordKwang20261006'
DEST='/Game/Characters/JasonPlayer20261003/KwangSword20261006V2/Animations'
d=json.loads((OUT/'adapted-actions.json').read_text())
lib=u.EditorAssetLibrary
mesh=u.load_asset(d['mesh'])
factory=u.AnimSequenceFactory()
factory.set_editor_property('target_skeleton',mesh.skeleton)
factory.set_editor_property('preview_skeletal_mesh',mesh)
receipt=dict(clips={},sources={},source_url=d['source_url'],license='Epic Paragon content; Unreal Engine projects only')
for label,c in d['clips'].items():
    name='J_Kwang_'+label.replace('.','_')
    if lib.does_asset_exist(DEST+'/'+name):
        # Resume the same production after interruption without rewriting any
        # package that was already saved successfully in this unique folder.
        clip=u.load_asset(DEST+'/'+name)
        receipt['clips']['Melee.FullBody.'+label]=clip.get_path_name()
        receipt['sources'][label]=dict(clip=c['source'],range=c['source_range'])
        continue
    clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.AnimSequence,factory)
    ctl=clip.get_editor_property('controller')
    frames=c['frames']
    ctl.open_bracket('Adapt Kwang full-body '+label,False)
    try:
        ctl.set_frame_rate(u.FrameRate(c['rate'],1),False)
        ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
        for j,bone in enumerate(d['names']):
            ctl.add_bone_curve(bone,False)
            keys=[f[j] for f in frames]
            if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],[u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):
                raise RuntimeError('Cannot write '+bone)
    finally:ctl.close_bracket(False)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
    u.AnimationLibrary.add_animation_notify_track(clip,'SwordTiming')
    for marker,fraction in [('Contact',c['contact']),('Release',c['release']),('NativeSwordGrip',0.)]:
        u.AnimationLibrary.add_animation_sync_marker(clip,marker,fraction*clip.get_play_length(),'SwordTiming')
    for key,value in dict(ThirdPersonSource=d['provenance'],SourceAnimation=c['source'],SourceURL=d['source_url'],
                          SourceRange=json.dumps(c['source_range']),AuthoringScript='SourceAssets/ThirdPersonSwordKwang20261006/adapt_kwang.py',
                          BladeConvention='length +Z; face XZ; cutting edge -X; derived from Kwang native weapon geometry').items():
        lib.set_metadata_tag(clip,key,value)
    if not lib.save_loaded_asset(clip,False):
        raise RuntimeError('Cannot save '+clip.get_path_name())
    receipt['clips']['Melee.FullBody.'+label]=clip.get_path_name()
    receipt['sources'][label]=dict(clip=c['source'],range=c['source_range'])
    (OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
    print('KWANG_FINAL_SAVED '+clip.get_path_name())

(OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
print('KWANG_SWORD_SAVE_COMPLETE')
