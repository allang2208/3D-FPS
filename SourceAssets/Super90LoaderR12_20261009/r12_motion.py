"""R12 motion: Delta Force-style phases on the native Super90 clock.

exec() after r12_core.py. pose(f, count, empty, family) -> (bones, handle, tube).
Normal 7: release 0-18 / offscreen fetch / tube 74-87 / push 87-114 /
flick + tube drop 114-127 / open-palm regrip to 146. Empty adds the overhand
charging-handle pull, bolt forward at last + 48, end at last + 68.
"""

EMPTY_MODE = 'rack'  # Reference: left hand crosses OVER the receiver; right stays on the grip.

def kick(f, f0, period=8., decay=5.):
    """Damped impact response starting at f0 (0 before), peak about period/4 later."""
    x = f - f0
    return 0. if x < 0 else math.sin(2 * math.pi * x / period) * math.exp(-x / decay)

def settle(f, f0, f1, ov=.08):
    """Eased arrival with a small overshoot and settle (weight, not a linear blend)."""
    span = f1 - f0; u = (f - (f0 + .55 * span)) / (.45 * span)               # overshoot finishes at f1
    return phase(f, f0, f1) + (ov * math.sin(math.pi * u) if 0. < u < 1. else 0.)

def gun_angles(f, count, empty, lay=None):
    """R12: shoulder pivot and reference muzzle-up framing, then reverse cant."""
    lay = lay or LAYOUT; E = last_frame(count); D = duration(count, empty); DN = E + NORMAL_TAIL
    hold, dock = lay.get('roll_hold', 44.), lay.get('roll_dock', 66.)
    s0 = settle(f, 3, 26, .035)
    roll = hold * s0 + (dock - hold) * settle(f, 64, 85, .025)
    pitch = lay.get('pitch', 26.) * phase(f, 3, 28)
    yaw = lay.get('yaw', 0.) * phase(f, 4, 28)
    load = phase(f, 87, E) * (1 - phase(f, E, E + 5))
    roll += 1.0 * load + 1.4 * kick(f, 87, 7, 3.5) + 1.6 * kick(f, E, 8, 4)
    pitch += -.5 * load - .6 * kick(f, 87, 7, 3.5) - .9 * kick(f, E, 8, 4)
    if empty:
        # Reference frames 269-285: after shedding the loader, turn the right
        # receiver side up so the left hand can cross above it without underhooking.
        reverse = phase(f, E + 11, E + 29)
        roll = roll * (1 - reverse) + lay.get('empty_roll', -25.) * reverse
        pitch += lay.get('rack_pitch_add', 6.) * reverse
        yaw += lay.get('rack_yaw_add', 3.) * reverse
        recover = phase(f, E + 50, D - 3)
        roll *= 1 - recover; pitch *= 1 - recover; yaw *= 1 - recover
        pitch += -.7 * kick(f, E + 41, 6, 3) + .9 * kick(f, E + RELEASE_TAIL, 7, 3)
    else:
        recover = phase(f, E + 12, D - 2)
        roll *= 1 - recover; pitch *= 1 - recover; yaw *= 1 - recover
    end = 1 - phase(f, D - 3, D)
    return roll * end, pitch * end, yaw * end, s0 * (1 - recover), 0.

BUTT = BIND_TO_IDLE @ BUTT_BIND
def gun_move(f, count, empty, lay=None):
    """Stock stays in the shoulder pocket: pitch/yaw and the cant pivot on the butt pad;
    only a small butt slide (<= 3 cm, layout) is allowed."""
    lay = lay or LAYOUT
    roll, pitch, yaw, off, eoff = gun_angles(f, count, empty, lay)
    q = Quaternion(UP, math.radians(yaw)) @ Quaternion(RIGHT, math.radians(pitch)) @ Quaternion(barrel, math.radians(roll))
    slide = native_delta(lay.get('butt_slide_cam_cm', (0., 0., 0.))) * off
    return T(BUTT + slide) @ q.to_matrix().to_4x4() @ T(-BUTT)

