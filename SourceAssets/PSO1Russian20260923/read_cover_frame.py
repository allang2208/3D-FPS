"""Measure the PKM_Cover rest frame in component space (read-only)."""
import unreal as u
import json
from pathlib import Path

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
mesh = u.load_asset('/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular')
pose = u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)


def unpack(t):
    l, r = t.translation, t.rotation
    s = getattr(t, 'scale', None) or getattr(t, 'scale3d', None)
    s = [1.0, 1.0, 1.0] if s is None else [s.x, s.y, s.z]
    return {'loc_cm': [l.x, l.y, l.z], 'quat_xyzw': [r.x, r.y, r.z, r.w], 'scale': s}


out = {}
for name in ('WPN_root', 'PKM_Cover', 'PKM_Tray', 'PKM_CarryHandle'):
    rec = {}
    for key, space in (('local', u.AnimPoseSpaces.LOCAL), ('world', u.AnimPoseSpaces.WORLD)):
        try:
            rec[key] = unpack(u.AnimPoseExtensions.get_ref_bone_pose(pose, name, space))
        except Exception as exc:
            rec[key] = 'ERR %s' % exc
    out[name] = rec
(O / 'cover_frame.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('PSO1_COVER_FRAME ' + json.dumps({k: v.get('world') for k, v in out.items()}))
print('PSO1_COVER_LOCAL ' + json.dumps({k: v.get('local') for k, v in out.items()}))
