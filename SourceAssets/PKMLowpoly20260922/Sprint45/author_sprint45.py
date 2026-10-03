"""Sprint45: remove the wrist-twist spike that collapses the palm in the sprint entry.

Sprint44 fixed the forearm surface and the single-frame snap, but measuring the palm
against the accepted idle baseline showed the palm's linear-blend skinning still goes
non-rigid for about four frames:

    frame   palm |B'B-I| p99    rel(hand_l, lowerarm_twist_01_l)
    f2          0.693            51.6        idle baseline is 0.693
    f3          0.861            98.0
    f4          1.202           151.4
    f5          1.183           155.6        <- near the 180 deg worst case
    f6          0.861           108.1
    f7          0.681            69.8
    f9          0.677            31.0        settled, equals the baseline

The palm blends hand_l with the three forearm bones, and the collapse tracks the
relative rotation between them - an authored wrist-twist spike across f2-f8, present
in the untouched Combat17 authoring (Sprint44 does not create it and only moves the
peak from 1.234 to 1.202).

The fix adds a twist about the live forearm axis, equally to all three ramped bones,
so the forearm follows the hand more closely through the spike.  A common twist is a
rigid rotation of the forearm skin: it leaves the relative rolls between those bones
alone, which is what shapes the surface profile Sprint44 optimised, and hand_l keeps
its world matrix exactly as before.  The amount is not guessed - it is searched per
frame against the measured palm collapse, then smoothed in time and forced back to
zero outside the spike.
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
HERE = ROOT / 'Sprint45'
EXPORT = HERE / 'Exports'
EDIT = HERE / 'Edit'
for d in (EXPORT, EDIT):
    d.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location('elbow39_author', E39 / 'author_elbow39.py')
E = importlib.util.module_from_spec(spec)
sys.modules['elbow39_author'] = E
spec.loader.exec_module(E)

RAMPED = E.RAMPED
ORDER = E.ORDER
AU_INDEX = E.AU_INDEX
COLLAPSE_LIMIT = 0.85       # above the idle baseline of 0.693
DELTAS = np.arange(-60.0, 60.1, 5.0)
SMOOTH_TAPS = 3

md = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
V7_BONES = list(md['bones'])
WIDX, WVAL = md['w_idx'], md['w_val'].astype(np.float64)
W = np.zeros((len(md['verts']), len(V7_BONES)))
for k in range(WIDX.shape[1]):
    i2, w = WIDX[:, k], WVAL[:, k]
    a = (i2 >= 0) & (w > 0)
    np.add.at(W, (np.where(a)[0], i2[a]), w[a])
PALM = {n for n in V7_BONES if n == 'hand_l' or n.endswith('_metacarpal_l')}
FINGER = {n for n in V7_BONES if n.endswith('_l') and n.startswith(
    ('thumb_0', 'index_0', 'middle_0', 'ring_0', 'pinky_0'))}
pi = [V7_BONES.index(n) for n in PALM]
fi = [V7_BONES.index(n) for n in FINGER]
psh, fsh = W[:, pi].sum(axis=1), W[:, fi].sum(axis=1)
PALMV = np.where((psh > 0.6) & (fsh < 0.2))[0]

CLIPS = (
    ('sprint_enter', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_enter_Sprint44.blend',
     'PKM_sprint_enter_Sprint44', EXPORT / 'A_PKM_sprint_enter.fbx',
     'PKM_sprint_enter_Sprint45'),
    ('sprint_exit', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_exit_Sprint44.blend',
     'PKM_sprint_exit_Sprint44', EXPORT / 'A_PKM_sprint_exit.fbx',
     'PKM_sprint_exit_Sprint45'),
)


def skin_of(pose):
    skin = np.tile(np.eye(4), (len(V7_BONES), 1, 1))
    for i, n in enumerate(V7_BONES):
        if n in pose:
            skin[i] = np.array(pose[n]) @ np.linalg.inv(np.array(E.AU_REST_M[AU_INDEX[n]]))
    return skin


def palm_collapse(skin):
    B = np.zeros((len(PALMV), 3, 3))
    for k in range(WIDX.shape[1]):
        idx, w = WIDX[PALMV, k], WVAL[PALMV, k]
        a = (idx >= 0) & (w > 0)
        B[a] += w[a, None, None] * skin[idx[a]][:, :3, :3]
    M = np.einsum('nji,njk->nik', B, B) - np.eye(3)
    return float(np.percentile(np.linalg.norm(M, axis=(1, 2)), 99))


def with_twist(fr, delta, prof=(1.0, 1.0, 1.0)):
    skin = np.copy(fr['skin'])
    if abs(delta) < 1e-9:
        return skin
    fv = Vector(fr['f'].tolist())
    for k, name in enumerate(RAMPED):
        local = float(delta) * prof[k]
        if abs(local) < 1e-9:
            continue
        h = fr['pose'][name].translation
        base = np.array(fr['pose'][name]) @ np.linalg.inv(np.array(E.AU_REST_M[AU_INDEX[name]]))
        skin[V7_BONES.index(name)] = np.array(
            Matrix.Translation(h)
            @ Matrix.Rotation(math.radians(local), 4, fv)
            @ Matrix.Translation(-h)) @ base
    return skin


def run(label, blend, action_name, dest, edit_name):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    source = bpy.data.actions[action_name]
    rig.animation_data.action = source
    rig.animation_data.action_slot = source.slots[0]
    scene.render.fps = 120
    scene.render.fps_base = 1.0
    start, end = map(int, source.frame_range)

    rest_local = {}
    for b in rig.data.bones:
        rest_local[b.name] = ((b.parent.matrix_local.inverted() @ b.matrix_local)
                              if b.parent else b.matrix_local.copy())
    PARENT = {n: rig.data.bones[n].parent.name for n in ORDER}

    frames = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.pose.bones}
        e = np.array(pose['lowerarm_l'].translation)
        s = np.array(pose['upperarm_l'].translation)
        w = np.array(pose['hand_l'].translation)
        frames.append({'pose': pose, 'skin': skin_of(pose), 'e': e,
                       'u': (e - s) / np.linalg.norm(e - s),
                       'f': (w - e) / np.linalg.norm(w - e),
                       'base': skin_of(pose).copy()})

    before = [palm_collapse(fr['skin']) for fr in frames]
    over = [i for i, v in enumerate(before) if v > COLLAPSE_LIMIT]
    print('  collapse before: peak %.4f at f%d ; %d frames over %.2f %s'
          % (max(before), start + int(np.argmax(before)), len(over),
             COLLAPSE_LIMIT, [start + i for i in over]), flush=True)

    # search the extra twist per frame, then keep it only where it helps
    # How the extra twist is distributed along the forearm matters.  A common twist is
    # a rigid rotation of the whole forearm and only moves the relative angle by the
    # same amount; concentrating it on the wrist-end bone (station 0.85) can pull the
    # palm's blend partners together without dragging the mid-forearm and elbow.  The
    # profiles are ordered like E.RAMPED = (lowerarm_l, twist_02, twist_01).
    PROFS = ((1.0, 1.0, 1.0), (0.0, 0.0, 1.0), (0.0, 0.5, 1.0), (0.0, 0.25, 1.0),
             (0.25, 0.5, 1.0))
    lo = max(0, min(over) - 1) if over else 0
    hi = min(len(frames) - 1, max(over) + 1) if over else 0
    env = np.zeros(len(frames))
    span = hi - lo + 1
    if span > 1:
        env[lo:hi + 1] = 0.5 * (1.0 - np.cos(2.0 * np.pi * np.arange(span)
                                             / (span - 1.0)))
    elif span == 1:
        env[lo] = 1.0

    applied, keep, best = (1.0, 1.0, 1.0), np.zeros(len(frames)), None
    for probe in PROFS:
        for amp in DELTAS:
            if abs(amp) < 1e-9:
                continue
            cand = env * float(amp)
            peak = max(palm_collapse(with_twist(frames[i], cand[i], probe))
                       if lo <= i <= hi else before[i] for i in range(len(frames)))
            if best is None or peak < best[0] - 1e-4:
                best = (peak, probe, cand)
        print('    profile %-18s best so far %.4f'
              % (str(probe), best[0] if best else float('nan')), flush=True)
    if best:
        applied, keep = best[1], best[2]
        print('    chosen %s amplitude %.1f deg (peak %.4f)'
              % (str(applied), float(np.abs(keep).max()), best[0]), flush=True)

    after = [palm_collapse(with_twist(fr, d, applied)) for fr, d in zip(frames, keep)]
    print('  collapse after : peak %.4f at f%d' % (max(after), int(np.argmax(after))),
          flush=True)
    print('  extra twist: max |d| %.1f deg, max |d per frame| %.2f deg, window f%d..f%d'
          % (float(np.abs(keep).max()), float(np.abs(np.diff(keep)).max()),
             start + lo, start + hi), flush=True)

    # forearm surface must not regress: measure the banded roll profile
    FIT = getattr(E, 'FIT', None)
    if FIT is None:
        FIT = E.BIN_OK & (E.BIN_T >= -0.10) & (E.BIN_T <= 0.90)

    def prof(fr, delta, ap=(1.0, 1.0, 1.0)):
        return E.roll_profile(
            E.deform_arm(with_twist(fr, delta, ap)), fr['e'], fr['u'], fr['f'])

    def surf(vals):
        worst = tv = 0.0
        for v in vals:
            vv = np.array(v, dtype=np.float64)
            for i in range(1, len(vv)):
                if np.isnan(vv[i]) or np.isnan(vv[i - 1]):
                    continue
                while vv[i] - vv[i - 1] > 180.0:
                    vv[i] -= 360.0
                while vv[i - 1] - vv[i] > 180.0:
                    vv[i] += 360.0
            d = np.diff(np.nan_to_num(vv[FIT], nan=0.0))
            worst = max(worst, float(np.clip(d, 0, None).max()))
            tv = max(tv, float(np.abs(d).sum()))
        return worst, tv

    p0 = [prof(fr, 0.0) for fr in frames]
    p1 = [prof(fr, d, applied) for fr, d in zip(frames, keep)]
    w0, t0 = surf(p0)
    w1, t1 = surf(p1)
    print('  forearm surface worst_step %.1f -> %.1f ; TV %.1f -> %.1f'
          % (w0, w1, t0, t1), flush=True)

    # apply: add the extra twist on top of the pose already in the blend
    action = source.copy()
    action.name = edit_name
    action.use_fake_user = True
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in list(bag.fcurves):
                    if any('"%s"' % n in curve.data_path for n in ORDER):
                        bag.fcurves.remove(curve)

    previous = {}
    max_hand_drift = 0.0
    for i, frame in enumerate(range(start, end + 1)):
        fr = frames[i]
        d = float(keep[i])
        world = {}
        for name in ORDER:
            m = fr['pose'][name].copy()
            local = d * applied[RAMPED.index(name)] if name in RAMPED else 0.0
            if abs(local) > 1e-9:
                h = fr['pose'][name].translation
                m = (Matrix.Translation(h)
                     @ Matrix.Rotation(math.radians(local), 4, Vector(fr['f'].tolist()))
                     @ Matrix.Translation(-h) @ m)
            world[name] = m
        for name in ORDER:
            pm = world[PARENT[name]] if PARENT[name] in world else fr['pose'][PARENT[name]]
            basis = (pm @ rest_local[name]).inverted() @ world[name]
            loc, quat, scl = basis.decompose()
            if name in previous and quat.dot(previous[name]) < 0.0:
                quat.negate()
            previous[name] = quat.copy()
            bone = rig.pose.bones[name]
            bone.rotation_mode = 'QUATERNION'
            bone.location, bone.rotation_quaternion, bone.scale = loc, quat, scl
            for ch in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(ch, frame=frame, group=name)
        max_hand_drift = max(max_hand_drift,
                             float((world['hand_l'].translation
                                    - fr['pose']['hand_l'].translation).length))

    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if any('"%s"' % n in curve.data_path for n in ORDER):
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'

    scene.frame_start, scene.frame_end = start, end
    scene.frame_set(start)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(
        filepath=str(dest), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
        bake_anim=True, bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
    bpy.ops.wm.save_as_mainfile(filepath=str(EDIT / (edit_name + '.blend')))
    return {'frames': len(frames), 'action': action.name,
            'collapse_before_peak': round(max(before), 4),
            'collapse_after_peak': round(max(after), 4),
            'collapse_before': [round(v, 4) for v in before],
            'collapse_after': [round(v, 4) for v in after],
            'extra_twist': [round(float(v), 2) for v in keep],
            'extra_twist_max': round(float(np.abs(keep).max() * max(applied)), 2),
            'profile': list(applied),
            'extra_twist_max_step': round(float(np.abs(np.diff(keep)).max()), 2),
            'surface_before': [round(w0, 1), round(t0, 1)],
            'surface_after': [round(w1, 1), round(t1, 1)],
            'max_hand_drift': max_hand_drift,
            'window': [start + lo, start + hi] if over else None}


ONLY = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
results = {}
for label, blend, action_name, dest, edit_name in CLIPS:
    if ONLY and label not in ONLY:
        continue
    print('\n=== %s (%s) ===' % (label, action_name), flush=True)
    res = run(label, blend, action_name, dest, edit_name)
    results[label] = dict(res, source_blend=str(blend), export=str(dest),
                          edit=str(EDIT / (edit_name + '.blend')))
    print('EXPORTED %s  hand drift %.3e' % (dest.name, res['max_hand_drift']), flush=True)

(HERE / 'authoring_sprint45.json').write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
print('\nSPRINT45_AUTHOR_DONE')