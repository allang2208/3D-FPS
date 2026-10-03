"""Pick the correction for the sprint_loop pose by direct measurement.

The loop's pose is static, so its correction should be a constant, and the entry's
last frame must use that same constant or the enter -> loop crossfade bends the arm.
Sprint44's straight-line target and Sprint43's optimiser disagree on this pose and
their deviations from the mean are exact negations of each other - a branch
difference, where the surface profile is a circular quantity and the sign of a bump
matters.  So measure the candidates instead of arguing about them, wrap-safe.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Sprint44'

spec = importlib.util.spec_from_file_location('elbow39_author', E39 / 'author_elbow39.py')
E = importlib.util.module_from_spec(spec)
sys.modules['elbow39_author'] = E
spec.loader.exec_module(E)

RAMPED = E.RAMPED
FIT = getattr(E, 'FIT', None)
if FIT is None:
    FIT = E.BIN_OK & (E.BIN_T >= -0.10) & (E.BIN_T <= 0.90)

CANDIDATES = {
    'zero': (0.0, 0.0, 0.0),
    's44_loop': (75.0, 35.0, 19.64),
    's44_negated': (-75.0, -35.0, -19.64),
    's44_enter_boundary': (-75.0, -35.0, -30.0),
    's44_enter_boundary_neg': (75.0, 35.0, 30.0),
    's43_absolute': (65.0, 65.0, 64.64),
    's43_absolute_neg': (-65.0, -65.0, -64.64),
}

BLEND = ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend'
ACTION = 'PKM17_base_sprint_loop'

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
act = bpy.data.actions[ACTION]
rig.animation_data.action = act
rig.animation_data.action_slot = act.slots[0]
scene.render.fps = 120
start, end = map(int, act.frame_range)

frames = []
for frame in range(start, end + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pose = {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.pose.bones}
    e = np.array(pose['lowerarm_l'].translation)
    s = np.array(pose['upperarm_l'].translation)
    w = np.array(pose['hand_l'].translation)
    base = np.tile(np.eye(4), (len(E.V7_BONES), 1, 1))
    for i, n in enumerate(E.V7_BONES):
        if n in pose:
            base[i] = np.array(pose[n] @ E.AU_REST_M[E.AU_INDEX[n]].inverted())
    frames.append({'pose': pose, 'e': e,
                   'u': (e - s) / np.linalg.norm(e - s),
                   'f': (w - e) / np.linalg.norm(w - e), 'base': base})


def profile_of(fr, corr):
    skin = np.copy(fr['base'])
    for name, ang in zip(RAMPED, corr):
        if abs(ang) < 1e-9:
            continue
        h = fr['pose'][name].translation
        skin[E.V7_BONES.index(name)] = np.array(
            Matrix.Translation(h)
            @ Matrix.Rotation(math.radians(float(ang)), 4, Vector(fr['f'].tolist()))
            @ Matrix.Translation(-h)
            @ fr['pose'][name] @ E.AU_REST_M[E.AU_INDEX[name]].inverted())
    return E.roll_profile(E.deform_arm(skin), fr['e'], fr['u'], fr['f'])


def unwrap_cols(prof):
    out = np.array(prof, dtype=np.float64)
    for b in range(out.shape[1]):
        col = out[:, b]
        for i in range(1, len(col)):
            if np.isnan(col[i]) or np.isnan(col[i - 1]):
                continue
            while col[i] - col[i - 1] > 180.0:
                col[i] -= 360.0
            while col[i - 1] - col[i] > 180.0:
                col[i] += 360.0
    return out


def unwrap_band(v):
    """Unwrap along the band axis too: the profile is circular, and a rigid forearm
    twist must not be able to change a smoothness score."""
    out = np.array(v, dtype=np.float64)
    for i in range(1, len(out)):
        if np.isnan(out[i]) or np.isnan(out[i - 1]):
            continue
        while out[i] - out[i - 1] > 180.0:
            out[i] -= 360.0
        while out[i - 1] - out[i] > 180.0:
            out[i] += 360.0
    return out


results = {}
for tag, corr in CANDIDATES.items():
    prof = unwrap_cols([profile_of(fr, corr) for fr in frames])
    worst, tv, rate = 0.0, 0.0, 0.0
    for p in prof:
        v = unwrap_band(p[FIT])
        d = np.diff(v)
        worst = max(worst, float(np.clip(d, 0, None).max()))
        tv = max(tv, float(np.abs(d).sum()))
    rate = float(np.abs(np.diff(prof[:, FIT], axis=0)).max())
    dev = np.array(corr) - np.mean(corr)
    results[tag] = {'corr': list(corr), 'worst_step': round(worst, 1),
                    'tv': round(tv, 1), 'deviation_from_mean': [round(float(x), 1) for x in dev]}
    print('  %-22s corr %-24s worst_step %6.1f  TV %6.1f  dev %s'
          % (tag, tuple(round(c, 1) for c in corr), worst, tv,
             tuple(round(float(x), 1) for x in dev)))

best = min(results, key=lambda k: results[k]['worst_step'] + 0.02 * results[k]['tv'])
print('\nBEST %s -> %s' % (best, results[best]))
(HERE / 'loop_constant.json').write_text(
    json.dumps({'candidates': results, 'best': best}, indent=2), encoding='utf-8')
print('PICK_LOOP_CONSTANT_DONE')