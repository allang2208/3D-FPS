"""Save and register only the new native drink adaptation."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/ThirdPersonWizardDrink20261010'
DEST='/Game/Characters/JasonPlayer20261003/WizardDrink20261010/Animations'
NAME='J_Wizard_Drink_NativeArm';PATH=DEST+'/'+NAME
AUTHOR='Tools/PlayerBody/author_wizard_drink20261010.py'
config=ROOT/'Content/ColdSteelData/player_body.json'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('WIZARD_DRINK_SAVE_REQUIRES_END_PLAY')
payload=(OUT/'authored.json').read_bytes();data=json.loads(payload)
original=json.loads((OUT/'inputs.json').read_text())['previous_clips']['Consume.Drink']
cfg=json.loads(config.read_text(encoding='utf-8-sig'));previous=cfg['clips']['Consume.Drink']
if cfg['body_mesh']!=data['mesh'] or previous not in (original,PATH+'.'+NAME):
    raise RuntimeError('Active body or drink changed; keep current configuration')
lib=u.EditorAssetLibrary;mesh=u.load_asset(data['mesh'])
clip=u.load_asset(PATH) if lib.does_asset_exist(PATH) else None
if clip and lib.get_metadata_tag(clip,'AuthoringScript')!=AUTHOR:raise RuntimeError('Keep existing authored asset '+PATH)
fresh=not clip
if fresh:
    factory=u.AnimSequenceFactory();factory.set_editor_property('target_skeleton',mesh.skeleton);factory.set_editor_property('preview_skeletal_mesh',mesh)
    clip=u.AssetToolsHelpers.get_asset_tools().create_asset(NAME,DEST,u.AnimSequence,factory)
c=data['clips']['Consume.Drink'];frames=c['frames']
clip.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(c['rate'],1))
ctl=clip.get_editor_property('controller');ctl.open_bracket('Native Wizard drinking arm',False)
try:
    ctl.set_frame_rate(u.FrameRate(c['rate'],1),False);ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
    for j,bone in enumerate(data['names']):
        if fresh:ctl.add_bone_curve(bone,False)
        keys=[f[j] for f in frames]
        if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],[u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):
            raise RuntimeError('Cannot write '+bone)
finally:ctl.close_bracket(False)
clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('enable_root_motion',False)
clip.set_editor_property('force_root_lock',True);clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
u.AnimationLibrary.remove_all_animation_sync_markers(clip)
if fresh:u.AnimationLibrary.add_animation_notify_track(clip,'ConsumeTiming')
for marker,fraction in [('Contact',c['contact']),('Release',c['release']),('NativeConsumeArm',0.)]:
    u.AnimationLibrary.add_animation_sync_marker(clip,marker,fraction*clip.get_play_length(),'ConsumeTiming')
source_hash=hashlib.sha256(payload).hexdigest()
for tag,value in {'AuthoringScript':AUTHOR,'SourceAsset':c['source'],'SourceHash':source_hash,'SourceURL':data['source_url'],'MotionScope':data['scope']}.items():
    lib.set_metadata_tag(clip,tag,value)
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Cannot finalize '+PATH)
if not lib.save_loaded_asset(clip,False):raise RuntimeError('Cannot save '+PATH)
cfg=json.loads(config.read_text(encoding='utf-8-sig'))
if cfg['body_mesh']!=data['mesh'] or cfg['clips']['Consume.Drink']!=previous:raise RuntimeError('Configuration changed while saving; new asset retained')
cfg['clips']['Consume.Drink']=clip.get_path_name()
config.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt=dict(clips={'Consume.Drink':clip.get_path_name()},previous_clip=original,source_asset=c['source'],source_hash=source_hash,
    source_url=data['source_url'],gameplay_tested=False,rendered=False)
(OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print('WIZARD_DRINK_SAVED_AND_REGISTERED',clip.get_path_name())
