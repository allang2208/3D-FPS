"""V85 R6 hybrid Inspect (user, 2026-11-02): V85's release (N0-N1) opens and its back-of-hand regrip (N4-N8) closes;
V82's open-palm spin (fingers spread, palm up) runs between them, all on one hybrid speed clock.

blender -b --factory-startup --python author_inspect_r6.py -- [--long-grip] [--no-export]
Both sources turn the sword about the same axis from the same WristLocked V4 idle, so they are sampled at the same
sword phase: V85 through its solver at v85_keys.time_of_phi(phi), V82 from its baked author action
(extract_v82_poses.py) at the V82 clock's time for that phase. The blend is hand-first (a bone-local blend swung
the hand 9 m/s, the two arms differ by up to 24 cm at the elbow): the right-hand target and finger shapes are
blended, the arm is re-solved with V85's IK, the sword keeps the hybrid clock's rotation (V85's in-plane guard roll
fades out where V82 leads, which matches V82's blade within 3-5 deg) and its hilt position blends V85's contact
placement with V82's hand-relative placement. Then the clearance search and the V9 forearm twist. Prep,
follow-through, recovery and the left hand are R5's.
"""
import bisect
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import v85_keys as C  # noqa: E402  (also puts spin_design on the path)
import v85_arm as A  # noqa: E402
import v85_setup  # noqa: E402
import v85_hand as Hd  # noqa: E402
from spin_design import Curve, smoothstep  # noqa: E402
from v85_arm import Arm  # noqa: E402
from v85_frame import BEND_CAP_FINAL, BEND_CAP_SOLVE, ELBOW_GIVE_R, Solver, mix_mat  # noqa: E402
from v85_setup import WPN  # noqa: E402
from v85_solve import solve  # noqa: E402

VARIANT = 'LongGrip' if '--long-grip' in sys.argv else 'Standard'
CLIP = 'A_RuneSword_Inspect'
OUT = HERE / 'ExportV85' / ('LongGrip' if VARIANT == 'LongGrip' else '')
BLEND = HERE / ('AzureRunesword_InspectHybridR6' + ('_LongGrip' if VARIANT == 'LongGrip' else '') + '.blend')
FPS = C.FPS

# V82 clock (author_inspect_v82.py design.PHI); every V82 channel is keyed on this phase.
V82_PHI = Curve([(0.00, 0.0), (0.18, 0.0), (0.32, -8.0), (0.38, -16.0), (0.40, -18.0), (0.448, 10.0),
                 (0.504, 75.0), (0.568, 160.0), (0.636, 245.0), (0.700, 310.0), (0.760, 346.0), (0.8224, 360.0)])


def v82_time(phi):
    lo, hi = 0.40, 0.8224
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if V82_PHI(mid) < phi else (lo, mid)
    return 0.5 * (lo + hi)


# Hybrid clock (clip seconds). Accent on the release, V82's palm spin flows and slows, the roll onto the back of
# the hand is the slow showing beat (V85's palm-to-back flip gets ~150 ms instead of ~95), then the drive home
# re-accelerates and the fist takes the blade still moving (R5 follow-through and recovery).
T0 = C.SPIN_START * C.TEMPO
SPEED = Curve([(T0, 0.0), (0.53, 650.0), (0.575, 1250.0), (0.615, 1150.0), (0.66, 950.0), (0.70, 750.0),
               (0.74, 620.0), (0.78, 480.0), (0.84, 330.0), (0.91, 320.0), (0.96, 500.0), (1.01, 680.0),
               (1.07, 620.0), (1.13, 420.0)])
T_SE = SPEED.xs[-1]
_DT = 1.0 / 2400.0
_N = int(round((T_SE - T0) / _DT))
_acc = [0.0]
for _i in range(_N):
    _acc.append(_acc[-1] + 0.5 * (SPEED(T0 + _i * _DT) + SPEED(T0 + (_i + 1) * _DT)) * _DT)
