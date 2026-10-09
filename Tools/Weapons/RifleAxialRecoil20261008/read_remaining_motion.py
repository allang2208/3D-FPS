"""Read-only follow-up requested by the user: remaining rifles and both LMGs."""
import json, math
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if P != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project ' + str(P))
S = u.AnimPoseSpaces.WORLD
specs = {
    'akm': ('/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative', '/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_'),
    'ash12': ('/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface', '/Game/Weapons/ASH12/Integrated20260917/Animations/A_ASH12_'),
    'm16a2': ('/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny', '/Game/Weapons/M16A2/Gameplay20260919/Animations/A_M16_'),
    'svd': ('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock', '/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_'),
    'pkm_lowpoly': ('/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular', '/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_'),
    'lmg201': ('/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10', '/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_'),
}

def vec(v): return [v.x, v.y, v.z]
def sub(a, b): return [x-y for x, y in zip(a, b)]
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def norm(a): return math.sqrt(dot(a, a))
def tf(t): return dict(p=vec(t.translation), q=[t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w])
def load(path):
    obj = u.load_asset(path)
    if not obj: raise RuntimeError('Cannot load ' + path)
    return obj

report = dict(project=str(P), read_only=True, game_started=False, sample_hz=240, weapons={})
for weapon, (mesh_path, prefix) in specs.items():
    mesh = load(mesh_path)
    opts = u.AnimPoseEvaluationOptions()
    opts.evaluation_type = u.AnimDataEvalType.COMPRESSED
    opts.optional_skeletal_mesh = mesh
    opts.should_retarget = True
    cache = {}

    def measure(clip):
        path = clip.get_path_name()
        if path in cache: return cache[path]
        length = clip.get_play_length()
        samples = []
        for i in range(math.ceil(length*240)+1):
            t = min(i/240, length)
            pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, t, opts)
            root = u.AnimPoseExtensions.get_bone_pose(pose, 'WPN_root', S)
            if not samples:
                if weapon == 'akm':
                    # Matches runtime AKMSovietCalibration.h (metres in WPN_root).
                    rear = root.transform_location(u.Vector(.0007595263, .1704100072, .1019900516))
                    front = root.transform_location(u.Vector(.0008, .5575537682, .0968115032))
                else:
                    rear = u.AnimPoseExtensions.get_bone_pose(pose, 'WPN_RearSight', S).translation
                    front = u.AnimPoseExtensions.get_bone_pose(pose, 'WPN_FrontSight', S).translation
                axis = sub(vec(front), vec(rear))
                axis_len = norm(axis)
                if axis_len < .001: raise RuntimeError('Invalid sight axis ' + path)
                axis = [x/axis_len for x in axis]
                initial = tf(root)
            value = tf(root)
            delta = sub(value['p'], initial['p'])
            rearward = -dot(delta, axis)
            lateral = math.sqrt(max(0, dot(delta, delta)-rearward*rearward))
            angle = math.degrees(2*math.acos(min(1, abs(dot(value['q'], initial['q'])))))
            samples.append(dict(time=t, rearward_cm=rearward, lateral_cm=lateral, rotation_deg=angle, root=value))
        peak = max(samples, key=lambda s: s['rearward_cm'])
        value = dict(asset=path, duration=length, rate_scale=clip.get_editor_property('rate_scale'), axis=axis,
            rearward_peak_cm=peak['rearward_cm'], peak_time=peak['time'],
            forward_peak_cm=min(s['rearward_cm'] for s in samples),
            lateral_peak_cm=max(s['lateral_cm'] for s in samples),
            rotation_peak_deg=max(s['rotation_deg'] for s in samples), samples=samples)
        cache[path] = value
        return value

    row = dict(mesh=mesh_path, clips={}, profiles={})
    for role in ('fire', 'aim_fire'):
        row['clips'][role] = measure(load(prefix+role))
    profile_folder = P/'Content/Weapons/AnimationProfiles20261001'/('ue_'+weapon)
    if weapon == 'svd': profile_folder = P/'Content/Weapons/SVDDragunov20260922/GripProfiles20261001'
    for file in sorted(profile_folder.glob('DA_*.uasset')):
        path = '/Game/' + file.relative_to(P/'Content').with_suffix('').as_posix()
        profile = load(path)
        entries = []
        for layer in profile.get_editor_property('clips'):
            base = layer.get_editor_property('base')
            if not base or not base.get_name().lower().endswith(('_fire', '_aim_fire')): continue
            retained = layer.get_editor_property('retained')
            tracks = []
            for track in layer.get_editor_property('tracks'):
                if str(track.get_editor_property('bone')) in ('WPN_root', 'root', 'pelvis'):
                    tracks.append(dict(bone=str(track.get_editor_property('bone')), times=list(track.get_editor_property('times')), values=list(track.get_editor_property('values'))))
            entries.append(dict(base=base.get_path_name(), retained=retained.get_path_name() if retained else None,
                duration=layer.get_editor_property('duration'), root_tracks=tracks))
            if retained: measure(retained)
        row['profiles'][file.stem] = dict(path=path, entries=entries)
    row['measured_sequences'] = cache
    report['weapons'][weapon] = row
    print('RIFLE_REMAINING_INPUT', weapon, json.dumps({k:{q:v[q] for q in ('duration', 'rearward_peak_cm', 'peak_time', 'forward_peak_cm', 'rotation_peak_deg')} for k,v in row['clips'].items()}), flush=True)
(O/'remaining_motion.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('RIFLE_REMAINING_READ_COMPLETE', str(O/'remaining_motion.json'), flush=True)
