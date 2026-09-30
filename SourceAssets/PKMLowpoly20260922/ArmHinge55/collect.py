"""ArmHinge55: read every PKM / 201 animation the runtime can load (RAW source keys) for the
left-arm skin bones, plus the bind pose of each gun's native arm skeleton.  Read only."""
import unreal as u, json, gzip, hashlib
from pathlib import Path

HERE = Path(globals().get('__file__') or r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\ArmHinge55\collect.py').resolve().parent
PROJECT = HERE.parents[2]
IN = HERE / 'Inputs'
IN.mkdir(exist_ok=True)
GUNS = {
    'PKM': ('/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular',
            ['/Game/Weapons/PKMLowpoly20260922/Animations', '/Game/Weapons/PKMLowpoly20260922/Accessories14/Animations']),
    '201': ('/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10',
            ['/Game/Weapons/LMG201/BeltFeed08/Animations', '/Game/Weapons/LMG201/Accessories22/Animations',
             '/Game/Weapons/LMG201/Magazine24/Animations', '/Game/Weapons/LMG201/Drum46/Animations',
             '/Game/Weapons/LMG201/ClothReload44/Animations']),
}
BONES = ['clavicle_l', 'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
         'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']
G, B = u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights


def tr(t):
    return [*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, *t.scale3d.to_tuple()]


def disk(p):
    return PROJECT / 'Content' / (p.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha(p):
    return hashlib.sha256(disk(p).read_bytes()).hexdigest()


index = {}
for gun, (meshpath, folders) in GUNS.items():
    mesh = u.load_asset(meshpath)
    skel = mesh.get_editor_property('skeleton')
    dm, status = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    _, rows = B.get_all_bones_info(dm)
    rows = sorted(rows, key=lambda b: b.index)
    names = [str(b.name) for b in rows]
    bind = {'names': names, 'parents': [b.parent_index for b in rows], 'rest': [tr(b.world_transform) for b in rows]}
    (IN / (gun + '_bind.json')).write_text(json.dumps(bind))
    opts = u.AnimPoseEvaluationOptions()
    opts.optional_skeletal_mesh = mesh
    opts.evaluation_type = u.AnimDataEvalType.RAW
    clips = {}
    for folder in folders:
        for path in u.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False):
            a = u.load_asset(path)
            if not isinstance(a, u.AnimSequence) or a.get_editor_property('skeleton') != skel:
                continue
            frames = u.AnimationLibrary.get_num_frames(a)
            times = [u.AnimationLibrary.get_time_at_frame(a, i) for i in range(frames + 1)]
            world, local = [], []
            for t in times:
                pose = u.AnimPoseExtensions.get_anim_pose_at_time(a, t, opts)
                world.append([tr(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.WORLD)) for n in BONES])
                local.append([tr(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in BONES])
            key = path.split('.')[0]
            f = IN / gun / (key.split('/Animations/')[0].split('/')[-1] + '__' + key.split('/Animations/')[1].replace('/', '__') + '.json.gz')
            f.parent.mkdir(exist_ok=True)
            with gzip.open(f, 'wt', encoding='utf8') as h:
                json.dump({'asset': key, 'sha256': sha(key), 'times': times, 'bones': BONES, 'world': world, 'local': local,
                           'seconds': a.get_play_length()}, h, separators=(',', ':'))
            clips[key] = {'file': str(f), 'sha256': sha(key), 'keys': len(times), 'seconds': a.get_play_length()}
            print('ARMHINGE55_READ', gun, key, len(times), flush=True)
    index[gun] = {'mesh': meshpath, 'clips': clips}
(HERE / 'inputs.json').write_text(json.dumps(index, indent=2))
print('ARMHINGE55_INPUTS', {g: len(v['clips']) for g, v in index.items()}, flush=True)
