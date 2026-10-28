"""Dual kukri combo stages 1 and 2 (Clips/DualAttack.json, Clips/DualAttack2.json, 120 fps): the right blade swings the
single stage, then the left blade swings its mirror image (user 2026-10-26: "first hit like the single one, upper-right
to lower-left; dual: the left hand mirrors it; right first, then left"; then "the second stage the same way").

Sources: SourceAssets/Kukri20261020/Clips/Attack.json (stage 1, V6 sweep right -> left, contact 0.32-0.45) and
Attack2.json (stage 2, V11 diagonal upper-left -> lower-right, contact 0.34-0.47), both 38/30 s, and the accepted dual
hold (Clips/DualIdle.json frame 0).  OFFSET = the runtime's KukriRhythm::DualSweepOffsets[stage]: the left swing is the
mirrored single clip at t - OFFSET.  The two arms take turns and never share space (Work/r4/dualattack_clear.py: capsule
clearance between the arms and blades every 1/60 s; the start and end are also checked on the real kukri SDF):
 DualAttack (OFFSET 56/120 s)
  right  0.04-0.17  blends from the dual hold into the single swing (its wind-up up and right), then plays the single
                    clip -- cut in from the right, contact 0.32-0.45, follow-through to the left -- and from ~0.60 drops
                    straight down into the hanging rest (the mirror of the single clip's lowered left arm, below the frame)
                    instead of the single clip's under-frame turn back to the right, which would cross the left's swing;
                    it rises from there back into the dual hold over the last 0.35 s
  left   leaves the X at once with its mirrored wind-up (up and LEFT, out of the frame, single clip 0.00-0.23 from 0.00),
         waits there while the right sweeps, then plays the mirrored single clip: cut in from the left, contact
         OFFSET+0.32..0.45 left -> right, follow-through to the right, under-frame turn back and lift to the mirrored
         stance, blending into the dual hold over the last 0.25 s
 DualAttack2 (OFFSET 60/120 s)
  The right's wind-up crosses the body close to the lens to the LEFT edge (where the left fist holds), so the left first
  drops straight down into its hanging rest (the single clip's own lowered left arm) and rises from there into its own
  mirrored swing:
  right  blends from the hold into the single diagonal (fist down to the bottom centre, back-hand wind-up up the left,
         one cut through the centre to the lower right, contact 0.34-0.47), drops from ~0.48 into the hanging rest, rises
         back into the hold over the last 0.35 s
  left   slides its kukri rigidly off the right one (toward the lens, 0.00-0.06), then out to the left and down (0.06-0.16:
         the right wind-up sweeps up the left side close to the lens right after; a plain drop swung the left blade
         back through the right one), drops into the hanging rest (0.16-0.32), waits there, rises at OFFSET into the
         mirrored diagonal: fist to the bottom
         centre, wind-up up the RIGHT, cut through the centre to the lower left (contact OFFSET+0.34..0.47), under-frame
         turn and lift to the mirrored stance, into the hold over the last 0.25 s
 Both clips end on DualIdle frame 0.
Mirror: the virtual-right -> left mapping of dual_rig (left bone rotation = ROT_X180 @ right world rotation, positions from
the left bones' own locals = the mirror image, bind-checked symmetric); the left kukri rides hand_l with the constant
left_kukri.json grip, so it is the mirrored single kukri.
Run:  python -I author_dual_attack.py [DualAttack] [DualAttack2] [--preview]
      -> Clips/<name>.json (+ Work/render/<name lower>.json with --preview)
"""
import json
import sys
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
from dual_rig import DualRig, ROT_X180, ndc  # noqa: E402
from kmath import T, qmat, qfrommat, qslerp, mesh_to_cam, cam_to_mesh  # noqa: E402

FPS = 120
SINGLE_DIR = P.parent / 'Kukri20261020' / 'Clips'
STAGES = {
    'DualAttack': dict(
        source='Attack.json', offset_frames=56,
        entry=0.13, entry_delay=0.04,          # right: hold -> single swing (the X opens from the left blade first)
        right_stop=0.75, right_drop=(0.60, 0.92), right_back=0.35,
        left_mode='windup', left_start=0.0, left_wait=0.23, left_in=(0.0, 0.10), left_back=0.25),
    'DualAttack2': dict(
        source='Attack2.json', offset_frames=60,
        entry=0.13, entry_delay=0.06,
        right_stop=0.60, right_drop=(0.48, 0.80), right_back=0.35,
        left_mode='hang', left_out=(((0.0, 0.06), (-6.0, 4.0, 2.0)), ((0.06, 0.16), (-8.0, 20.0, -12.0))), left_drop=(0.16, 0.32),
        left_in=(0.0, 0.15), left_back=0.25),
}