def tube_world(f, count, empty, lay=None, move=None):
    lay = lay or LAYOUT
    move = move or gun_move(f, count, empty, lay)
    docked = move @ BIND_TO_IDLE @ tube_bind(lay)
    if f >= 87: return docked
    # Tube (with the hand on the post) rises into view from below-left once visible
    # (74), lines up, then is driven home: accelerating axial slam into the funnel at 85.
    lead_w = native_delta(tuple(lay.get('approach_cam_cm', (-3., -8., -24.)))) * (1 - phase(f, SHOW_BEGIN - 1, 82))
    u = max(0., min(1., (f - 77) / 10.)); slam = u * u
    back = lay.get('approach_back', .03) * (1 - slam) * (1 - .35 * phase(f, SHOW_BEGIN - 1, 77))
    tilt = Matrix.Rotation(math.radians(-6) * (1 - phase(f, SHOW_BEGIN - 1, 83)), 4, 'X')
    return T(lead_w) @ docked @ T(Vector((0, -back, 0))) @ tilt

def post_world(f, count, empty, lay=None, move=None, tube=None):
    E = last_frame(count)
    s = stroke_len(lay) * push_fraction(min(f, E))
    tube = tube or tube_world(f, count, empty, lay, move)
    return tube @ post_in_tube(s, lay)

def drop(tube, f, E):
    """Released tube and pusher fall under gravity (real seconds at 1.3x)."""
    t = max(0., (f - E - 2) / (60 * PLAY_RATE))
    if t <= 0: return tube
    away = native_delta((0., -1.0, -.35)).normalized()
    pos = tube.translation + away * (1.15 * t) - UP * (.55 * t + 4.905 * t * t) - tube.to_3x3().col[1].normalized() * (.35 * t)
    spin = Quaternion(tube.to_3x3().col[0].normalized(), -5.5 * t) @ Quaternion(FORWARD, 2.0 * t)
    return Matrix.LocRotScale(pos, spin @ tube.to_quaternion(), one)

def rel(move, m): return move.inverted() @ m

def left_fingers(f, count, empty, family, start_local):
    E = last_frame(count); DN = E + NORMAL_TAIL; out = {}
    for n in finger_names['l']:
        digit = n.split('_')[0]; k = DIGIT_ORDER[digit]
        local = mix(start_local[n], OPEN[n], phase(f, k * 1.2, 5 + k * 1.2))             # release the fore-end
        local = mix(local, POST_FINGERS.get(n, OPEN[n]), phase(f, 48 + k, 64 + k))         # close on the post offscreen
        if f > E:
            local = mix(local, SPLAY[n], phase(f, E + k * .8, E + 4 + k * .8))             # flick open, index first
            local = mix(local, OPEN[n], phase(f, E + 9, E + 15))
            if empty and EMPTY_MODE == 'rack':
                D = duration(count, True)
                local = mix(local, HOOK[n], phase(f, E + 28 + k * .35, E + 33 + k * .35) * (1 - phase(f, E + 44, E + 47)))
                local = mix(local, start_local[n], phase(f, D - 9 + k * .8, D - 2 + k * .5))
            else:
                local = mix(local, start_local[n], phase(f, DN - 9 + k * .8, DN - 2 + k * .5)) # palm first, then close
        out[n] = local
    return out

