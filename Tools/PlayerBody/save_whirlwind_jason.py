"""Save the authored third-person whirlwind phases as new Jason AnimSequences.

This batch writes only Whirlwind20261006/Animations. No PIE, preview, rendering,
asset replacement, or skeleton mutation is required.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonWhirlwind20261006'
DEST = '/Game/Characters/JasonPlayer20261003/Whirlwind20261006/Animations'
data = json.loads((OUT/'authored-phases.json').read_text())
lib = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
mesh = u.load_asset(data['mesh'])
factory = u.AnimSequenceFactory()
factory.set_editor_property('target_skeleton', mesh.skeleton)
factory.set_editor_property('preview_skeletal_mesh', mesh)
receipt = dict(runtime_clips={}, clips={}, source_url=data['source_url'], provenance=data['provenance'])

for label, authored in data['clips'].items():
    name = 'J_Whirlwind_'+label
    path = DEST+'/'+name
    if lib.does_asset_exist(path):
        raise RuntimeError('Refusing to replace saved candidate: '+path)
    clip = assets.create_asset(name, DEST, u.AnimSequence, factory)
    frames = authored['frames']
    controller = clip.get_editor_property('controller')
    controller.open_bracket('Author third-person whirlwind '+label, False)
    try:
        # Use the same rate as the project's factory/compression default.
        # The phase sampler supplies the skill's exact stage durations.
        controller.set_frame_rate(u.FrameRate(authored['rate'], 1), False)
        controller.set_number_of_frames(u.FrameNumber(len(frames)-1), False)
        for j, bone in enumerate(data['names']):
            controller.add_bone_curve(bone, False)
            keys = [f[j] for f in frames]
            if not controller.set_bone_track_keys(bone,
                    [u.Vector(*t[:3]) for t in keys],
                    [u.Quat(*t[3:7]) for t in keys],
                    [u.Vector(*t[7:]) for t in keys], False):
                raise RuntimeError('Could not author track '+bone)
    finally:
        controller.close_bracket(False)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.REF_POSE)
    lib.set_metadata_tag(clip, 'ThirdPersonSource', data['provenance'])
    lib.set_metadata_tag(clip, 'WhirlwindPhase', label)
    lib.set_metadata_tag(clip, 'AuthoringScript', 'Tools/PlayerBody/author_whirlwind_jason.py')
    if not lib.save_loaded_asset(clip, False):
        raise RuntimeError('Could not save '+path)
    receipt['runtime_clips']['Melee.FullBody.Whirlwind.'+label] = clip.get_path_name()
    receipt['clips'][label] = dict(asset=clip.get_path_name(), keys=len(frames), duration=clip.get_play_length())
    print('WHIRLWIND_SAVED '+clip.get_path_name())

(OUT/'assets-saved.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
