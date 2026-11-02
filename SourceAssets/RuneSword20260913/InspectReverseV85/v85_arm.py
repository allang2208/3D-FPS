"""Right/left arm support for V84 (from the V82 solver), parameterised by the rig context.

Hand first: the target hand pose is kept and the forearm, elbow and humeral roll are chosen to carry it.
The wrist limit only trims what the arm cannot reach, inside an explicit anatomical box.
"""
import math

from v85_keys import TEMPO  # R5: limits are per motion-time 1/120 s; the slowed clip has TEMPO frames per step

MAX_TRIM_STEP = 2.5 / TEMPO  # deg per 1/120 s of wrist-cap trim (R4)
MAX_SWIVEL_STEP = math.radians(9.0) / TEMPO  # per 1/120 s (4 deg starved the palm-to-back flip: 60-70 deg wrist trims)
MAX_HUMERUS_STEP = 3.0 / TEMPO  # deg per 1/120 s

from mathutils import Matrix, Quaternion, Vector


class Arm:
    def __init__(self, rest, idle, idle_scale):
        self.rest, self.idle, self.scale = rest, idle, idle_scale

    # ---- metrics -------------------------------------------------------------------------------------------
    def wrist_bend(self, pose, side):
        lo, hand = 'lowerarm_' + side, 'hand_' + side
        fd = (pose[hand].translation - pose[lo].translation).normalized()
        rd = (self.rest[hand].translation - self.rest[lo].translation).normalized()
        ha = pose[hand].to_quaternion() @ self.rest[hand].to_quaternion().inverted() @ rd
        return math.degrees(fd.angle(ha.normalized())) if ha.length > 1e-6 else 0.0

    def elbow_gap(self, pose, side):
        up, lo, hand = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
        axis = (pose[hand].translation - pose[lo].translation).normalized()
        rest_fore = (self.rest[hand].translation - self.rest[lo].translation).normalized()
        up_delta = pose[up].to_quaternion() @ self.rest[up].to_quaternion().inverted()
        fore_delta = pose[lo].to_quaternion() @ self.rest[lo].to_quaternion().inverted()
        no_roll = (up_delta @ rest_fore).rotation_difference(axis) @ up_delta
        rel = fore_delta @ no_roll.inverted()
        ang = 2.0 * math.atan2(Vector((rel.x, rel.y, rel.z)).dot(axis), rel.w)
        return math.degrees((ang + math.pi) % (2.0 * math.pi) - math.pi)

    # ---- IK --------------------------------------------------------------------------------------------------
    @staticmethod
    def fit_elbow(shoulder, target, upper, fore, hint):
        axis = target - shoulder
        reach = axis.length
        limit = upper + fore - 1e-4
        clamped = 0.0
        if reach > limit:
            clamped = reach - limit
            target = shoulder + axis.normalized() * limit
            axis, reach = target - shoulder, limit
        d = axis.normalized()
        pole = hint - shoulder
        pole = pole - d * pole.dot(d)
        if pole.length < 1e-5:
            pole = Vector((0.0, -1.0, 0.0)) - d * d.y * -1.0
        pole.normalize()
        ca = max(-1.0, min(1.0, (upper * upper + reach * reach - fore * fore) / (2.0 * upper * reach)))
        a = math.acos(ca)
        return shoulder + (d * math.cos(a) + pole * math.sin(a)) * upper, clamped

    def solve(self, hand_world, side, shoulder=None, give=0.22, bend_cap=30.0, follow=0.6, key=None):
        """Elbow from the hand's own forearm direction (moved up to `give` off the plain IK elbow);
        the forearm carries the swing only, so the hand's roll stays between lowerarm and hand (V9 rule)."""
        up, lo, hand = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
        I = self.idle
        s0 = I[up].translation.copy() if shoulder is None else shoulder.copy()
        upper = (I[lo].translation - I[up].translation).length
        fore = (I[hand].translation - I[lo].translation).length
        target = hand_world.translation.copy()
        # Soft reach: never snap straight (the parked left arm hit full extension and the elbow then popped
        # out 3.6 cm in a frame as it bent again). Beyond 96 % of the arm the hand eases short of the target.
        limit = upper + fore
        reach = (target - s0).length
        soft = 0.96 * limit
        clamped = 0.0
        if reach > soft:
            eff = soft + (limit - soft) * (1.0 - math.exp(-(reach - soft) / (limit - soft))) - 1e-4
            clamped = reach - eff
            target = s0 + (target - s0).normalized() * eff
        old_fore = (I[hand].translation - I[lo].translation).normalized()
        planted, _ = self.fit_elbow(s0, target, upper, fore, I[lo].translation)
        aimed = hand_world.to_quaternion() @ I[hand].to_quaternion().inverted() @ old_fore
        ideal = target - aimed.normalized() * fore

        def assemble(elbow):
            axis = (target - elbow).normalized()
            upper_axis = (elbow - s0).normalized()
            old_upper = (I[lo].translation - I[up].translation).normalized()
            pose = {
                up: Matrix.LocRotScale(s0, old_upper.rotation_difference(upper_axis) @ I[up].to_quaternion(), self.scale[up]),
                lo: Matrix.LocRotScale(elbow, old_fore.rotation_difference(axis) @ I[lo].to_quaternion(), self.scale[lo]),
                hand: Matrix.LocRotScale(target, hand_world.to_quaternion(), self.scale[hand]),
            }
            return pose

        # Swivel the elbow about the shoulder-wrist axis from the plain IK elbow toward the hand's own forearm
        # direction. Interpolating the swivel ANGLE keeps it continuous (R9/R10 lerped hint points, which
        # flipped the pole near the axis and jumped the elbow 5-7 cm in a frame). `give` caps the swing.
        d = (target - s0).normalized()
        ref = Vector((0.0, 0.0, -1.0)) - d * (-d.z)
        if ref.length < 1e-4:
            ref = Vector((1.0, 0.0, 0.0)) - d * d.x
        u = ref.normalized()
        v = d.cross(u)
        centre = s0 + d * (planted - s0).dot(d)
        radius = (planted - centre).length

        def angle_of(p):
            q = p - s0 - d * (p - s0).dot(d)
            return math.atan2(q.dot(v), q.dot(u)), q.length

        a_p, _ = angle_of(planted)
        a_i, r_i = angle_of(ideal)
        delta = (a_i - a_p + math.pi) % (2.0 * math.pi) - math.pi
        key = key or side
        prev = getattr(self, 'prev_delta', {}).get(key)
        if prev is not None:  # stay on the previous frame's branch near +-180
            delta += 2.0 * math.pi * round((prev - delta) / (2.0 * math.pi))
        self.prev_delta = dict(getattr(self, 'prev_delta', {}), **{key: delta})
        reliable = max(0.0, min(1.0, r_i / 0.05))
        max_swing = give / max(radius, 1e-3)
        delta = max(-max_swing, min(max_swing, delta)) * reliable

        last = getattr(self, 'prev_swivel', {}).get(key)

        def angle_at(t):
            a = a_p + delta * t
            if last is not None:  # V85: the elbow may not whip faster than MAX_SWIVEL_STEP per frame
                step = (a - last + math.pi) % (2.0 * math.pi) - math.pi
                a = last + max(-MAX_SWIVEL_STEP, min(MAX_SWIVEL_STEP, step))
            return a

        def at(t):
            a = angle_at(t)
            return assemble(centre + (u * math.cos(a) + v * math.sin(a)) * radius)

        best = at(follow)
        bend = self.wrist_bend(best, side)
        x = max(0.0, min(1.0, (bend - (bend_cap - 10.0)) / 20.0))
        t = follow + (1.0 - follow) * x * x * (3.0 - 2.0 * x)
        if t > follow + 1e-6:
            best = at(t)
        self.prev_swivel = dict(getattr(self, 'prev_swivel', {}), **{key: angle_at(t)})
        self.last = {'side': side, 'a_p': math.degrees(a_p), 'a_i': math.degrees(a_i), 'r_i': r_i,
                     'delta': math.degrees(delta), 'bend_follow': bend, 't': t, 'radius': radius}
        return best, clamped

    def roll_humerus(self, pose, side, previous):
        """Turn the upper arm about its own axis so the elbow keeps its idle axial relation (V82 roll_shoulder,
        measured against idle so the idle frame needs no turn)."""
        up, lo = 'upperarm_' + side, 'lowerarm_' + side
        axis = (pose[lo].translation - pose[up].translation).normalized()
        ref = self.elbow_gap(self.idle, side)

        def metric(deg):
            trial = dict(pose)
            trial[up] = Matrix.LocRotScale(pose[up].translation,
                                           Quaternion(axis, math.radians(deg)) @ pose[up].to_quaternion(), self.scale[up])
            return abs(self.elbow_gap(trial, side) - ref)

        samples = [(metric(d), d) for d in range(-95, 96, 5)]
        best = min(v for v, _ in samples)
        cand = [d for v, d in samples if v <= best + 1.0]
        coarse = min(cand, key=lambda d: abs(d) if previous is None else abs(d - previous))
        # V82 stopped at the 5 deg grid, which steps the upper arm frame to frame; refine to 0.25 deg.
        fine = [(metric(coarse + 0.25 * k), coarse + 0.25 * k) for k in range(-20, 21)]
        best = min(v for v, _ in fine)
        cand = [d for v, d in fine if v <= best + 0.25]
        chosen = min(cand, key=lambda d: abs(d) if previous is None else abs(d - previous))
        if previous is not None:
            chosen = previous + max(-MAX_HUMERUS_STEP, min(MAX_HUMERUS_STEP, chosen - previous))
        pose[up] = Matrix.LocRotScale(pose[up].translation,
                                      Quaternion(axis, math.radians(chosen)) @ pose[up].to_quaternion(), self.scale[up])
        return chosen

    def limit_bend(self, pose, side, cap):
        """Trim the hand toward the forearm only beyond `cap` (position kept). R4: the trim may change by at most
        MAX_TRIM_STEP per frame — the arm still swinging under a hand that has stopped on its key swung the bend
        8 deg a frame, and a trim that followed it exactly popped the hand (and fingers, twist bones) 8 deg."""
        hand, lo = 'hand_' + side, 'lowerarm_' + side
        prev_all = getattr(self, 'prev_trim', {})
        prev = prev_all.get(side, 0.0)
        keep = pose[hand].translation.copy()
        cur = pose[hand].to_quaternion()
        locked = (pose[lo] @ self.idle[lo].inverted() @ self.idle[hand]).to_quaternion()
        if cur.dot(locked) < 0.0:
            locked.negate()
        full = math.degrees(cur.rotation_difference(locked).angle)
        want, best = 0.0, cur
        if self.wrist_bend(pose, side) > cap:
            lo_t, hi_t, best = 0.0, 1.0, locked
            for _ in range(16):
                mid = 0.5 * (lo_t + hi_t)
                q = cur.slerp(locked, mid)
                pose[hand] = Matrix.LocRotScale(keep, q, self.scale[hand])
                if self.wrist_bend(pose, side) <= cap:
                    best, hi_t = q, mid
                else:
                    lo_t = mid
            want = math.degrees(cur.rotation_difference(best).angle)
        got = max(0.0, min(full, prev + max(-MAX_TRIM_STEP, min(MAX_TRIM_STEP, want - prev))))
        if abs(got - want) > 1e-6:
            best = cur.slerp(locked, got / full) if full > 1e-6 else cur
        self.prev_trim = dict(prev_all, **{side: got})
        pose[hand] = Matrix.LocRotScale(keep, best, self.scale[hand])
        return got

    def group_impulse(self, pose, degrees, axis, displacement, weapon_from_hand):
        """Rotate forearm, hand and sword together about the wrist (V82 support_right_impulse)."""
        if abs(degrees) <= 1e-7 and displacement.length <= 1e-7:
            return
        U, L, H = 'upperarm_r', 'lowerarm_r', 'hand_r'
        a, e, h = (pose[n].translation.copy() for n in (U, L, H))
        upper = (e - a).length
        q = Quaternion(axis, math.radians(degrees))
        elbow = h + q @ (e - h) + displacement
        h = h + displacement
        shoulder = elbow - (elbow - a).normalized() * upper
        turn = (e - a).normalized().rotation_difference((elbow - shoulder).normalized())
        pose[U] = Matrix.LocRotScale(shoulder, turn @ pose[U].to_quaternion(), self.scale[U])
        pose[L] = Matrix.LocRotScale(elbow, q @ pose[L].to_quaternion(), self.scale[L])
        pose[H] = Matrix.LocRotScale(h, q @ pose[H].to_quaternion(), self.scale[H])
        pose['WPN_root'] = weapon_from_hand(q @ pose['WPN_root'].to_quaternion(), pose[H])