def left_hand_target(f, count, empty, family, move, post):
    E = last_frame(count); D = duration(count, empty)
    start = idles[family]
    support = move @ start['hand_l']
    held = post @ HAND_IN_POST
    if f <= E and f >= 72: return held
    if f <= E:
        # 0-6 loosen and clear the fore-end; 6-26 drop straight to the staging
        # grasp below the frame (where the tube will appear); small fetch loop;
        # 58-72 settle on the post that is already in the hand off screen.
        clear = support.copy(); clear.translation += native_delta((0., -3.0, -2.0)) * phase(f, 2, 9)
        # Staging = the docked grasp (gun-relative) lowered below the frame edge.
        dock_mv = gun_move(87, count, empty)
        stage_rel = rel(dock_mv, post_world(87, count, empty, move=dock_mv) @ HAND_IN_POST)
        staging = move @ stage_rel
        staging.translation += native_delta(tuple(LAYOUT.get('staging_cam_cm', (-1.0, -2.0, -5.0)))) * (1 - phase(f, 52, 74))
        loop = native_delta((-1.0, -1.5, -3.0)) * pulse(f, 32, 56)
        a = phase(f, 4, 33)
        pos = bezier(clear.translation, clear.translation + native_delta((-1., -3., -5.)),
                     staging.translation + native_delta((0., -2., 6.)), staging.translation, a) + loop
        # Fore-end grip -> post grip supinates (palm turns up/forward), never the long way round.
        rot = twist_slerp(clear.to_quaternion(), staging.to_quaternion(), clear.to_quaternion() @ PALM_AXIS['l'], phase(f, 8, 40), -1)
        h = Matrix.LocRotScale(pos, rot, one)
        return mix(h, held, phase(f, 58, 72))
    flick = _flick(f, count, empty, family, move)
    DN = E + NORMAL_TAIL                      # both branches regrip on the normal clock
    fl = flick_len(count)
    if empty and EMPTY_MODE == 'rack': return rack_target(f, count, family, move, flick)
    a = phase(f, E + fl, DN - 6)
    if a <= 0: return flick
    f0 = rel(gun_move(E + fl, count, empty), _flick(E + fl, count, empty, family))
    end = start['hand_l']
    p = bezier(f0.translation, f0.translation + native_delta((-1., -6., -6.)),
               end.translation + native_delta((-3., -6., -5.)), end.translation, a)
    # Open palm back to the fore-end grip pronates toward the family's idle hold.
    q = twist_slerp(f0.to_quaternion(), end.to_quaternion(), f0.to_quaternion() @ PALM_AXIS['l'], phase(f, E + fl, DN - 4), +1)
    gun_up = (BIND_TO_IDLE.to_3x3() @ Vector((0, 0, 1))).normalized()
    p = p + gun_up * .004 * kick(f, DN - 6, 8, 3) * (1 - phase(f, DN - 2, DN))   # palm lands on the fore-end
    return move @ Matrix.LocRotScale(p, q, one)

def flick_len(count):
    """The whole push is on screen, so every count gets a visible flick (short counts a bit shorter)."""
    return round(7 + 3 * (count - 1) / 6)

def _flick(f, count, empty, family, move=None):
    """Open-hand flick off the post: up-left (camera) with the wrist easing toward the regrip."""
    E = last_frame(count); move = move or gun_move(f, count, empty)
    rel_release = rel(gun_move(E, count, empty), post_world(E, count, empty)) @ HAND_IN_POST
    u = max(0., min(1., (f - E - 1) / max(1., flick_len(count) - 2))); a = 1 - (1 - u) ** 3     # snap off, then float
    reach = .7 + .3 * (count - 1) / 6
    pos = (move @ rel_release).translation + native_delta(tuple(LAYOUT.get('flick_cam_cm', (3., -10., 9.)))) * (a * reach)
    q0 = rel_release.to_quaternion(); q1 = idles[family]['hand_l'].to_quaternion()
    if q0.dot(q1) < 0: q1.negate()
    return Matrix.LocRotScale(pos, move.to_quaternion() @ q0.slerp(q1, .30 * a), one)

_rack_keys = {}
def rack_keys(family):
    """Gun-relative overhand keys. Right side up after reverse cant, palm faces
    inward, wrist behind the handle and fingers toward the muzzle. The reference
    reaches over the receiver but does not bend the wrist down from above it."""
    if family in _rack_keys: return _rack_keys[family]
    B3 = BIND_TO_IDLE.to_3x3()
    gx = (B3 @ Vector((1, 0, 0))).normalized(); gy = (B3 @ Vector((0, 1, 0))).normalized(); gz = (B3 @ Vector((0, 0, 1))).normalized()
    ih = idle['hand_l']; fing_h = (ih.inverted() @ idle['middle_01_l'].translation).normalized()
    across = (ih.inverted() @ idle['index_01_l'].translation - ih.inverted() @ idle['pinky_01_l'].translation).normalized()
    palm_h = fing_h.cross(across).normalized(); fing_h = (fing_h - palm_h * fing_h.dot(palm_h)).normalized()
    def orient(palm_w, fing_w):
        fing_w = (fing_w - palm_w * fing_w.dot(palm_w)).normalized()
        src = Matrix((palm_h, fing_h, palm_h.cross(fing_h).normalized())).transposed()
        dst = Matrix((palm_w, fing_w, palm_w.cross(fing_w).normalized())).transposed()
        return (dst @ src.inverted()).to_quaternion()
    # Reference: back of the hand is visible; forearm approaches from below-right,
    # fingers point upper-left. Solve that palm plane at the reversed gun pose,
    # then keep the contact orientation rigid in receiver space.
    rack_move = gun_move(last_frame(7) + 34, 7, True)
    q_world = orient(native_delta((-.9,-.2,0.)).normalized(), native_delta((.2,-.4,.9)).normalized())
    q = rack_move.to_quaternion().inverted() @ q_world
    tip = I.copy()
    for n in ('index_metacarpal_l', 'index_01_l', 'index_02_l'): tip = tip @ HOOK[n]
    handle = BIND_TO_IDLE @ HANDLE_OPEN_BIND
    hook = Matrix.LocRotScale(handle + gy * .013 + gx * .010 - (q @ tip.translation), q, one)
    above = hook.copy(); above.translation += gx * .025 + gz * .035 + gy * .010
    pulled = hook.copy(); pulled.translation += -gy * .024
    _rack_keys[family] = (above, hook, pulled)
    return _rack_keys[family]

