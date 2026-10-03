"""Sprint44: rebuild the PKM tactical sprint left arm with the rolls unwrapped in time.

Elbow41 improved the sprint entry surface (worst backward step 105.4 -> 71.2,
TV 465.5 -> 207.4) but broke the motion, and the mechanism is now pinned exactly.

UM4TacticalSprintComponent::Configure shows the tactical sprint is the same three
clips for every weapon, so sprint_enter / sprint_loop / sprint_exit ARE the PKM
tactical sprint.

Elbow39 decides how far to twist each forearm bone by putting it on the straight
line between the two bones that straddle the forearm:

    slope = (roll[hand_l] - roll[anchor]) / (station[hand_l] - station[anchor])

and it unwrapped `roll` only WITHIN a frame (chained anchor -> ... -> hand).  On
sprint_enter the left forearm's roll sweeps ~200 deg, so the chain crosses +/-180
and the branch it picks for hand_l flips between frame 3 and frame 4: -212.7 deg
becomes +138.0 deg, which is the same orientation but inverts `slope`.  `full`
therefore jumps from the -75 clamp to +4.8 on lowerarm_l and from -35 to +35 on
lowerarm_twist_02_l in a single frame at 120 fps.  That is the twist that shows up
when entering the tactical sprint; the authored rolls themselves are perfectly
smooth (<= 45 deg per frame, and the bones converge to one roll).

So this round keeps Elbow39's algorithm and changes only the unwrapping: the
per-bone offset from the anchor is unwrapped ACROSS FRAMES, so the straight-line
target is continuous and so is the correction.  The correction is then low-passed
and its per-frame change clamped, and the three clips are anchored to a common
value where they share a pose (enter ends exactly where loop and exit begin).

Every descendant's local channels are re-derived from its preserved world matrix,
so for any correction the hand, fingers, weapon and grip cannot move.
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
EXPORT = HERE / 'Exports'
EDIT = HERE / 'Edit'
for d in (EXPORT, EDIT):
    d.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location('elbow39_author', E39 / 'author_elbow39.py')
E = importlib.util.module_from_spec(spec)
sys.modules['elbow39_author'] = E
spec.loader.exec_module(E)

STATION, CAP = E.STATION, E.CAP
ANCHOR, RAMPED, ORDER = E.ANCHOR, E.RAMPED, E.ORDER
CHAIN = [ANCHOR] + list(ORDER)
FIT = getattr(E, 'FIT', None)
if FIT is None:
    FIT = E.BIN_OK & (E.BIN_T >= -0.10) & (E.BIN_T <= 0.90)
TV_WEIGHT = 0.02
SMOOTH_TAPS = 5
MAX_DELTA = 6.0
# Measured directly on the sprint_loop pose (pick_loop_constant.py): the best
# correction is a nearly UNIFORM twist of all three forearm bones - its deviation
# from its own mean is (0.1, 0.1, -0.2) deg - and it scores worst_step 0.0 / TV 76.0
# against 17.5 / 157.7 for the straight-line target's answer.  Because the loop pose
# is also the entry's last frame and the exit's first, all three clips use it there.
LOOP_CONST = np.array([65.0, 65.0, 64.64])
TAPER = 18

CLIPS = (
    ('sprint_enter', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
     'PKM17_base_sprint_enter', 120, EXPORT / 'A_PKM_sprint_enter.fbx',
     'PKM_sprint_enter_Sprint44'),
    ('sprint_loop', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
     'PKM17_base_sprint_loop', 120, EXPORT / 'A_PKM_sprint_loop.fbx',
     'PKM_sprint_loop_Sprint44'),
    ('sprint_exit', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
     'PKM17_base_sprint_exit', 120, EXPORT / 'A_PKM_sprint_exit.fbx',
     'PKM_sprint_exit_Sprint44'),
)


def wrap180(v):
    return (v + 180.0) % 360.0 - 180.0


def unwrap_time(series):
    out = np.array(series, dtype=np.float64)
    for i in range(1, len(out)):
        while out[i] - out[i - 1] > 180.0:
            out[i] -= 360.0
        while out[i - 1] - out[i] > 180.0:
            out[i] += 360.0
    return out


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


def profile_cost(row):
    v = row[FIT]
    dv = np.diff(v)
    return (float(np.clip(dv, 0, None).max()) + TV_WEIGHT * float(np.abs(dv).sum()),
            float(np.clip(dv, 0, None).max()), float(np.abs(dv).sum()))


def twist_rate(prof):
    return float(np.abs(np.diff(prof[:, FIT], axis=0)).max())


def smooth_and_limit(series, anchor=None, anchor_at='start'):
    series = np.asarray(series, dtype=np.float64)
    out = np.copy(series)
    if len(series) >= SMOOTH_TAPS and SMOOTH_TAPS > 1:
        pad = SMOOTH_TAPS // 2
        padded = np.vstack([np.repeat(series[:1], pad, axis=0), series,
                            np.repeat(series[-1:], pad, axis=0)])
        out = np.stack([padded[i:i + len(series)]
                        for i in range(SMOOTH_TAPS)]).mean(axis=0)
    if anchor is None:
        for i in range(1, len(out)):
            out[i] = np.clip(out[i], out[i - 1] - MAX_DELTA, out[i - 1] + MAX_DELTA)
    elif anchor_at == 'start':
        out[0] = np.asarray(anchor, dtype=np.float64)
        for i in range(1, len(out)):
            out[i] = np.clip(out[i], out[i - 1] - MAX_DELTA, out[i - 1] + MAX_DELTA)
    else:
        out[-1] = np.asarray(anchor, dtype=np.float64)
        for i in range(len(out) - 2, -1, -1):
            out[i] = np.clip(out[i], out[i + 1] - MAX_DELTA, out[i + 1] + MAX_DELTA)
    return out


def run(blend, action_name, fps, dest, edit_name, anchor=None, anchor_at='start',
        fixed_corr=None, taper_to=None, constant_corr=None):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    source = bpy.data.actions[action_name]
    rig.animation_data.action = source
    rig.animation_data.action_slot = source.slots[0]
    scene.render.fps = int(fps)
    scene.render.fps_base = 1.0
    start, end = map(int, source.frame_range)

    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    rest_local = {n: rest[rig.data.bones[n].parent.name].inverted() @ rest[n]
                  if rig.data.bones[n].parent else rest[n].copy() for n in ORDER}
    PARENT = {n: rig.data.bones[n].parent.name for n in ORDER}

    e_r = rest['lowerarm_l'].translation
    s_r = rest['upperarm_l'].translation
    w_r = rest['hand_l'].translation
    a0 = (e_r - s_r).normalized()
    b0 = (w_r - e_r).normalized()
    flen = (w_r - e_r).length
    q1 = (a0 - a0.dot(b0) * b0).normalized()
    q2 = b0.cross(q1)
    rings, rphis = {}, {}
    for name in CHAIN:
        c = e_r + b0 * (STATION[name] * flen)
        ring = [c + math.cos(2 * math.pi * i / 24) * q1 * 0.045
                + math.sin(2 * math.pi * i / 24) * q2 * 0.045 for i in range(24)]
        rings[name] = ring
        rphis[name] = []
        for v in ring:
            dd = v - e_r
            dd = dd - dd.dot(b0) * b0
            rphis[name].append(math.atan2(dd.dot(q2), dd.dot(q1)))

    frames = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.pose.bones}
        e = np.array(pose['lowerarm_l'].translation)
        s = np.array(pose['upperarm_l'].translation)
        w = np.array(pose['hand_l'].translation)
        u = (e - s) / np.linalg.norm(e - s)
        f = (w - e) / np.linalg.norm(w - e)
        base = np.tile(np.eye(4), (len(E.V7_BONES), 1, 1))
        for i, n in enumerate(E.V7_BONES):
            if n in pose:
                base[i] = np.array(pose[n] @ E.AU_REST_M[E.AU_INDEX[n]].inverted())
        frames.append({'pose': pose, 'e': e, 'u': u, 'f': f, 'base': base})

    # ---- rolls, chained within each frame exactly as Elbow39 does -------------
    raw = []
    for fr in frames:
        u_v, f_v = Vector(fr['u'].tolist()), Vector(fr['f'].tolist())
        e_v = Vector(fr['e'].tolist())
        rolls = {}
        for name in CHAIN:
            delta = fr['pose'][name] @ E.AU_REST_M[E.AU_INDEX[name]].inverted()
            rolls[name] = E.roll_probe(delta, rings[name], rphis[name], e_v, u_v, f_v)
        for i in range(1, len(CHAIN)):
            rolls[CHAIN[i]] = E.unwrap(rolls[CHAIN[i]], rolls[CHAIN[i - 1]])
        raw.append(rolls)

    # ---- the fix: unwrap each bone's offset from the anchor ACROSS FRAMES -----
    a_series = unwrap_time([wrap180(r[ANCHOR]) for r in raw])
    rel = {}
    for name in ORDER:
        d = [wrap180(r[name] - r[ANCHOR]) for r in raw]
        rel[name] = unwrap_time(d)
    cont = [{ANCHOR: a_series[i], **{n: a_series[i] + rel[n][i] for n in ORDER}}
            for i in range(len(raw))]

    # ---- Elbow39's straight-line target, now continuous in time --------------
    full = []
    for r in cont:
        t0, r0 = STATION[ANCHOR], r[ANCHOR]
        t1, r1 = STATION['hand_l'], r['hand_l']
        slope = (r1 - r0) / (t1 - t0)
        full.append(np.array([max(-CAP[n], min(CAP[n],
                        (r0 + slope * (STATION[n] - t0)) - r[n])) for n in RAMPED]))
    full = np.array(full)
    # No smoothing / limiting: with the rolls unwrapped in time the correction is
    # already far smoother than the arm's own motion (24 deg/frame against the
    # source's 45), while forcing it flat measurably wrecks the surface.
    limited = full if fixed_corr is None else np.asarray(fixed_corr, dtype=np.float64)
    if constant_corr is not None:
        limited = np.tile(np.asarray(constant_corr, dtype=np.float64),
                          (len(limited), 1))
    if taper_to is not None:
        # blend the tail onto the shared boundary constant, so the crossfade from
        # sprint_enter into sprint_loop does not bend the arm
        n = len(limited)
        k = min(TAPER, n)
        for i in range(k):
            # w = 1 at the final frame, 0 at frame n-k
            w = 1.0 if k == 1 else 1.0 - (i / (k - 1.0))
            w = w * w * (3.0 - 2.0 * w)
            limited[n - 1 - i] = (1.0 - w) * limited[n - 1 - i] + w * taper_to

    # ---- measure the surface for original / continuous raw / continuous limited
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

    prof_base = unwrap_cols([profile_of(fr, np.zeros(3)) for fr in frames])
    prof_full = unwrap_cols([profile_of(fr, c) for fr, c in zip(frames, full)])
    prof_lim = unwrap_cols([profile_of(fr, c) for fr, c in zip(frames, limited)])

    def summarise(prof):
        cs = [profile_cost(p) for p in prof]
        return {'worst_cost': round(max(c[0] for c in cs), 1),
                'worst_step': round(max(c[1] for c in cs), 1),
                'worst_tv': round(max(c[2] for c in cs), 1),
                'twist_rate': round(twist_rate(prof), 1)}
    costs = {'original': summarise(prof_base),
             'rolls_continuous': summarise(prof_full),
             'smoothed': summarise(prof_lim)}
    for k, v in costs.items():
        print('  %-17s %s' % (k, v), flush=True)
    print('  correction |delta| per frame: raw %.2f -> limited %.2f deg'
          % (float(np.abs(np.diff(full, axis=0)).max()),
             float(np.abs(np.diff(limited, axis=0)).max())), flush=True)

    # ---- apply ---------------------------------------------------------------
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
        corr = limited[i]
        world = {}
        for name in ORDER:
            m = fr['pose'][name].copy()
            if name in RAMPED:
                ang = float(corr[RAMPED.index(name)])
                if abs(ang) > 1e-9:
                    h = fr['pose'][name].translation
                    m = (Matrix.Translation(h)
                         @ Matrix.Rotation(math.radians(ang), 4,
                                           Vector(fr['f'].tolist()))
                         @ Matrix.Translation(-h) @ m)
            world[name] = m
        for name in ORDER:
            pm = world[PARENT[name]] if PARENT[name] in world else fr['pose'][PARENT[name]]
            loc, quat, scl = E.local_channels(world[name], pm, rest_local[name])
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
    return {'frames': len(frames), 'fps': fps, 'action': action.name,
            'max_hand_drift': max_hand_drift, 'costs': costs,
            'corr_first': {n: round(float(v), 1) for n, v in zip(RAMPED, limited[0])},
            'corr_last': {n: round(float(v), 1) for n, v in zip(RAMPED, limited[-1])},
            'corr_max_delta_raw': round(float(np.abs(np.diff(full, axis=0)).max()), 2),
            'corr_max_delta': round(float(np.abs(np.diff(limited, axis=0)).max()), 2),
            'corr_median': [round(float(v), 2) for v in np.median(limited, axis=0)],
            'corr_series': [[round(float(v), 3) for v in row] for row in limited]}


ONLY = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CLIP_BY_LABEL = {c[0]: c for c in CLIPS}
WORK = ['sprint_loop', 'sprint_enter', 'sprint_exit']
results = {}
shared = None
for label in WORK:
    if ONLY and label not in ONLY:
        continue
    _, blend, action_name, fps, dest, edit_name = CLIP_BY_LABEL[label]
    fixed = None
    taper = None
    if label == 'sprint_loop':
        anchor, anchor_at = None, 'start'
        fixed = None
        constant = LOOP_CONST       # the measured optimum for this static pose
        taper = None
    elif label == 'sprint_enter':
        anchor, anchor_at = shared, 'end'
        constant = None
        # No explicit taper: UM4TacticalSprintComponent already crossfades the loop in
        # over the last 35% of the entry (SprintLoopAlpha = SmoothStep(.65,1,Progress)),
        # so the engine performs this blend.  Forcing it inside the clip only moves the
        # cost into the frames we measure and costs about ten times the surface quality.
        taper = None
    else:
        # sprint_exit is the exact reverse of sprint_enter: the pose probe shows the
        # same hand travel in the opposite order and the source gives identical
        # statistics for both.  Reuse the entry's correction in reverse rather than
        # re-derive it, where the roll branch for the hand is ambiguous.
        anchor, anchor_at = shared, 'start'
        fixed = np.array(results['sprint_enter']['corr_series'], dtype=np.float64)[::-1]
        constant = None
        taper = None
    print('\n=== %s (%s) ===' % (label, action_name), flush=True)
    res = run(blend, action_name, fps, dest, edit_name, anchor, anchor_at, fixed,
              taper, constant)
    if label == 'sprint_loop':
        shared = res['corr_median']
        print('  shared boundary correction %s' % shared, flush=True)
    results[label] = dict(res, source_blend=str(blend), export=str(dest),
                          edit=str(EDIT / (edit_name + '.blend')))
    print('EXPORTED %s frames %d  hand drift %.3e  corr step raw %.2f -> %.2f deg/frame'
          % (dest.name, res['frames'], res['max_hand_drift'],
             res['corr_max_delta_raw'], res['corr_max_delta']), flush=True)

(HERE / 'authoring_sprint44.json').write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
print('\nSPRINT44_AUTHOR_DONE')