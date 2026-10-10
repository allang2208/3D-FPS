"""Explicit, read-only review of the accepted food clips; never save assets or run play."""
import hashlib
import json
import math
from pathlib import Path

import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonFoodReview20261010'
OUT.mkdir(parents=True, exist_ok=True)
payload = (ROOT/'SourceAssets/ThirdPersonFoodNative20261010/authored.json').read_bytes()
authored = json.loads(payload)
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
motion = json.loads((ROOT/'Content/ColdSteelData/potion_use_motion.json').read_text(encoding='utf-8-sig'))
mesh = u.load_asset(cfg['body_mesh'])


def pack(t):
    return [*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z,
            t.rotation.w, *t.scale3d.to_tuple()]


def angle(a, b):
    norm = math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
    return math.degrees(2.*math.acos(min(1., abs(sum(x*y for x, y in zip(a, b)))/norm)))


def file_hash(asset):
    path = ROOT/'Content'/(asset.split('.')[0].removeprefix('/Game/')+'.uasset')
    return hashlib.sha256(path.read_bytes()).hexdigest()


report = dict(scope='All saved food bone tracks at 60 Hz, source/compressed data and current configuration; no gameplay or rendering.',
              clips={}, gameplay_tested=False, rendered=False, assets_modified=False)
drink = cfg['clips']['Consume.Drink']
report['drink_hash'] = file_hash(drink)
prior = json.loads((ROOT/'SourceAssets/ThirdPersonFoodUpperarmFix20261010/diagnosis.json').read_text())
report['drink_matches_accepted_hash'] = report['drink_hash'] == prior['drink_hash']
for key, definition in authored['clips'].items():
    clip = u.load_asset(cfg['clips'][key])
    duration = clip.get_play_length()
    rate = definition['rate']
    markers = {str(m.marker_name):m.time for m in u.AnimationLibrary.get_animation_sync_markers(clip)}
    errors = {kind:dict(position_cm=0., rotation_deg=0., scale=0.)
              for kind in ('authored_to_source', 'source_to_compressed')}
    options = []
    for mode in (u.AnimDataEvalType.SOURCE, u.AnimDataEvalType.COMPRESSED):
        option = u.AnimPoseEvaluationOptions()
        option.optional_skeletal_mesh = mesh
        option.evaluation_type = mode
        options.append(option)
    hashes = file_hash(clip.get_path_name())
    for i, frame in enumerate(definition['frames']):
        poses = [u.AnimPoseExtensions.get_anim_pose_at_time(clip, min(i/rate, duration), opt) for opt in options]
        for j, bone in enumerate(authored['names']):
            saved = [pack(u.AnimPoseExtensions.get_bone_pose(pose, bone, u.AnimPoseSpaces.LOCAL)) for pose in poses]
            for kind, a, b in [('authored_to_source', frame[j], saved[0]), ('source_to_compressed', *saved)]:
                out = errors[kind]
                out['position_cm'] = max(out['position_cm'], math.dist(a[:3], b[:3]))
                out['rotation_deg'] = max(out['rotation_deg'], angle(a[3:7], b[3:7]))
                out['scale'] = max(out['scale'], max(abs(x-y) for x, y in zip(a[7:], b[7:])))
    bounds = u.load_asset('/Game/Items/Consumables/'+('Bread20261003/SM_Bread' if definition['food']=='bread'
                           else 'Baguette20261003/SM_Baguette')).get_bounds()
    contact = [bounds.origin.x, bounds.origin.y, bounds.origin.z+bounds.box_extent.z]
    checks = dict(
        skeleton_matches=clip.get_editor_property('skeleton') == mesh.skeleton,
        duration_matches=abs(duration-definition['times']['duration']) < 1.e-5,
        current_item_timing_matches=definition['times'] == motion[definition['food']]['times'],
        native_marker_present='NativeConsumeArm' in markers,
        contact_marker_matches=abs(markers.get('Contact', -1.)-definition['contact']*duration) < 1.e-5,
        release_marker_matches=abs(markers.get('Release', -1.)-definition['release']*duration) < 1.e-5,
        author_hash_matches=u.EditorAssetLibrary.get_metadata_tag(clip, 'SourceHash') == hashlib.sha256(payload).hexdigest(),
        runtime_food_bounds_match=math.dist(contact, definition['contact_point']) < .01,
        source_matches_author=errors['authored_to_source']['position_cm'] < .01 and errors['authored_to_source']['rotation_deg'] < .01,
        compression_preserves_pose=errors['source_to_compressed']['position_cm'] < .1 and errors['source_to_compressed']['rotation_deg'] < .25,
        scale_preserved=max(v['scale'] for v in errors.values()) < .001,
        asset_unchanged=file_hash(clip.get_path_name()) == hashes)
    report['clips'][key] = dict(asset=clip.get_path_name(), frames=len(definition['frames']),
                              bones=len(authored['names']), markers=markers, errors=errors, checks=checks)
report['drink_unchanged_during_review'] = file_hash(drink) == report['drink_hash']
report['passed'] = report['drink_matches_accepted_hash'] and report['drink_unchanged_during_review'] and all(
    all(row['checks'].values()) for row in report['clips'].values())
(OUT/'saved-animation-review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('FOOD_REVIEW', json.dumps(report))