SCALE = (360.0 - C.WINDUP[-1][1]) / _acc[-1]
_TAB = [C.WINDUP[-1][1] + SCALE * a for a in _acc]
END_H = T_SE + (C.END - C.SPIN_END) * C.TEMPO

# R6b (user: "提高播放速度，跟原 M 键的速度匹配，保留节奏感"): the whole design above plays on V82's timetable — prep
# 0-0.40 s, turn 0.40-0.8224 s, settled by 1.162 s (V82 1.158 s) — through one smooth, monotone time warp, so every
# beat keeps its share of the turn. Clip time c -> design time PLAY(c).
PLAY = Curve([(0.0, 0.0), (0.06, 0.06 * T0 / 0.40), (0.40, T0), (0.8224, T_SE), (1.1624, END_H)])
END_C = PLAY.xs[-1]


def clip_of(design_t):
    lo, hi = 0.0, END_C
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if PLAY(mid) < design_t else (lo, mid)
    return 0.5 * (lo + hi)


def phi_h(t):
    if t <= T0:
        return C.phi_at(t / C.TEMPO)
    if t >= T_SE:
        return 360.0
    x = (t - T0) / _DT
    i = min(int(x), _N - 1)
    return _TAB[i] + (_TAB[i + 1] - _TAB[i]) * (x - i)


def time_h(phi):
    i = min(max(bisect.bisect_left(_TAB, phi), 1), len(_TAB) - 1)
    a, b = _TAB[i - 1], _TAB[i]
    return T0 + (i - 1 + (phi - a) / max(1e-9, b - a)) * _DT


def t85_of(t):
    if t <= T0:
        return t / C.TEMPO
    if t >= T_SE:
        return C.SPIN_END + (t - T_SE) / C.TEMPO
    return C.time_of_phi(phi_h(t))


# V82 share by clip time. The two hands are never closer than ~80 deg in the middle, so each hand-over needs time:
# in from V85's release key N1 (~100 ms, the hand opens palm-up), out across V85's own palm-to-back flip (~150 ms).
V82_IN, V82_FULL, V82_HOLD, V82_OUT = 0.60, 0.70, 0.75, 0.97


def w82(t):
    if t <= T0 or t >= T_SE:
        return 0.0
    return smoothstep((t - V82_IN) / (V82_FULL - V82_IN)) * (1.0 - smoothstep((t - V82_HOLD) / (V82_OUT - V82_HOLD)))


c = v85_setup.load(VARIANT)
S = Solver(c)
rig = c.rig
D = np.load(HERE / 'Work' / ('v82_poses_%s.npz' % VARIANT))
idx82 = {str(n): i for i, n in enumerate(D['names'])}
P82 = D['pose']
rest_err = max(float(np.abs(D['rest'][idx82[n]] - np.array([list(r) for r in c.rest[n]])).max()) for n in c.names)
if rest_err > 1e-4:
    raise RuntimeError('V82 rig rest differs from the V85 idle rig (%.6f)' % rest_err)


def v82_pose(t):
    x = min(max(t * D['fps'], 0.0), P82.shape[0] - 1.000001)
    i, a = int(x), x - int(x)
    return {n: mix_mat(Matrix(P82[i, idx82[n]].tolist()), Matrix(P82[i + 1, idx82[n]].tolist()), a) for n in c.names}


order, pending = [], set(c.names)
while pending:
    for n in list(pending):
        if c.parent[n] is None or c.parent[n] not in pending:
            order.append(n)
            pending.remove(n)


def under(n, root):
    while c.parent[n]:
        n = c.parent[n]
        if n == root:
            return True
    return False


HAND_TREE = [n for n in order if under(n, 'hand_r')]
FINGERS_R = set(c.finger_r)
HA = Arm(c.rest, c.idle, c.idle_scale)  # the hybrid arm keeps its own continuity state (synced from V85 at w = 0)
hybrid_humerus = 0.0
hand_q_prev = None