def smooth(a, b, t):
    x = min(1.0, max(0.0, (t - a) / (b - a)))
    return x * x * (3 - 2 * x)


def frame_local(clip, k):
    fr = clip['frames'][k]
    return {n: T(v[0], v[1], v[2]) for n, v in fr.items()}


def sample_local(clip, t):
    """Parent-local pose of a 120 fps clip at time t (slerp between frames)."""
    n = len(clip['frames'])
    x = min(max(t * FPS, 0.0), n - 1.0)
    i = min(int(x), n - 2)
    a, b, f = frame_local(clip, i), frame_local(clip, i + 1), x - i
    return {k: T(a[k].p + (b[k].p - a[k].p) * f, qslerp(a[k].q, b[k].q, f), a[k].s) for k in a}


def blend_local(a, b, w, names):
    out = dict(a)
    for k in names:
        qb = b[k].q if np.dot(a[k].q, b[k].q) >= 0 else -b[k].q
        out[k] = T(a[k].p + (b[k].p - a[k].p) * w, qslerp(a[k].q, qb, w), a[k].s)
    return out


def left_time(c, t, offset, length):
    """Single-clip time of the mirrored left swing."""
    if c['left_mode'] == 'windup':
        if t < c['left_start']:
            return 0.0
        if t < c['left_start'] + c['left_wait']:
            return t - c['left_start']
        if t < offset + c['left_wait']:
            return c['left_wait']
    return min(max(t - offset, 0.0), length - offset)


