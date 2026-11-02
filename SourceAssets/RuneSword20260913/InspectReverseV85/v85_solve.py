"""Per-frame V85 pose (rig-space matrices for every bone) plus the authoring report row (from V84)."""
import math

import numpy as np
from mathutils import Matrix, Quaternion, Vector

import v85_keys as C
import v85_hand as Hd
from v85_frame import (BEND_CAP_FINAL, BEND_CAP_SOLVE, DOWNSTROKE_DEG, ELBOW_GIVE_R, mix_mat)
from v85_setup import UP, WPN


TANV = math.tan(math.radians(75.0 / 2.0))


def downstroke_weight(t):
    # V82: elbow-led forward tilt before the turn (now the counter-move of a clockwise turn).
    load = C.smoothstep((t - 0.245) / 0.105)
    release = C.smoothstep((t - 0.398) / 0.07)
    return load * (1.0 - release)


def solve(S, t):
    c = S.c
    idle, scale = c.idle, c.idle_scale
    phi = C.phi_at(t)
    tt = min(t, C.SPIN_END)
    turn_h = C.HAND_TURN(tt)
    grip = C.GRIP(tt) if t < C.SPIN_END else 1.0
    recover = C.smoothstep((t - C.SPIN_END) / (C.RECOVER_END - C.SPIN_END)) if t > C.SPIN_END else 0.0
    keep = 1.0 - recover
    out, lift, forward = C.OUT(tt) * keep, C.LIFT(tt) * keep, C.FWD(tt) * keep
    fw = C.smoothstep((t - 0.30) / 0.10) * keep
    offset = (UP * lift + c.fwd_dir * forward + c.right_dir * (out + C.RIGHT(tt) * keep)
              + Vector((0.0, C.DEPTH(tt) * keep, 0.0)))
    flat = Quaternion().slerp(c.flatten_q, fw)
    sword_rot = Quaternion(c.spin_axis, math.radians(phi)) @ flat @ idle[WPN].to_quaternion()
    roll = C.ROLL(tt) * c.roll_inplane_deg
    if abs(roll) > 1e-6:
        sword_rot = sword_rot @ Quaternion((0.0, 0.0, 1.0), math.radians(roll))

    # The hand keeps its own keyed path throughout (it equals the held hand at both ends, where turn == phi
    # mod 360 and the hand-local terms are zero); the grip weight only decides where the sword sits.
    turn = Quaternion(c.spin_axis, math.radians(turn_h)) @ flat
    sup, ext = C.SUPINATE(tt) * keep, C.EXTEND(tt) * keep
    # The palm/back flip of the reference turns the hand about the FOREARM axis (true pronation), so the wrist
    # bend does not change; a roll about the hand's own finger axis bent the wrist 70-100 deg into the cap.
    fore_local = idle['hand_r'].to_quaternion().inverted() @ (
        idle['hand_r'].translation - idle['lowerarm_r'].translation).normalized()
    local = Quaternion(fore_local, math.radians(sup)) @ Quaternion((0.0, 0.0, 1.0), math.radians(ext))
    pivot = c.contact_sword + offset
    hand_r = Matrix.LocRotScale(pivot + turn @ (idle['hand_r'].translation - c.contact_sword),
                                turn @ idle['hand_r'].to_quaternion() @ local, scale['hand_r'])
    if recover > 0.0:
        hand_r = Matrix.LocRotScale(hand_r.translation,
                                    mix_mat(hand_r, idle['hand_r'], recover).to_quaternion(), scale['hand_r'])
        sword_rot = sword_rot.slerp(idle[WPN].to_quaternion(), recover)
    sword_rot = S.lift_tip(sword_rot, hand_r @ c.contact_hand_local)

    left_path, left_open = C.LEFT_PATH(tt), C.LEFT_OPEN(tt)
    if t >= C.SPIN_END:
        left_path = 1.0 - C.smoothstep((t - C.LEFT_APPROACH_START) / (C.LEFT_PALM_CONTACT - C.LEFT_APPROACH_START))
        left_open = 1.0
    l_off = Vector(C.LEFT_PARK) * left_path + Vector(C.LEFT_BULGE) * (4.0 * left_path * (1.0 - left_path)) \
        + c.right_dir * out
    hand_l = Matrix.LocRotScale(idle['hand_l'].translation + l_off, idle['hand_l'].to_quaternion(), scale['hand_l'])
    shoulder_l = idle['upperarm_l'].translation + Vector(C.LEFT_SHOULDER) * left_path

    pose = {n: idle[n].copy() for n in c.names}
    row = {'seconds': round(t, 4), 'phi_deg': round(phi, 2), 'hand_turn_deg': round(turn_h, 2), 'supinate': round(sup, 1),
           'grip': round(grip, 3), 'recover': round(recover, 3)}
    idle_hold = recover >= 1.0 - 1e-4 or (t <= 0.06 + 1e-6)
    if idle_hold:
        # Exact idle, except the forearm twist bones also follow the V9 rule here (the installed idle does).
        S.humerus['r'] = 0.0
        S.twist['r'].prev = S.twist['l'].prev = None
        S.twist['r'].apply(pose, scale)
        S.twist['l'].apply(pose, scale)
        row.update(idle_hold=True)
        return pose, row

    follow = 0.6 * fw
    solved_r, clamp_r = S.arm.solve(hand_r, 'r', give=ELBOW_GIVE_R, bend_cap=BEND_CAP_SOLVE, follow=follow)
    solved_l, clamp_l = S.arm.solve(hand_l, 'l', shoulder_l, give=0.055, bend_cap=180.0, follow=0.0)
    pose.update(solved_r)
    pose.update(solved_l)
    pose['hand_l'] = pose['lowerarm_l'] @ idle['lowerarm_l'].inverted() @ idle['hand_l']
    for side in ('r', 'l'):
        S.attach_helpers(pose, 'upperarm_' + side)
    S.humerus['r'] = S.arm.roll_humerus(pose, 'r', S.humerus['r']) if fw > 1e-4 else 0.0
    S.attach_helpers(pose, 'upperarm_r')
    trim = S.arm.limit_bend(pose, 'r', BEND_CAP_FINAL)

    def from_hand(rot, hand):
        return S.weapon_at(rot, hand @ c.contact_hand_local)

    pose[WPN] = from_hand(sword_rot, pose['hand_r'])
    S.arm.group_impulse(pose, DOWNSTROKE_DEG * downstroke_weight(t), Vector((1.0, 0.0, 0.0)), Vector(), from_hand)
    follow_deg = C.FOLLOW(t) if t >= C.SPIN_END else 0.0
    S.arm.group_impulse(pose, follow_deg, c.spin_axis,
                        Vector((0.0, 0.0, -C.FOLLOW_DROP_M * follow_deg / C.FOLLOW_PEAK_DEG)), from_hand)
    roll_r = S.twist['r'].apply(pose, scale)
    roll_l = S.twist['l'].apply(pose, scale)
    S.right_fingers(pose, t)
    S.left_fingers(pose, t, left_open)

    held = pose['hand_r'] @ c.grip_r.inverted()
    weights = {}
    residual = 0.0
    hand_pts, _ = c.hand_skin.posed(pose)
    fore_pts, _ = c.fore_skin.posed(pose)
    if grip < 0.999:
        free, weights = S.free_weapon(pose, pose[WPN].to_quaternion(), t)
        # Clear the real sword mesh (hilt and guard) out of the open hand and the forearm it hangs beside;
        # fingertips already sit ~1 cm inside the accepted fist, so the closing hook keeps that allowance.
        clear_pts = np.vstack([hand_pts, fore_pts])
        hook = min(1.0, max(0.0, 1.0 - grip) * C.CONTACT['palm'](tt))
        allow = 0.004 + 0.010 * hook
        free, search_s = c.field.search_axis(free, clear_pts, c.spin_axis, allow=allow, prev=S.search_prev,
                                                span=0.02)
        S.search_prev = search_s
        residual = max([d for d, _, _ in c.field.depths(free, clear_pts)] + [0.0])
        row['search_m'] = round(search_s, 4)
        # The turn always comes from the sword clock; the grip only pulls the hilt's position into the fist.
        # (Blending the hand-relative rotation in made the blade follow the hand's opposite turn for two
        # frames at the release — a visible back-step before the whip.)
        pose[WPN] = Matrix.LocRotScale(free.translation.lerp(held.translation, grip), free.to_quaternion(),
                                       c.idle_scale[WPN])
    else:
        pose[WPN] = held
        S.search_prev = 0.0
    clear_hand = c.field.report(pose[WPN], hand_pts)
    clear_fore = c.field.report(pose[WPN], fore_pts)

    # Left palm onto the final held sword (V82 two-hand handoff).
    attach = C.smoothstep((t - C.LEFT_ATTACH_START) / (C.LEFT_PALM_CONTACT - C.LEFT_ATTACH_START))
    if attach > 0.0:
        # R4: start from the requested (unclamped) left target — the solved hand already sat a soft-reach clamp
        # short of it, and clamping it a second time jumped the left hand ~5 mm on the first attach frame.
        start_l = Matrix.LocRotScale(hand_l.translation, pose['hand_l'].to_quaternion(), scale['hand_l'])
        target_l = mix_mat(start_l, pose[WPN] @ c.grip_l, attach)
        solved_l, clamp_l = S.arm.solve(target_l, 'l', shoulder_l, give=0.055, bend_cap=180.0, follow=attach,
                                       key='l_attach')
        pose.update(solved_l)
        S.attach_helpers(pose, 'upperarm_l')
        roll_l = S.twist['l'].apply(pose, scale)
        S.left_fingers(pose, t, left_open)

    mesh_now = pose[WPN] @ c.rest[WPN].inverted()
    # Nearest in-view depth of the blade line (guard to tip): what the lens could clip.
    in_view = []
    for k in range(9):
        p = pose[WPN] @ Vector((0.0, 0.0, 0.05 + 0.095 * k))
        if p.y > 0.0 and abs(p.x / (p.y * TANV * 16 / 9)) <= 1.05 and abs(p.z / (p.y * TANV)) <= 1.05:
            in_view.append(p.y)
    row['blade_in_view_min_depth_m'] = round(min(in_view), 4) if in_view else None
    # Which side of the hand the lens sees: +1 = back of the hand faces the camera, -1 = palm faces it.
    hp = pose['hand_r'].translation
    back = pose['hand_r'].to_quaternion() @ Vector((0.0, 1.0, 0.0))
    fingers = pose['hand_r'].to_quaternion() @ Vector((-1.0, 0.0, 0.0))
    row['dorsum_to_camera'] = round(back.dot(-hp.normalized()), 3)
    # Hilt axis relative to the palm centre (middle_01 root) along the back-of-hand normal: < 0 = palm side.
    palm_c = 0.5 * (pose['middle_01_r'].translation + hp)
    wpn_inv = pose[WPN].inverted()
    lz = (wpn_inv @ palm_c).z
    foot = pose[WPN] @ Vector((0.0, 0.0, lz))
    row['hilt_side_m'] = round((foot - palm_c).dot(back), 4)
    row['hilt_to_camera_m'] = round(-(foot - palm_c).dot(hp.normalized()), 4)
    row['fingers_screen_deg'] = round(math.degrees(math.atan2(fingers.z, fingers.x)), 1)
    row.update({
        'idle_hold': False, 'tip_depth_m': round((mesh_now @ c.tip_bind).y, 4),
        'tip_ndc_x_over_depth': round((mesh_now @ c.tip_bind).x / max(1e-4, (mesh_now @ c.tip_bind).y), 2),
        'pommel_depth_m': round((mesh_now @ c.pommel_bind).y, 4),
        'wrist_bend_r_deg': round(S.arm.wrist_bend(pose, 'r'), 2), 'wrist_trim_r_deg': round(trim, 2),
        'elbow_axial_r_deg': round(S.arm.elbow_gap(pose, 'r'), 2), 'humerus_roll_r_deg': S.humerus['r'],
        'hand_roll_v9_r_deg': round(roll_r, 2), 'hand_roll_v9_l_deg': round(roll_l, 2),
        'reach_clamp_m': round(max(clamp_r, clamp_l), 4),
        'contact_weights': {k: round(v, 3) for k, v in weights.items()},
        'push_residual_mm': round(residual * 1000.0, 2), 'clear_hand': clear_hand, 'clear_forearm': clear_fore,
        'hand_r': [round(v, 4) for v in pose['hand_r'].translation],
        'elbow_r': [round(v, 4) for v in pose['lowerarm_r'].translation],
        'shoulder_r_delta_m': round((pose['upperarm_r'].translation - idle['upperarm_r'].translation).length, 4),
    })
    return pose, row
