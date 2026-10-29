"""Read the currently routed thrust to local authoring input; no package writes."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = ROOT/'SourceAssets/KukriThirdPerson20261024/ComboV3'
INPUT = json.loads((BASE/'inputs.json').read_text())
CFG = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))


def pack(t):
    return [t.translation.x, t.translation.y, t.translation.z,
            t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w,
            t.scale3d.x, t.scale3d.y, t.scale3d.z]


for label, target in INPUT['targets'].items():
    section = CFG if label == 'jason' else CFG['body_variants'][label]
    path = section['clips']['Kukri.FullBody.Thrust']
    clip = u.load_asset(path)
    mesh = u.load_asset(target['mesh'])
    if not isinstance(clip, u.AnimSequence):
        raise RuntimeError('Active thrust unavailable: '+path)
    opt = u.AnimPoseEvaluationOptions()
    opt.optional_skeletal_mesh = mesh
    opt.evaluation_type = u.AnimDataEvalType.SOURCE
    rate = 60
    count = round(clip.get_play_length()*rate)+1
    frames = []
    for k in range(count):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, min(k/rate, clip.get_play_length()), opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in target['names']])
    # The reported fault is also sampled from the runtime compression path.
    # Only wrist/forearm/palm bones are needed to distinguish source vs compression.
    names = ['lowerarm_l', 'hand_l', 'middle_01_l', 'index_01_l', 'pinky_01_l',
             'lowerarm_twist_01_l', 'lowerarm_twist_02_l']
    opt.evaluation_type = u.AnimDataEvalType.COMPRESSED
    compressed = []
    for k in range(count):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, min(k/rate, clip.get_play_length()), opt)
        compressed.append([pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.WORLD)) for n in names])
    original = json.loads((ROOT/f'SourceAssets/KukriThrustHand20261025/{label}-actions.json').read_text())['clips']['Thrust']
    original['frames'] = frames
    original['rate'] = rate
    data = dict(asset=path, mesh=target['mesh'], names=target['names'], parents=target['parents'],
                clips={'Thrust': original}, compressed=dict(names=names, frames=compressed, rate=rate))
    (OUT/(label+'-current.json')).write_text(json.dumps(data, separators=(',', ':')))
    print('KUKRI_THRUST_WRIST_INPUT '+label+' '+path, flush=True)
print('KUKRI_THRUST_WRIST_PREPARED', flush=True)
