"""Background repair of current firearm sleeves; never publish or replace a source.

Preserve each native fit. Apply the reviewed shoulder-opening edit by matching
the historical topology, then use the existing garment boundary-preserving LOD
policy. The SVD opening is already fixed and must not be cut a second time.
"""
import math
import sys
from pathlib import Path

import unreal as u

P = Path('D:/FPS3D/FPSGAME')
sys.path.insert(0, str(P / 'Tools/ModularOutfit'))
import garment_ue as g

R = P / 'SourceAssets/ChainmailCameraClearance20260929'
HISTORY = P / 'SourceAssets/ChainmailReloadFit20260929'
FOUNDATION = P / 'SourceAssets/GarmentFoundation20260929'
DEST = '/Game/Characters/ModularOutfit20260924/ChainmailCameraClearance20260929'


def face_key(data, face):
    return tuple(sorted(tuple(round(x, 3) for x in data['positions'][i]) for i in face))


def main(only=None, collect_poses=True):
    u.SystemLibrary.execute_console_command(None, 'r.FreeSkeletalMeshBuffers 0')
    config = g.read(P / 'Content/ColdSteelData/modular_outfits.json')
    recipe = config['items']['ue_chainmail_shirt']
    profiles = list(g.read(HISTORY / 'sources.json'))
    master = g.read(HISTORY / 'M4_fitted.json')
    review = g.read(FOUNDATION / 'edits.json')['ue_chainmail_shirt']
    foundation = g.read(FOUNDATION / 'ue_chainmail_shirt.json')
    if master['triangles'] != foundation['triangles']:
        raise RuntimeError('Historical shoulder edit no longer matches its topology')
    cap_keys = {face_key(master, master['triangles'][i]) for i in review['delete_triangles']}
    sources = {profile: recipe['rig_meshes'][profile] for profile in profiles}
    if not (R / 'before.json').exists():
        g.write(R / 'before.json', dict(sources=sources, recipe=recipe))
    elif g.read(R / 'before.json')['sources'] != sources:
        raise RuntimeError('Active source changed during production')
    receipts = g.read(R / 'saved.json') if (R / 'saved.json').exists() else {}
    for profile, path in sources.items():
        if only and profile not in only:
            continue
        source_sha = g.digest(g.asset_file(path))
        if profile in receipts:
            old = receipts[profile]
            if old['source_sha256'] != source_sha or old['asset_sha256'] != g.digest(g.asset_file(old['asset'])):
                raise RuntimeError('Completed source or output changed: ' + profile)
            continue
        source = u.load_asset(path)
        dm, data = g.source_snapshot(source)
        if profile == 'SVD' and '/SVDShoulderOpening20260929/' in path:
            removed = []
        else:
            history = g.read(HISTORY / (profile + '_fitted.json'))
            if data['triangles'] != history['triangles'] or len(data['positions']) != len(history['positions']):
                raise RuntimeError('Current topology differs from the reviewed native source: ' + profile)
            if history['triangles'] == master['triangles']:
                removed = review['delete_triangles']
            else:
                # Single-arm derivatives use their own vertex IDs; match only
                # the reviewed geometric cap signatures, never profile suffixes.
                removed = [i for i, face in enumerate(history['triangles']) if face_key(history, face) in cap_keys]
                if len(removed) != 120:
                    raise RuntimeError('Unexpected single-arm cap correspondence: ' + profile)
        for triangle in removed:
            _, ok = u.GeometryScript_MeshEdits.delete_triangle_from_mesh(dm, triangle, True)
            if not ok:
                raise RuntimeError('Cannot remove reviewed shoulder face: ' + profile)
        folder = R / profile
        g.write(folder / 'input.json', dict(source=path, source_sha256=source_sha,
            removed_triangles=removed, historical_topology=str(HISTORY / (profile + '_fitted.json')),
            contract='Keep all surviving positions, weights, UV, materials, cuff/lining and sway colors'))
        receipt = g.save_candidate(dm, source, DEST + '/' + profile + '/SK_' + profile + '_Chainmail', folder)
        receipt.update(source=path, source_sha256=source_sha, removed_faces=len(removed),
            runtime_visual='pending', layer_clearance='pending', native_fit_preserved=True)
        receipts[profile] = receipt
        g.write(R / 'saved.json', receipts)
        print('CHAINMAIL_REPAIR_SAVED', profile, len(removed), receipt['asset'], flush=True)

    if not collect_poses:
        return

    # Read fresh compressed SVD poses for the user's specific ADS/reload issue.
    # No PIE, viewport capture, world creation or synthetic input.
    native, profile = next((k, v) for k, v in config['profiles'].items() if v['rig_profile'] == 'SVD')
    mesh = u.load_asset(native)
    _, native_data = g.source_snapshot(mesh)
    _, bare = g.source_snapshot(u.load_asset(profile['native_bare_skin']))
    g.write(R / 'SVD/native.json', native_data)
    g.write(R / 'SVD/bare.json', bare)
    g.write(R / 'SVD/before_LOD0.json', g.snapshot(u.load_asset(sources['SVD']), 0))
    _, bones = g.B.get_all_bones_info(g.dynamic(mesh))
    g.write(R / 'SVD/bone_names.json', [str(b.name) for b in bones])
    options = u.AnimPoseEvaluationOptions(optional_skeletal_mesh=mesh,
        evaluation_type=u.AnimDataEvalType.COMPRESSED)
    poses, clips = [], {}
    for folder in ['Complete20260923/Animations', 'Accessories20260923/Animations']:
        for file in sorted((P / 'Content/Weapons/SVDDragunov20260922' / folder).glob('*.uasset')):
            if not any(file.stem.endswith('_' + suffix) for suffix in ['aim', 'idle', 'reload', 'reload_empty']):
                continue
            path = '/Game/' + file.relative_to(P / 'Content').with_suffix('').as_posix()
            clip = u.load_asset(path)
            if not isinstance(clip, u.AnimSequence):
                continue
            duration = clip.get_play_length()
            count = max(2, math.ceil(duration * 20) + 1) if 'reload' in file.stem else 1
            for i in range(count):
                time = duration * i / (count - 1) if count > 1 else 0.
                pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, time, options)
                poses.append(dict(clip=path, time=time, bones={name: g.transform(
                    u.AnimPoseExtensions.get_bone_pose(pose, name, u.AnimPoseSpaces.WORLD))
                    for name in native_data['rest']}))
            clips[path] = g.digest(file)
    g.write(R / 'SVD/poses.json', dict(native=native, native_sha256=g.digest(g.asset_file(native)), clips=clips, poses=poses))
    g.write(R / 'production.json', dict(profiles=list(receipts), saved_meshes=len(receipts),
        editor_started=False, runtime_visual='pending', publication='pending'))
    print('CHAINMAIL_REPAIR_ASSETS_COMPLETE', len(receipts), 'SVD_POSES', len(poses), flush=True)


if __name__ == '__main__':
    main()