def slerp_raw(a, b, t):
    """Slerp without the shortest-path sign flip (mathutils always takes the short way)."""
    d = max(-1.0, min(1.0, a.dot(b)))
    om = math.acos(d)
    if om < 1e-6:
        return a.copy()
    s = math.sin(om)
    ka, kb = math.sin((1.0 - t) * om) / s, math.sin(t * om) / s
    return Quaternion((ka * a.w + kb * b.w, ka * a.x + kb * b.x, ka * a.y + kb * b.y, ka * a.z + kb * b.z)).normalized()


def blend(pose, t, t85, w):
    """Hand-first: V85 hand position, hand rotation slerped to V82's, arm re-solved, finger locals blended, sword
    rotation from the clock with the guard roll faded out, hilt between V85's contact and V82's hand-relative
    placement."""
    global hybrid_humerus, hand_q_prev
    old = dict(pose)
    if w <= 1e-5:
        # After the hand-over the hybrid arm keeps solving V85's own hand (its elbow and humeral roll converge
        # under the rate limits); switching straight back to V85's arm stepped the upper arm 7 deg in a frame.
        solved, _ = HA.solve(old['hand_r'], 'r', give=ELBOW_GIVE_R, bend_cap=BEND_CAP_SOLVE, follow=0.6)
        pose.update(solved)
        S.attach_helpers(pose, 'upperarm_r')
        hybrid_humerus = HA.roll_humerus(pose, 'r', hybrid_humerus)
        S.attach_helpers(pose, 'upperarm_r')
        pose['hand_r'] = old['hand_r']
        for n in HAND_TREE:
            pose[n] = old[n]
        return pose
    p82 = v82_pose(v82_time(phi_h(t)))
    qa, qb = old['hand_r'].to_quaternion(), p82['hand_r'].to_quaternion()
    # Across the palm-to-back hand-over the two hands drift past 180 deg apart; a shortest-path slerp then flips
    # direction (a 50 deg one-frame pop). Keep whichever path continues the previous frame's hand.
    cands = [slerp_raw(qa, qb, w), slerp_raw(qa, -qb, w)]
    q = cands[0] if hand_q_prev is None else max(cands, key=lambda x: abs(x.dot(hand_q_prev)))
    hand_q_prev = q.copy()
    target = Matrix.LocRotScale(old['hand_r'].translation, q, c.idle_scale['hand_r'])
    solved, _ = HA.solve(target, 'r', give=ELBOW_GIVE_R, bend_cap=BEND_CAP_SOLVE, follow=0.6)
    pose.update(solved)
    S.attach_helpers(pose, 'upperarm_r')
    hybrid_humerus = HA.roll_humerus(pose, 'r', hybrid_humerus)
    S.attach_helpers(pose, 'upperarm_r')
    HA.limit_bend(pose, 'r', BEND_CAP_FINAL)
    for n in HAND_TREE:
        par = c.parent[n]
        local = old[par].inverted() @ old[n]
        if n in FINGERS_R:
            local = mix_mat(local, p82[par].inverted() @ p82[n], w)
        pose[n] = pose[par] @ local
    roll = C.ROLL(min(t85, C.SPIN_END)) * c.roll_inplane_deg
    rot = old[WPN].to_quaternion() @ Quaternion((0.0, 0.0, 1.0), math.radians(-w * roll))
    contact, _ = S.free_weapon(pose, rot, t85)
    rel82 = (pose['hand_r'] @ (p82['hand_r'].inverted() @ p82[WPN])).translation
    pose[WPN] = Matrix.LocRotScale(contact.translation.lerp(rel82, w), rot, c.idle_scale[WPN])
    return pose


c.source_action.name = 'RETAINED_V4_Idle'
c.source_action.use_fake_user = True
action = c.source_action.copy()
action.name = CLIP
action.use_fake_user = True
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in list(bag.fcurves):
                bag.fcurves.remove(curve)

