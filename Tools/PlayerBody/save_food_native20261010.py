"""Save and register the two food clips without modifying the accepted drink."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonFoodNative20261010'
DEST = '/Game/Characters/JasonPlayer20261003/FoodNative20261010/Animations'
AUTHOR = 'Tools/PlayerBody/author_food_native20261010.py'
config = ROOT/'Content/ColdSteelData/player_body.json'
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('FOOD_NATIVE_SAVE_REQUIRES_END_PLAY')
payload = (OUT/'authored.json').read_bytes()
data = json.loads(payload)
cfg = json.loads(config.read_text(encoding='utf-8-sig'))
labels = {'Consume.EatBread':'J_Food_Bread_NativeArm', 'Consume.EatBaguette':'J_Food_Baguette_NativeArm'}
previous = {key:cfg['clips'][key] for key in labels}
for key, name in labels.items():
    if previous[key] not in (data['previous_clips'][key], DEST+'/'+name+'.'+name):
        raise RuntimeError('Food configuration changed; preserve current '+key)
if cfg['body_mesh'] != data['mesh'] or cfg['clips']['Consume.Drink'] != data['drink_clip_unchanged']:
    raise RuntimeError('Body or accepted drink changed; preserve current configuration')
lib = u.EditorAssetLibrary
mesh = u.load_asset(data['mesh'])
saved = {}
for key, name in labels.items():
    path = DEST+'/'+name
    clip = u.load_asset(path) if lib.does_asset_exist(path) else None
    if clip and lib.get_metadata_tag(clip, 'AuthoringScript') != AUTHOR:
        raise RuntimeError('Keep existing authored asset '+path)
    fresh = not clip
    if fresh:
        factory = u.AnimSequenceFactory()
        factory.set_editor_property('target_skeleton', mesh.skeleton)
        factory.set_editor_property('preview_skeletal_mesh', mesh)
        clip = u.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST, u.AnimSequence, factory)
    c = data['clips'][key]
    frames = c['frames']
    clip.get_editor_property('platform_target_frame_rate').set_editor_property('default', u.FrameRate(c['rate'], 1))
    ctl = clip.get_editor_property('controller')
    ctl.open_bracket('Native food arm from accepted drink', False)
    try:
        ctl.set_frame_rate(u.FrameRate(c['rate'], 1), False)
        ctl.set_number_of_frames(u.FrameNumber(len(frames)-1), False)
        for j, bone in enumerate(data['names']):
            if fresh:
                ctl.add_bone_curve(bone, False)
            keys = [f[j] for f in frames]
            if not ctl.set_bone_track_keys(bone, [u.Vector(*t[:3]) for t in keys],
                    [u.Quat(*t[3:7]) for t in keys], [u.Vector(*t[7:]) for t in keys], False):
                raise RuntimeError('Cannot write '+bone)
    finally:
        ctl.close_bracket(False)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.REF_POSE)
    u.AnimationLibrary.remove_all_animation_sync_markers(clip)
    if fresh:
        u.AnimationLibrary.add_animation_notify_track(clip, 'ConsumeTiming')
    for marker, fraction in [('Contact', c['contact']), ('Release', c['release']), ('NativeConsumeArm', 0.)]:
        u.AnimationLibrary.add_animation_sync_marker(clip, marker, fraction*clip.get_play_length(), 'ConsumeTiming')
    for tag, value in {'AuthoringScript':AUTHOR, 'SourceAsset':c['source'],
            'SourceHash':hashlib.sha256(payload).hexdigest(), 'SourceURL':data['source_url'], 'MotionScope':data['scope']}.items():
        lib.set_metadata_tag(clip, tag, value)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Cannot finalize '+path)
    if not lib.save_loaded_asset(clip, False):
        raise RuntimeError('Cannot save '+path)
    saved[key] = clip.get_path_name()
cfg = json.loads(config.read_text(encoding='utf-8-sig'))
if cfg['body_mesh'] != data['mesh'] or any(cfg['clips'][k] != previous[k] for k in previous):
    raise RuntimeError('Configuration changed during save; new assets retained without changing configuration')
cfg['clips'].update(saved)
config.write_text(json.dumps(cfg, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
receipt = dict(clips=saved, previous_clips=previous, drink_clip_unchanged=cfg['clips']['Consume.Drink'],
               source_url=data['source_url'], gameplay_tested=False, rendered=False)
(OUT/'assets-saved.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
print('FOOD_NATIVE_SAVED_AND_REGISTERED', json.dumps(saved))
