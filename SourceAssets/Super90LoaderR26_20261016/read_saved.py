"""Read back the installed loader clips and grip entries; compare with inputs.json and the R26 patch."""
import json, math
from pathlib import Path
import unreal as u
O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text())
P = json.loads((O / 'animation_patch.json').read_text())
mesh = u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.should_retarget = False
bones = ['hand_l', 'lowerarm_l', 'middle_02_l']
frames = [60, 90, 100, 111, 112, 116, 121, 130]


def angle(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    return math.degrees(2 * math.acos(min(1., d)))


def key(track, f):
    v = track['values']
    return v[f * 10:f * 10 + 10] if len(track['times']) > 1 else v[:10]


out = {}
for role in ('normal_7', 'empty_7', 'normal_1'):
    clip = D['clips'][role]
    asset = u.load_asset(clip['path'].split('.')[0])
    tracks = {t['bone']: t for t in P['clips'][role]['tracks']}
    rows = {}
    for kind in ('SOURCE', 'COMPRESSED'):
        options.evaluation_type = getattr(u.AnimDataEvalType, kind)
        for f in frames:
            pose = u.AnimPoseExtensions.get_anim_pose_at_time(asset, f / 60., options)
            for b in bones:
                t = u.AnimPoseExtensions.get_bone_pose(pose, b, u.AnimPoseSpaces.LOCAL)
                q = [t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w]
                rows.setdefault(kind, []).append(dict(frame=f, bone=b,
                    vs_installed_deg=round(angle(q, clip['rows'][f][b][3:7]), 3),
                    vs_patch_deg=round(angle(q, key(tracks[b], f)[3:7]), 3) if b in tracks else None))
    out[role] = dict(meta=E.get_metadata_tag(asset, 'Super90LoaderR26') if (E := u.EditorAssetLibrary) else None,
                     frames=u.AnimationLibrary.get_num_frames(asset), rows=rows)
profile = u.load_asset('/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_vertical')
want = P['profiles']['vertical']['clips']
seen = {}
for c in profile.get_editor_property('clips'):
    path = c.get_editor_property('base').get_path_name()
    if path in want:
        got = {str(t.get_editor_property('bone')): len(t.get_editor_property('times')) for t in c.get_editor_property('tracks')}
        seen[path.rsplit('.', 1)[-1]] = all(got.get(t['bone']) == len(t['times']) for t in want[path]['tracks'])
out['vertical_profile_matches_patch'] = seen
(O / 'saved_readback.json').write_text(json.dumps(out, indent=1))
for role in ('normal_7', 'empty_7', 'normal_1'):
    item = out[role]
    print('R26_READBACK', role, 'tag', item['meta'], 'frames', item['frames'])
    for r in item['rows']['COMPRESSED']:
        if r['bone'] == 'hand_l':
            print('   f%3d hand_l vs installed %.2f deg, vs patch %s' % (r['frame'], r['vs_installed_deg'], r['vs_patch_deg']))
print('R26_PROFILE', json.dumps(seen))