twist = {s: Hd.Twist(c.rest, s) for s in ('r', 'l')}
search_prev = 0.0
end_frame = int(round(END_C * FPS))
prev_q, rows = {}, []
t85_prev = 0.0
for frame in range(end_frame + 1):
    clip = frame / FPS
    t = PLAY(clip)  # design time: every R6 curve below is written on it
    t85 = t85_of(t)
    # R6b: per-frame rate limits are per 1/120 s of V85 motion (R4 values); a frame now covers a varying amount.
    k = max(0.25, (t85 - t85_prev) * 120.0) if frame else 1.0
    t85_prev = t85
    A.MAX_SWIVEL_STEP, A.MAX_HUMERUS_STEP, A.MAX_TRIM_STEP = math.radians(9.0) * k, 3.0 * k, 2.5 * k
    pose, row = solve(S, t85)
    w = w82(t)
    if '--diag' in sys.argv and T0 < t < T_SE:
        p82 = v82_pose(v82_time(phi_h(t)))
        qa, qb = pose['hand_r'].to_quaternion(), p82['hand_r'].to_quaternion()
        sa, sb = pose[WPN].to_quaternion(), p82[WPN].to_quaternion()
        rel_a = pose['hand_r'].inverted() @ pose[WPN]
        rel_b = p82['hand_r'].inverted() @ p82[WPN]
        row['diag'] = {'hand_deg': round(math.degrees(qa.rotation_difference(qb).angle), 1),
                       'hand_m': round((pose['hand_r'].translation - p82['hand_r'].translation).length, 3),
                       'sword_deg': round(math.degrees(sa.rotation_difference(sb).angle), 1),
                       'rel_deg': round(math.degrees(rel_a.to_quaternion().rotation_difference(rel_b.to_quaternion()).angle), 1),
                       'rel_m': round((rel_a.translation - rel_b.translation).length, 3),
                       'elbow_m': round((pose['lowerarm_r'].translation - p82['lowerarm_r'].translation).length, 3)}
    if t > V82_IN and not row.get('idle_hold'):
        pose = blend(pose, t, t85, w)
        twist['r'].apply(pose, c.idle_scale)
    else:
        # V85 alone: its solve already applied the twist; carry its continuity into the next hand-over.
        HA.prev_swivel = dict(getattr(S.arm, 'prev_swivel', {}))
        HA.prev_delta = dict(getattr(S.arm, 'prev_delta', {}))
        HA.prev_trim = dict(getattr(S.arm, 'prev_trim', {}))
        hybrid_humerus = S.humerus['r']
        twist['r'].prev = S.twist['r'].prev
        hand_q_prev = None
    hand_pts, _ = c.hand_skin.posed(pose)
    fore_pts, _ = c.fore_skin.posed(pose)
    if w > 1e-5:
        # The blended hilt sits between the two sources' contacts; clear it out of the hand and forearm along
        # the spin axis (fingertips already sit ~1 cm inside the accepted fist).
        pose[WPN], search_prev = c.field.search_axis(pose[WPN], np.vstack([hand_pts, fore_pts]), c.spin_axis,
                                                     allow=0.010, prev=search_prev, span=0.02)
    else:
        search_prev = 0.0
    row.update({'motion_s': row['seconds'], 'design_s': round(t, 4), 'seconds': round(clip, 4),
                'phi_h_deg': round(phi_h(t), 2),
                'w82': round(w, 3), 'hybrid_search_m': round(search_prev, 4),
                'clear_hand': c.field.report(pose[WPN], hand_pts), 'clear_forearm': c.field.report(pose[WPN], fore_pts)})
    world = {}
    for n in order:
        b = rig.pose.bones[n]
        b.rotation_mode = 'QUATERNION'
        pm = world.get(c.parent[n], Matrix.Identity(4))
        loc, q, sc = (c.local_rest[n].inverted() @ (pm.inverted() @ pose[n])).decompose()
        if n in prev_q and q.dot(prev_q[n]) < 0.0:
            q.negate()
        prev_q[n] = q.copy()
        b.location, b.rotation_quaternion, b.scale = loc, q, c.idle_local[n][2]
        world[n] = pm @ c.local_rest[n] @ Matrix.LocRotScale(loc, q, sc)
        for ch in ('location', 'rotation_quaternion', 'scale'):
            b.keyframe_insert(ch, frame=frame, group=n)
    rows.append(row)