def author(D, name, preview):
    c = STAGES[name]
    R = D.R
    rig = R.rig
    single = json.loads((SINGLE_DIR / c['source']).read_text('utf-8'))
    hold_clip = json.loads((P / 'Clips' / 'DualIdle.json').read_text('utf-8'))
    assert single['bones'] == hold_clip['bones'] == rig.names
    offset = c['offset_frames'] / FPS
    L1 = single['length']
    length = offset + L1
    n = int(round(length * FPS))
    hold = frame_local(hold_clip, 0)
    right_chain = [k for k in rig.names if k in R.right_chain or k in R.wpn_desc]
    left_chain = D.left_chain
    local_base = R.base_local
    # Hanging rests below the frame: the single clip's own lowered left arm, and its mirror for the right.
    w0 = rig.world(frame_local(single, 0))
    world = rig.world(dict(hold))
    for k in rig.names:
        if k in R.right_chain:
            src = w0[k[:-2] + '_l']
            world[k] = T(world[D.parent[k]].point(local_base[k].p), qfrommat(ROT_X180 @ qmat(src.q)), src.s)
    hang_r = rig.localize(world)
    hang_l = frame_local(single, 0)
    outs = []
    if 'left_out' in c:
        # The left blade lies over the right one, nearer the lens: the left fist first slides its kukri straight off
        # it -- the dual hold's left hand and blade translated rigidly (camera fwd / left / up per step), the arm re-solved
        # to it -- and only then drops into the hanging rest.
        keys = json.loads((P / 'pose_keys.json').read_text('utf-8'))
        lp = keys['left_mirrored']
        Kv, Ev, dv = D.arm(lp)
        Kh = dv['K_hand']
        for window, (fwd, left, up) in c['left_out']:
            d = cam_to_mesh((fwd, left, up))       # virtual (mirrored) camera: + y is the actual left
            world_v, _ = R.pose(T(Kh.p + d, Kh.q, Kh.s), clav_r=tuple(lp.get('C', (0, 0, 0))), pole_r=Ev + d, pole_r_weight=1.0)
            world_out = rig.world(dict(hold))
            for k in left_chain:
                src = world_v[k[:-2] + '_r']
                world_out[k] = T(world_out[D.parent[k]].point(local_base[k].p), qfrommat(ROT_X180 @ qmat(src.q)), src.s)
            outs.append((window, rig.localize(world_out)))
    e0, e1 = c['entry_delay'], c['entry_delay'] + c['entry']
    frames, diags, prev, previews = [], [], None, {}
    for i in range(n + 1):
        t = i / FPS
        # Right: the single swing, then the hanging rest, then back into the hold.
        pose = blend_local(dict(hold), sample_local(single, min(t, c['right_stop'])), smooth(e0, e1, t), right_chain)
        pose = blend_local(pose, hang_r, smooth(*c['right_drop'], t), right_chain)
        pose = blend_local(pose, hold, smooth(length - c['right_back'], length, t), right_chain)
        # Left: the mirrored single swing on its own clock.
        left_world_v = rig.world(sample_local(single, left_time(c, t, offset, length)))
        world = rig.world(pose)
        for k in left_chain:
            src = left_world_v[k[:-2] + '_r']
            world[k] = T(world[D.parent[k]].point(local_base[k].p), qfrommat(ROT_X180 @ qmat(src.q)), src.s)
        mirrored = rig.localize(world)
        if c['left_mode'] == 'hang':
            for window, out_l in outs:
                pose = blend_local(pose, out_l, smooth(*window, t), left_chain)
            pose = blend_local(pose, hang_l, smooth(*c['left_drop'], t), left_chain)
            w_left = smooth(offset + c['left_in'][0], offset + c['left_in'][1], t)
        else:
            w_left = smooth(*c['left_in'], t)
        pose = blend_local(pose, mirrored, w_left, left_chain)
        pose = blend_local(pose, hold, smooth(length - c['left_back'], length, t), left_chain)
        if i == n:
            pose = dict(hold)                      # exact seam into DualIdle
        world = rig.world(pose)
        b = R.base
        K = R.hand_rel.inverse() * world['hand_r']
        world['WPN_root'] = T(K.p, K.q, b['WPN_root'].s)
        for k in rig.names:
            if k in R.wpn_desc and k != 'WPN_root':
                world[k] = R.base_local[k] * world[D.parent[k]]
        for s in 'lr':
            ik = 'ik_hand_' + s
            if ik in world:
                world[ik] = b[ik].relative_to(b['hand_' + s]) * world['hand_' + s]
        lk = R.local_keys(world, prev)
        prev = {k: v[1] for k, v in lk.items()}
        frames.append({k: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for k, v in lk.items()})
        hr, hl = mesh_to_cam(world['hand_r'].p), mesh_to_cam(world['hand_l'].p)
        diags.append(dict(t=round(t, 4), hand_r=[round(v, 3) for v in ndc(hr)], hand_l=[round(v, 3) for v in ndc(hl)],
                          w=[round(smooth(e0, e1, t), 3), round(w_left, 3), round(smooth(length - c['right_back'], length, t), 3)]))
        if preview and i % 8 == 0:
            K = world['WPN_root']
            left = json.loads((P / 'left_kukri.json').read_text('utf-8'))['rel_to_hand_l']
            rel = T(left['location'], left['rotation_wxyz'], (1, 1, 1))
            hl_ = world['hand_l']
            Kl = rel * T(hl_.p, hl_.q, (1, 1, 1))
            previews['%s_%04d' % (name.lower(), int(round(t * 1000)))] = dict(
                bones={k: x.pack() for k, x in world.items()}, kukri_r=T(K.p, K.q, (1, 1, 1)).pack(), kukri_l=Kl.pack())
    data = dict(name=name, fps=FPS, length=length, loop=False,
                contact=[single['contact'][0], single['contact'][1], offset + single['contact'][0], offset + single['contact'][1]],
                bones=rig.names, frames=frames, diagnostics=diags)
    (P / 'Clips' / (name + '.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    print('%s %.4f s, %d frames, offset %.4f s' % (name, length, len(frames), offset))
    if previews:
        out = P / 'Work' / 'render'
        out.mkdir(parents=True, exist_ok=True)
        (out / (name.lower() + '.json')).write_text(json.dumps(dict(poses=previews)), encoding='utf-8')
        print('previews:', len(previews))


# ---------------------------------------------------------------------------------------------------------- stage 3
# DualAttack3 (2026-10-26, user: "the third stage as the reference's double thrust, both blades forward together, ~100 %
# including the screen shake and the impact"): reference BV19dUqBJECT 近战动作 #5「双刃断川·破军势」, file 84.20-85.33 s
# (the user said 1:25-1:26; the move itself runs 84.2-85.3 s).  R8 (user: "slow it a little; check the blade direction,
# the grip and the wrist"): each arm has its own keys (fit_dual_thrust.py -> thrust_keys.json right / left): the right
# fist punches in from the right with its blade lying across to the crosshair, the left rises from below with its blade
# up and in to the same point, both wrists near the accepted rest (R7 drove both blades straight ahead, end-on, on a
# 43 deg ulnar wrist).  R9 (user: "the left too: a forward thrust like the right, edge forward"): the left is the right's
# mirror, from the left edge with its blade across to the crosshair, a little lower and nearer so it passes just under
# the right blade.  R7 ran at the reference's own pace (impact 0.30 s, the drive one frame); R8 is ~1.26x slower to
# the hit (0.38 s at the base attack speed) with the drive over 0.10 author s, and holds the hit a little longer.
# Phases (author s; the runtime's KukriRhythm::DualThrust; curve_thrust.py maps them onto the reference camera):
#   0.00-0.22 hold -> chamber (each fist out to its own edge, blade across)                    ref 84.17-84.28
#   0.22-0.50 chamber -> coil (drawn 2 cm back; the lunge runs 0.24-0.60)                      ref 84.28-84.43
#   0.50-0.60 the drive: coil -> impact, accelerating                                          ref 84.43-84.47
#   0.60 impact; 0.60-0.66 overshoot 2.5 cm deeper; 0.66-0.84 back onto the impact and held      ref 84.47-84.60
#   0.84-1.00 the right pulls out past the lower right, the left past the lower left (drop keys), 0.98-1.14 into the
#   hanging rests; 1.70-2.05 they rise back into the dual hold
THRUST = dict(length=2.05, t_in=(0.0, 0.22), coil=(0.22, 0.50), drive=(0.50, 0.60), press=(0.60, 0.66),
              settle=(0.66, 0.84), drop=(0.84, 1.00), hang=(0.98, 1.14), rise=(1.70, 2.05), contact=(0.54, 0.72),
              # R16 (2026-10-27, the 猎手刀身 long blade, tip 36 cm): the mirrored blades meet on the centre line during the
              # drive (-0.4 cm on the hunter envelope, kukri_sdf KUKRI_SDF_VARIANT=hunter); the left wrist rides 3 cm
              # lower through the whole move (>= 2 cm clear).  Camera cm, applied to every left key.
              left_offset=(0.0, 0.0, -3.0))


def author_thrust(D, preview):
    import fit_dual_thrust as FT
    R = D.R
    rig = R.rig
    F = FT.FR.Fitter(R)
    keys = json.loads((P / 'thrust_keys.json').read_text('utf-8'))
    X = {k: np.array([keys['right'][k]['x'], keys['left'][k]['x']], float) for k in ('chamber', 'coil', 'impact', 'press', 'drop')}
    for k in X:                         # elbow swivel / forearm roll: the same turn as the impact's, not 360 deg away
        X[k][:, 3:5] -= 360.0 * np.round((X[k][:, 3:5] - X['impact'][:, 3:5]) / 360.0)
    for k in X:
        X[k][1, 0:3] += np.asarray(THRUST['left_offset'], float)
    hold_clip = json.loads((P / 'Clips' / 'DualIdle.json').read_text('utf-8'))
    single = json.loads((SINGLE_DIR / 'Attack3.json').read_text('utf-8'))
    hold = frame_local(hold_clip, 0)
    right_chain = [k for k in rig.names if k in R.right_chain or k in R.wpn_desc]
    left_chain = D.left_chain
    local_base = R.base_local
    c = THRUST
    length = c['length']
    n = int(round(length * FPS))
    # Hanging rests below the frame: the single clip's own lowered left arm, and its mirror for the right.
    w0 = rig.world(frame_local(single, 0))
    world = rig.world(dict(hold))
    for k in rig.names:
        if k in R.right_chain:
            src = w0[k[:-2] + '_l']
            world[k] = T(world[D.parent[k]].point(local_base[k].p), qfrommat(ROT_X180 @ qmat(src.q)), src.s)
    hang = rig.localize(world)
    hang.update({k: v for k, v in frame_local(single, 0).items() if k in left_chain})

    def lerp(a, b, w):
        return a + (b - a) * w

    def keys_at(t):
        if t <= c['coil'][0]:
            return X['chamber']
        if t <= c['coil'][1]:
            return lerp(X['chamber'], X['coil'], smooth(*c['coil'], t))
        if t <= c['drive'][1]:
            u = min(1.0, max(0.0, (t - c['drive'][0]) / (c['drive'][1] - c['drive'][0])))
            return lerp(X['coil'], X['impact'], u * u)                      # accelerating into the target
        if t <= c['press'][1]:
            u = (t - c['press'][0]) / (c['press'][1] - c['press'][0])
            return lerp(X['impact'], X['press'], 1.0 - (1.0 - u) ** 2)       # overshoot, braking
        if t <= c['settle'][1]:
            return lerp(X['press'], X['impact'], smooth(*c['settle'], t))
        return lerp(X['impact'], X['drop'], smooth(*c['drop'], t))

    def arms_local(x):
        world = dict(F.evaluate(x[0], full=True)['world'])
        virtual = F.evaluate(x[1], full=True)['world']                      # the left: its virtual right arm, mirrored
        for k in left_chain:
            src = virtual[k[:-2] + '_r']
            world[k] = T(world[D.parent[k]].point(local_base[k].p), qfrommat(ROT_X180 @ qmat(src.q)), src.s)
        return rig.localize(world)

    chains = right_chain + left_chain
    frames, diags, prev, previews = [], [], None, {}
    for i in range(n + 1):
        t = i / FPS
        pose = blend_local(dict(hold), arms_local(keys_at(t)), smooth(*c['t_in'], t), chains)
        pose = blend_local(pose, hang, smooth(*c['hang'], t), chains)
        pose = blend_local(pose, hold, smooth(*c['rise'], t), chains)
        if i == n:
            pose = dict(hold)
        world = rig.world(pose)
        b = R.base
        K = R.hand_rel.inverse() * world['hand_r']
        world['WPN_root'] = T(K.p, K.q, b['WPN_root'].s)
        for k in rig.names:
            if k in R.wpn_desc and k != 'WPN_root':
                world[k] = R.base_local[k] * world[D.parent[k]]
        for s in 'lr':
            ik = 'ik_hand_' + s
            if ik in world:
                world[ik] = b[ik].relative_to(b['hand_' + s]) * world['hand_' + s]
        lk = R.local_keys(world, prev)
        prev = {k: v[1] for k, v in lk.items()}
        frames.append({k: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for k, v in lk.items()})
        hr, hl = mesh_to_cam(world['hand_r'].p), mesh_to_cam(world['hand_l'].p)
        diags.append(dict(t=round(t, 4), hand_r=[round(v, 3) for v in ndc(hr)], hand_l=[round(v, 3) for v in ndc(hl)]))
        if preview and (i % 6 == 0 or abs(t - c['drive'][1]) < 1e-6):
            K = world['WPN_root']
            left = json.loads((P / 'left_kukri.json').read_text('utf-8'))['rel_to_hand_l']
            rel = T(left['location'], left['rotation_wxyz'], (1, 1, 1))
            hl_ = world['hand_l']
            Kl = rel * T(hl_.p, hl_.q, (1, 1, 1))
            previews['dualattack3_%04d' % int(round(t * 1000))] = dict(
                bones={k: x.pack() for k, x in world.items()}, kukri_r=T(K.p, K.q, (1, 1, 1)).pack(), kukri_l=Kl.pack())
    data = dict(name='DualAttack3', fps=FPS, length=length, loop=False, contact=list(c['contact']), bones=rig.names,
                frames=frames, diagnostics=diags)
    (P / 'Clips' / 'DualAttack3.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    print('DualAttack3 %.4f s, %d frames' % (length, len(frames)))
    if previews:
        out = P / 'Work' / 'render'
        out.mkdir(parents=True, exist_ok=True)
        (out / 'dualattack3.json').write_text(json.dumps(dict(poses=previews)), encoding='utf-8')
        print('previews:', len(previews))


def main():
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or (list(STAGES) + ['DualAttack3'])
    for a in sys.argv[1:]:                     # quick tuning: --set=DualAttack2.entry_delay=0.08
        if a.startswith('--set='):
            key, v = a[6:].split('=')
            stage, field = key.split('.')
            STAGES[stage][field] = json.loads(v) if v.startswith('[') else tuple(float(x) for x in v.split(',')) if ',' in v else float(v)
    D = DualRig()
    for name in names:
        if name == 'DualAttack3':
            author_thrust(D, '--preview' in sys.argv)
        else:
            author(D, name, '--preview' in sys.argv)


if __name__ == '__main__':
    main()