def rack_target(f, count, family, move, flick):
    """Empty: flick -> left/top clearance -> cross the top -> hook/pull -> peel -> regrip."""
    E = last_frame(count); D = duration(count, True); fl = flick_len(count)
    above, hook, pulled = rack_keys(family)
    if f < E + fl: return flick
    f0 = rel(gun_move(E + fl, count, True), _flick(E + fl, count, True, family))
    def turn(a, b, t, sign):
        q = twist_slerp(a.to_quaternion(), b.to_quaternion(), a.to_quaternion() @ PALM_AXIS['l'], t, sign)
        return Matrix.LocRotScale(a.translation.lerp(b.translation, t), q, one)
    B3 = BIND_TO_IDLE.to_3x3()
    gx = (B3 @ Vector((1, 0, 0))).normalized(); gz = (B3 @ Vector((0, 0, 1))).normalized()
    crown = above.copy(); crown.translation = hook.translation - gx * .050 + gz * .065
    if f < E + 24:
        a = phase(f, E + fl, E + 24)
        g = turn(f0, crown, a, 0)
        g.translation = bezier(f0.translation, f0.translation + gz * .055 - gx * .025,
                               crown.translation - gx * .04, crown.translation, a)
    elif f < E + 30:
        g = mix(crown, above, phase(f, E + 24, E + 30))
    elif f < E + 33:
        g = mix(above, hook, phase(f, E + 30, E + 33))
    elif f < E + 44:
        u = max(0., min(1., (f - E - 33) / 9.)); g = mix(hook, pulled, u * u * (3 - 2 * u))   # brace, then yank
    elif f < E + 48:
        lift = pulled.copy(); lift.translation += gx * .025 + gz * .035
        g = mix(pulled, lift, phase(f, E + 44, E + 48))                                   # let the handle go
    else:
        lift = pulled.copy(); lift.translation += gx * .025 + gz * .035
        end = idles[family]['hand_l']; a = settle(f, E + 48, D - 5, .04)
        p = bezier(lift.translation, lift.translation + gz * .07 - gx * .07,
                   end.translation + gz * .045 - gx * .055, end.translation, min(1., a))
        # Back to the fore-end grip pronates toward the family's idle hold.
        q = twist_slerp(lift.to_quaternion(), end.to_quaternion(), lift.to_quaternion() @ PALM_AXIS['l'], phase(f, E + 48, D - 4), +1)
        gun_up = (BIND_TO_IDLE.to_3x3() @ Vector((0, 0, 1))).normalized()
        g = Matrix.LocRotScale(p + gun_up * .004 * kick(f, D - 7, 8, 3) * (1 - phase(f, D - 2, D)), q, one)
    if f < E + 33:
        q = twist_slerp(f0.to_quaternion(), hook.to_quaternion(), f0.to_quaternion() @ PALM_AXIS['l'], phase(f, E + fl, E + 30), 0)
        g = Matrix.LocRotScale(g.translation, q, one)
    return move @ g

