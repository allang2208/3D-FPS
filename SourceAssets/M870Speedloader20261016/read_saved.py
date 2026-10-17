"""Read back the saved M870 loader assets and compare with the authored data (no save)."""
import json, math
from pathlib import Path
import unreal as u
O = Path(__file__).parent
C = json.loads((O / 'clips.json').read_text()); names = json.loads((O / 'inputs.json').read_text())['m870']['names']
mesh = u.load_asset('/Game/Weapons/M870/Tactical20261015/SK_M870_V7')
opt = u.AnimPoseEvaluationOptions(); opt.optional_skeletal_mesh = mesh; opt.should_retarget = False
opt.evaluation_type = u.AnimDataEvalType.COMPRESSED
out = {}
for role in ('normal_1', 'normal_7', 'empty_1', 'empty_7'):
    a = u.load_asset('/Game/Weapons/M870/Speedloader20261016/Animations/A_M870_loader_' + role)
    worst = (0., ''); frames = C[role]['frames']
    for f in (0, 30, 87, 100, 110, 124, 135, 144, 160, 181, frames):
        if f > frames: continue
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(a, f / 60., opt)
        for n in names:
            t = u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL); r = C[role]['rows'][f][n]
            d = abs(t.rotation.x * r[3] + t.rotation.y * r[4] + t.rotation.z * r[5] + t.rotation.w * r[6])
            ang = math.degrees(2 * math.acos(min(1., d)))
            if ang > worst[0]: worst = (ang, '%s@%d' % (n, f))
    out[role] = dict(length=a.get_play_length(), frames=u.AnimationLibrary.get_num_frames(a), tag=u.EditorAssetLibrary.get_metadata_tag(a, 'M870Speedloader20261016') != '',
                     max_rotation_diff_deg=round(worst[0], 4), at=worst[1], skeleton=a.get_editor_property('skeleton').get_path_name())
    print('M870_LOADER_READ', role, json.dumps(out[role]), flush=True)
g = u.load_asset('/Game/Weapons/M870/Speedloader20261016/SM_M870_LoaderGuide')
b = g.get_bounding_box()
out['guide'] = dict(materials=[m.material_interface.get_path_name() for m in g.static_materials], bounds_min=[b.min.x, b.min.y, b.min.z], bounds_max=[b.max.x, b.max.y, b.max.z])
for fam in ('vertical', 'canted', 'prism', 'angled'):
    p = u.load_asset('/Game/Weapons/M870/CommonFurniture20261016/Profiles/DA_M870_' + fam)
    bases = [c.get_editor_property('base').get_name() for c in p.get_editor_property('clips')]
    out[fam] = dict(entries=len(bases), loader_entries=sum('loader' in x for x in bases))
print('M870_LOADER_READ_GUIDE', json.dumps(out['guide']), json.dumps({f: out[f] for f in ('vertical', 'canted', 'prism', 'angled')}), flush=True)
(O / 'saved_readback.json').write_text(json.dumps(out, indent=1))