for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
c.scene.render.fps, c.scene.render.fps_base = int(FPS), 1.0
c.scene.frame_start, c.scene.frame_end = 0, end_frame
c.scene.frame_set(0)
if '--no-export' not in sys.argv:
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(
        filepath=str(OUT / (CLIP + '.fbx')), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)

live = [r for r in rows if not r.get('idle_hold')]
free = [r for r in live if r['grip'] < 0.999 or r['w82'] > 0.0]
end_err = max((world[n].translation - c.idle[n].translation).length for n in ('hand_r', 'hand_l', 'WPN_root'))
report = {
    'revision': 'InspectReverseV85 R6 hybrid (V85 release + V82 open-palm spin + V85 back-of-hand regrip)',
    'variant': VARIANT, 'idle_source': str(c.source), 'v82_source': 'Work/v82_poses_%s.npz' % VARIANT,
    'seconds': round(END_C, 4), 'fps': FPS, 'spin_window_s': [round(clip_of(T0), 4), round(clip_of(T_SE), 4)],
    'cue_clip_s': {name: round(clip_of(d), 4) for name, d in
                   (('whip', 0.41 * C.TEMPO), ('land', 0.68), ('snap', 0.95), ('catch', T_SE))},
    'speed_scale': round(SCALE, 4), 'v82_phase_window_deg': [V82_IN, V82_FULL, V82_HOLD, V82_OUT],
    'max_hilt_in_hand_free_mm': max([r['clear_hand']['hilt_max_mm'] for r in free] or [0.0]),
    'max_guard_in_hand_mm': max(r['clear_hand']['guard_max_mm'] for r in live),
    'max_sword_in_forearm_mm': max(max(r['clear_forearm']['hilt_max_mm'], r['clear_forearm']['guard_max_mm']) for r in live),
    'max_wrist_trim_r_deg': max(r['wrist_trim_r_deg'] for r in live),
    'max_reach_clamp_m': max(r['reach_clamp_m'] for r in live),
    'hand_roll_v9_r_range_deg': [min(r['hand_roll_v9_r_deg'] for r in live), max(r['hand_roll_v9_r_deg'] for r in live)],
    'min_blade_in_view_depth_m': min([r['blade_in_view_min_depth_m'] for r in live
                                      if r['blade_in_view_min_depth_m'] is not None] or [None]),
    'keys': [dict(k, t=round(clip_of(time_h(float(k['phi'])) if k['phi'] > C.WINDUP[-1][1] else T0), 4))
             for k in C.KEYS],
    'end_translation_error_m': round(end_err, 6),
    'twist_rule': 'V9: lowerarm_twist_01 100 %, lowerarm_twist_02 50 % of hand roll vs lowerarm and bind',
    'testing': 'Authoring metrics only; no game or editor test. User tests.',
    'samples': rows,
}
(HERE / ('authoring_v85' + ('_long_grip' if VARIANT == 'LongGrip' else '') + '.json')).write_text(
    json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
if '--no-export' not in sys.argv:
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
else:
    (HERE / 'Work').mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'Work' / ('preview_%s.blend' % VARIANT)))
print('INSPECT_R6_AUTHORED', VARIANT, end_frame, {k: v for k, v in report.items() if k not in ('samples', 'keys')})