def right_index_press(f, count, start_local):
    """Empty only: right trigger finger extends to the bolt release (right side,
    ahead of the trigger guard), presses, and returns along the frame."""
    E = last_frame(count); out = dict(start_local)
    reach = phase(f, E + 32, E + 43) * (1 - phase(f, E + 52, E + 62))
    press = pulse(f, E + 44, E + 49)
    for n, amt, extra in (('index_01_r', .62, 6.), ('index_02_r', .55, 4.), ('index_03_r', .40, 2.)):
        pp, qq, ss = start_local[n].decompose(); rq = local_rest[n].to_quaternion()
        if qq.dot(rq) < 0: rq.negate()
        q = qq.slerp(rq, amt * reach)
        q = q @ Quaternion(Vector((0, 0, 1)), math.radians(extra) * press)
        out[n] = Matrix.LocRotScale(pp, q, ss)
    return out

def pose_sample(f, count, empty, family='base'):
    E = last_frame(count); D = duration(count, empty)
    start = idles[family]
    move = gun_move(f, count, empty)
    p = copy(start)
    for n in names:
        if n.startswith('WPN_'): p[n] = move @ idle[n]
    gun = p['WPN_root']
    opened = 0.
    if empty:
        # Bolt held back until released; slams home at last + 48 (overhand: yanked a
        # little further back by the handle first).
        opened = 1. - phase(f, E + RELEASE_TAIL - 1.5, E + RELEASE_TAIL)
        if EMPTY_MODE == 'rack': opened += (.024 / BOLT_OPEN) * phase(f, E + 33, E + 42) * (1 - phase(f, E + 45, E + 46))
        opened += .025 * pulse(f, E + RELEASE_TAIL, E + RELEASE_TAIL + 5)
    p['WPN_bolt'] = gun @ T((0, 0, BOLT_OPEN * opened)) @ GI @ idle['WPN_bolt']
    gate = phase(f, 82, 87) * (1 - phase(f, E + 2, E + 7))
    p['WPN_Load'] = p['WPN_Load'] @ Matrix.Rotation(math.radians(16) * gate, 4, 'X')
    tube = tube_world(f, count, empty, move=move)
    post = post_world(f, count, empty, move=move, tube=tube)
    if f > E + 2:
        # Once released, freeze the departure frame in world space; reversing the
        # shouldered gun must not drag the discarded loader back around with it.
        seated = tube_world(E + 2, count, empty)
        tube = drop(seated, f, E)
        s = stroke_len() * push_fraction(E); post = tube @ post_in_tube(s)
    hand = left_hand_target(f, count, empty, family, move, post_world(min(f, E), count, empty) if f <= E else post)
    # Elbow follows the natural forearm line for the post grip while it is held;
    # outside the hold it relaxes toward the idle wrist relation.
    hold_w = phase(f, 16, 46) * (1 - phase(f, E + 2, E + NORMAL_TAIL - 10))
    nat_post = hand.to_quaternion() @ POST_FOREARM_AXIS; nat_idle = hand.to_quaternion() @ PALM_AXIS['l']
    nat = (nat_post * hold_w + nat_idle * (1 - hold_w)).normalized()
    relax = phase(f, 1, 8) * (1 - phase(f, D - 8, D))
    # Lower/retract the left shoulder root while the hand is off screen so the
    # upper-arm end leaves the frame (Delta Force: arm fully out during the cant).
    # Released before the tube and hand come into view (whole push is on screen).
    shoulder_w = phase(f, 6, 24) * (1 - phase(f, 54, 72))
    src = copy(start)
    shift = native_delta(tuple(LAYOUT.get('shoulder_drop_cm', (-5., -3., -9.)))) * shoulder_w
    if empty:
        # Scapula protracts with the cross-body overhand reach, then returns before
        # the fore-end contact. This is authored shoulder movement, not limb scale
        # or the solver's emergency reach clamp.
        shoulder_reach = phase(f, E + 10, E + 27) * (1 - phase(f, E + 46, D - 6))
        shift += native_delta((1., 2., -3.)) * shoulder_reach
    # Shoulder drives the push: the root leans along the stroke and peaks on the seat.
    if f > 86:
        drive = .016 * phase(f, 87, 100) * (1 - phase(f, E + 2, E + 12)) + .006 * kick(f, E, 10, 4)
        shift = shift + tube_world(min(f, E), count, empty).to_3x3().col[1].normalized() * drive
    if shift.length > 1e-7:
        for n in names:
            if n.endswith('_l') and n not in ('ik_hand_l',): src[n] = T(shift) @ src[n]
    DN = E + (EMPTY_TAIL if empty and EMPTY_MODE == 'rack' else NORMAL_TAIL)
    hint = max(hold_w, .55 * phase(f, 4, 16) * (1 - phase(f, DN - 12, DN)))
    relax = phase(f, 1, 8) * (1 - phase(f, DN - 8, DN))
    stats = arm(p, src, hand, 'l', continuous=True, natural_axis=nat, relax=relax,
                hint_weight=LAYOUT.get('pole_weight', 1.) * hint, home=phase(f, D - 16, D - 2))
    for n in names:
        # Clavicle stays where the solver left it; nothing else in the left chain lags behind.
        if n.endswith('_l') and parents.get(n) == 'clavicle_l' and n != 'upperarm_l': p[n] = p['clavicle_l'] @ (start['clavicle_l'].inverted() @ start[n])
    start_local = {n: finger_local(start, n) for n in finger_names['l']}
    for n, local in left_fingers(f, count, empty, family, start_local).items():
        p[n] = p[parents[n]] @ local
    # Right hand stays on the grip; the elbow opens to keep the wrist near its idle relation.
    rh = move @ start['hand_r']
    right = arm(p, start, rh, 'r', continuous=True, natural_axis=rh.to_quaternion() @ PALM_AXIS['r'],
                hint_weight=.85 * phase(f, 2, 28) * (1 - phase(f, D - 22, D - 1)), relax=relax,
                home=phase(f, D - 16, D - 2))
    right_local = {n: finger_local(start, n) for n in finger_names['r']}
    if empty and EMPTY_MODE == 'press': right_local = right_index_press(f, count, right_local)
    for n in finger_names['r']: p[n] = p[parents[n]] @ right_local[n]
    parked = phase(f, E + HIDE_TAIL, D)
    p['WPN_Shell'] = mix(tube, move @ idle['WPN_Shell'], parked)
    p[PLUNGER_DRIVER] = mix(post, move @ idle[PLUNGER_DRIVER], parked)
    p['_stats'] = {'left': stats, 'right': right}
    return p, post, tube

