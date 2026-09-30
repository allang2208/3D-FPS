"""GripLayer56: read the active PKM / 201 clips (same set as ArmHinge55) for the grip-layer
feasibility study: component-space WPN_root, the left arm skin chain and every left finger.
Read only; writes Inputs/ next to this script.  Resumable short batches (~15 s) so a running
editor is never held for long; does nothing while PIE runs."""
import unreal as u, json, gzip, hashlib, time, os
from pathlib import Path

HEADLESS = os.environ.get('GRIPLAYER56_HEADLESS') == '1'  # set by run_headless.ps1

HERE = Path(globals().get('__file__') or r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\GripLayer56\collect.py').resolve().parent
PROJECT = HERE.parents[2]
ARM = HERE.parent / 'ArmHinge55'
IN = HERE / 'Inputs'
IN.mkdir(exist_ok=True)
ARM_BONES = ['clavicle_l', 'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
             'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']


def tr(t):
    return [*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, *t.scale3d.to_tuple()]


def sha(p):
    return hashlib.sha256((PROJECT / 'Content' / (p.removeprefix('/Game/') + '.uasset')).read_bytes()).hexdigest()


source = {g: v for g, v in json.loads((ARM / 'inputs.json').read_text()).items() if isinstance(v, dict) and 'clips' in v}
index = json.loads((HERE / 'inputs.json').read_text()) if (HERE / 'inputs.json').exists() else {}
start, done = time.time(), True
if not HEADLESS and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    print('GRIPLAYER56_PIE nothing read', flush=True)
    source, done = {}, False
for gun, entry in source.items():
    mesh = u.load_asset(entry['mesh'])
    bind = json.loads((ARM / 'Inputs' / (gun + '_bind.json')).read_text())
    names, parents = bind['names'], bind['parents']
    hand = names.index('hand_l')

    def below(i):
        out = []
        for j, p in enumerate(parents):
            if p == i:
                out += [j] + below(j)
        return out
    bones = ['WPN_root'] + ARM_BONES + [names[j] for j in below(hand)]
    opts = u.AnimPoseEvaluationOptions()
    opts.optional_skeletal_mesh = mesh
    opts.evaluation_type = u.AnimDataEvalType.RAW
    clips = index.get(gun, {}).get('clips', {})
    for key in entry['clips']:
        if key in clips and clips[key]['sha256'] == sha(key) and Path(clips[key]['file']).exists():
            continue
        if not HEADLESS and time.time() - start > 15:
            done = False
            break
        a = u.load_asset(key)
        frames = u.AnimationLibrary.get_num_frames(a)
        times = [u.AnimationLibrary.get_time_at_frame(a, i) for i in range(frames + 1)]
        world = []
        for t in times:
            pose = u.AnimPoseExtensions.get_anim_pose_at_time(a, t, opts)
            world.append([tr(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.WORLD)) for n in bones])
        f = IN / gun / (key.split('/Weapons/')[1].replace('/', '__') + '.json.gz')
        f.parent.mkdir(exist_ok=True)
        with gzip.open(f, 'wt', encoding='utf8') as h:
            json.dump({'asset': key, 'sha256': sha(key), 'times': times, 'bones': bones, 'world': world,
                       'seconds': a.get_play_length()}, h, separators=(',', ':'))
        clips[key] = {'file': str(f), 'sha256': sha(key), 'keys': len(times), 'seconds': a.get_play_length()}
        print('GRIPLAYER56_READ', gun, key, len(times), flush=True)
    index[gun] = {'mesh': entry['mesh'], 'bones': bones, 'clips': clips}
(HERE / 'inputs.json').write_text(json.dumps(index, indent=1))
print('GRIPLAYER56_' + ('COMPLETE' if done else 'PARTIAL'), {g: len(v['clips']) for g, v in index.items()}, flush=True)
