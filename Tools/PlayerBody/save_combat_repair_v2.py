"""Save this task's replacement sword skills without touching loaded old assets."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/BodyCombatRepair20261006V2'
DEST='/Game/Characters/JasonPlayer20261003/CombatRepair20261006V3/Animations'
if u.EditorLevelLibrary.get_pie_worlds(True):
    raise RuntimeError('PIE is running; no assets or runtime references were changed')
d=json.loads((OUT/'authored-actions.json').read_text());lib=u.EditorAssetLibrary
mesh=u.load_asset(d['mesh']);factory=u.AnimSequenceFactory()
factory.set_editor_property('target_skeleton',mesh.skeleton);factory.set_editor_property('preview_skeletal_mesh',mesh)
receipt=dict(clips={},provenance=d['provenance'])
author='SourceAssets/BodyCombatRepair20261006V2/author_actions.py'
for label,c in d['clips'].items():
    name='J_Sword_'+label.replace('.','_');path=DEST+'/'+name
    if lib.does_asset_exist(path):
        raise RuntimeError('Final packages already exist: '+path)
    clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.AnimSequence,factory)
    ctl=clip.get_editor_property('controller');frames=c['frames'];ctl.open_bracket('Rebuild sword skill '+label,False)
    try:
        ctl.set_frame_rate(u.FrameRate(c['rate'],1),False);ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
        for j,bone in enumerate(d['names']):
            ctl.add_bone_curve(bone,False);keys=[f[j] for f in frames]
            if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],[u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):
                raise RuntimeError('Cannot write '+bone)
    finally:ctl.close_bracket(False)
    clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',True);clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
    u.AnimationLibrary.add_animation_notify_track(clip,'SwordTiming')
    for marker,fraction in [('Contact',c['contact']),('Release',c['release'])]:
        u.AnimationLibrary.add_animation_sync_marker(clip,marker,fraction*clip.get_play_length(),'SwordTiming')
    lib.set_metadata_tag(clip,'ThirdPersonSource',d['provenance'])
    lib.set_metadata_tag(clip,'AuthoringScript',author)
    lib.set_metadata_tag(clip,'BladeConvention','length +Z; face XZ; cutting edge -X')
    if not lib.save_loaded_asset(clip,False):raise RuntimeError('Cannot save '+path)
    receipt['clips']['Melee.FullBody.'+label]=clip.get_path_name()
    (OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
    print('COMBAT_REPAIR_SAVED '+clip.get_path_name())
# Publish only after all newly named assets have actually saved. Current PIE
# keeps its existing loaded animations; a new session loads this configuration.
cfgpath=ROOT/'Content/ColdSteelData/player_body.json';cfg=json.loads(cfgpath.read_text(encoding='utf-8-sig'))
cfg['clips'].update(receipt['clips']);cfgpath.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('COMBAT_REPAIR_PUBLISHED')