pose_cache = {}
def pose(f, count, empty, family='base'):
    key = (count, empty, family)
    if key not in pose_cache:
        twist_context.clear(); pole_context.clear(); rows = []
        for frame in range(duration(count, empty) + 1):
            rows.append(pose_sample(frame, count, empty, family))
        pose_cache[key] = rows
    rows = pose_cache[key]; f = int(max(0, min(len(rows) - 1, round(f))))
    return rows[f]

def cycle_pose(f, family='base'):
    """Chamber-only continuation: idle -> empty bolt branch (no loader)."""
    at = last_frame(1) + CYCLE_START_TAIL + f * (EMPTY_TAIL - CYCLE_START_TAIL) / CYCLE_FRAMES
    target = pose(at, 1, True, family)[0]
    if f >= 12: return target
    t = phase(f, 0, 12); start = idles[family]; p = {}
    for n in names:
        par = parents[n]
        a = start[par].inverted() @ start[n] if par else start[n]
        b = target[par].inverted() @ target[n] if par else target[n]
        p[n] = p.get(par, I) @ mix(a, b, t)
    goal = mix(start['hand_l'], target['hand_l'], t)
    goal.translation += native_delta((0., -6., -3.)) * math.sin(math.pi * t)
    support = copy(p)
    repair = phase(f, 0, 5) * (1-phase(f, 9, 12))
    arm(p, support, goal, 'l', continuous=True, relax=repair)
    for n in finger_names['l']:
        p[n] = p[parents[n]] @ mix(finger_local(start, n), finger_local(target, n), phase(f, 3, 12))
    arm(p, support, p['WPN_root'] @ GI @ start['hand_r'], 'r', relax=repair)
    for n in finger_names['r']: p[n] = p[parents[n]] @ finger_local(start, n)
    return p
