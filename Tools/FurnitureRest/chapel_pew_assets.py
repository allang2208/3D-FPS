"""Capture selected native chair motion, or save the fitted pew motion headlessly."""
import hashlib
import json
import os
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(os.environ.get('CHAPEL_FURNITURE_OUTPUT', str(ROOT / 'SourceAssets/ChapelFurniture20261116')))
OUT.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
E = u.EditorAssetLibrary


def pack(t):
    return [t.translation.x, t.translation.y, t.translation.z,
            t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w,
            t.scale3d.x, t.scale3d.y, t.scale3d.z]


def options(mesh):
    opt = u.AnimPoseEvaluationOptions()
    opt.optional_skeletal_mesh = mesh
    opt.evaluation_type = u.AnimDataEvalType.COMPRESSED
    opt.should_retarget = False  # These are already native male/female sequences.
    return opt


if os.environ.get('CHAPEL_FURNITURE_STAGE', 'capture') == 'capture':
    body = read(ROOT / 'Content/ColdSteelData/player_body.json')
    nodes = {'default': body, **{k: v for k, v in body.get('body_variants', {}).items() if v.get('ready')}}
    result = {}
    for variant, node in nodes.items():
        mesh = u.load_asset(node['body_mesh'])
        ref = mesh.skeleton.get_reference_pose()
        names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
        comp = u.new_object(u.SkeletalMeshComponent)
        comp.set_skeletal_mesh_asset(mesh)
        indices = {name: i for i, name in enumerate(names)}
        rig = {'mesh': node['body_mesh'], 'names': names,
               'parents': [indices.get(str(comp.get_parent_bone(n)), -1) for n in names],
               'reference': [pack(u.AnimPoseExtensions.get_bone_pose(ref, n, u.AnimPoseSpaces.LOCAL)) for n in names],
               'clips': {}}
        for phase in ('Enter', 'Idle', 'Exit'):
            source = node['clips']['Rest.Chair55.' + phase]
            clip = u.load_asset(source)
            if not clip or clip.get_editor_property('skeleton') != mesh.skeleton:
                raise RuntimeError('Native pew source missing: ' + variant + '/' + phase)
            duration = clip.get_play_length()
            count = round(duration * 30) + 1
            frames = []
            for i in range(count):
                pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, i / 30, options(mesh))
                frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in names])
            rig['clips'][phase] = {'asset': source, 'rate': 30, 'duration': duration, 'frames': frames}
            print('CHAPEL_PEW_CAPTURED', variant, phase, flush=True)
        result[variant] = rig
    (OUT / 'native_sources.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
else:
    data = read(OUT / 'authored.json')
    digest = hashlib.sha256((OUT / 'authored.json').read_bytes()).hexdigest()
    receipt_path = OUT / 'assets_saved.json'
    receipt = read(receipt_path) if receipt_path.exists() else {'source_sha256': digest, 'variants': {}, 'camera_tracks': {}}
    if receipt['source_sha256'] != digest:
        raise RuntimeError('Keep saved assets intact; use a new revision for changed authoring.')
    for variant, rig in data['variants'].items():
        mesh = u.load_asset(rig['mesh'])
        folder = ('/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/' if variant == 'default'
                  else '/Game/Characters/KaitlinPlayer20261023/') + data.get('revision', 'ChapelPew20261116')
        routes = receipt['variants'].setdefault(variant, {})
        cameras = receipt['camera_tracks'].setdefault(variant, {})
        for phase, take in rig['clips'].items():
            role = 'Rest.ChapelPew.' + phase
            if role in routes:
                continue
            name = ('A_' if variant == 'default' else 'K_A_') + role.replace('.', '_')
            path = folder + '/' + name
            if E.does_asset_exist(path):
                raise RuntimeError('Preserve unreceipted asset: ' + path)
            clip = E.duplicate_asset(take['asset'], path)
            if not clip:
                raise RuntimeError('Could not create native pew clip: ' + path)
            ctl = clip.get_editor_property('controller')
            existing_tracks = {str(n) for n in u.AnimationLibrary.get_animation_track_names(clip)}
            ctl.open_bracket('Fit native chapel pew contacts', False)
            try:
                ctl.set_frame_rate(u.FrameRate(30, 1), False)
                ctl.set_number_of_frames(u.FrameNumber(len(take['frames']) - 1), False)
                for bone in data['changed_bones']:
                    index = rig['names'].index(bone)
                    keys = [f[index] for f in take['frames']]
                    if bone not in existing_tracks:
                        ctl.add_bone_curve(bone, False)
                    if not ctl.set_bone_track_keys(bone, [u.Vector(*k[:3]) for k in keys],
                                                   [u.Quat(*k[3:7]) for k in keys],
                                                   [u.Vector(*k[7:]) for k in keys], False):
                        raise RuntimeError('Pew bone track failed: ' + bone)
            finally:
                ctl.close_bracket(False)
            if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not E.save_loaded_asset(clip, False):
                raise RuntimeError('Pew animation compilation/save failed: ' + role)
            # Camera production samples this saved native animation, without a second retarget.
            eyes = []
            for i in range(len(take['frames'])):
                pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, i / 30, options(mesh))
                head = u.AnimPoseExtensions.get_bone_pose(pose, 'head', u.AnimPoseSpaces.WORLD)
                eye = head.transform_location(u.Vector(*rig['eye_offset']))
                eyes.append([eye.x, eye.y, eye.z])
            routes[role] = clip.get_path_name()
            cameras[role] = {'duration': clip.get_play_length(), 'eyes': eyes, 'animation': clip.get_path_name()}
            receipt_path.write_text(json.dumps(receipt, separators=(',', ':')), encoding='utf-8')
            print('CHAPEL_PEW_SAVED', variant, role, flush=True)
    receipt['saved'] = True
    receipt_path.write_text(json.dumps(receipt, separators=(',', ':')), encoding='utf-8')
    print('CHAPEL_PEW_ASSETS_COMPLETE', flush=True)
