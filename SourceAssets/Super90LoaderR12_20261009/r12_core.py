"""Super90 tube loader R12 shared authoring core (Blender background).

Endpoints come from the installed idle (Super90IdleMatchWalk20261008) and the
four grip profiles; UE SOURCE poses are calibrated into the native author root.
Reference: user Delta Force M1014 capture (empty reload); see
Docs/Weapons/super90-speedloader-r12-plan-20261009.md. Authoring only.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

O = Path(__file__).parent; S = O.parent
bpy.ops.wm.open_mainfile(filepath=str(S / 'BenelliM4Super9020261006/Super90_Gameplay_Editable.blend'))
rig = bpy.data.objects['SK_Super90']; scene = bpy.context.scene; scene.render.fps = 60
rig.data.pose_position = 'POSE'
rig.animation_data.action = bpy.data.actions['A_Super90_idle']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_set(0); bpy.context.view_layer.update()
blend_idle = {b.name: b.matrix.copy() for b in rig.pose.bones}
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
names = list(rest)
rig.animation_data_clear()
I = Matrix.Identity(4); one = Vector((1, 1, 1)); UP = Vector((0, 0, 1))
FAMILIES = ('vertical', 'canted', 'prism', 'angled')

def smooth(x):
    x = max(0., min(1., x)); return x * x * x * (x * (x * 6 - 15) + 10)
def phase(f, a, b): return smooth((f - a) / (b - a)) if b != a else float(f >= a)
def pulse(f, a, b): return math.sin(math.pi * max(0., min(1., (f - a) / (b - a))))
def mix(a, b, t):
    pa, qa, sa = a.decompose(); pb, qb, sb = b.decompose()
    if qa.dot(qb) < 0: qb.negate()
    return Matrix.LocRotScale(pa.lerp(pb, t), qa.slerp(qb, t), sa.lerp(sb, t))
def T(v): return Matrix.Translation(Vector(v))
def copy(p): return {n: m.copy() for n, m in p.items()}
def uemat(v): return Matrix.LocRotScale(Vector(v[:3]), Quaternion((v[6], *v[3:6])), Vector(v[7:10]))
def ortho(m):
    return Matrix.LocRotScale(m.translation, m.to_quaternion(), one)
def bezier(a, b, c, d, t): return a * (1 - t) ** 3 + b * (3 * (1 - t) ** 2 * t) + c * (3 * (1 - t) * t * t) + d * t ** 3

# --- UE SOURCE -> native author calibration (same method as the sprint/R3 fix).
NATIVE = json.loads((S / 'Super90Foregrips20261007/native.json').read_text())
C = Matrix.Diagonal((100, -100, 100, 1)); Ci = C.inverted()
K = {n: (C @ rest[n]).inverted() @ uemat(NATIVE['rest'][n]) for n in names}
Ki = {n: m.inverted() for n, m in K.items()}
eval_base = {}
for n in names:
    eval_base[n] = eval_base.get(parents[n], I) @ uemat(NATIVE['clips']['idle']['samples'][0]['local'][n])
ROOT = next(n for n in names if parents[n] is None)
evaluation_to_author = blend_idle[ROOT] @ (Ci @ eval_base[ROOT] @ Ki[ROOT]).inverted()

def author_pose(row):
    world = {}
    for n in names: world[n] = world.get(parents[n], I) @ uemat(row[n])
    return {n: ortho(evaluation_to_author @ Ci @ world[n] @ Ki[n]) for n in names}

# --- Installed idle: R9 idle samples with the accepted walking left hold.
WALK = S / 'Super90IdleMatchWalk20261008'
INPUTS = json.loads((WALK / 'inputs.json').read_text())
PATCH = json.loads((WALK / 'idle_patch.json').read_text())
LEFT_BONES = PATCH['left_bones']
row0 = {n: list(v) for n, v in INPUTS['idle_rows'][0].items()}
for track in PATCH['base_tracks']: row0[track['bone']] = track['values'][:10]
def apply_first_key(row, tracks):
    r = {n: list(v) for n, v in row.items()}
    for t in tracks:
        n = t['bone']; d = t['values'][:10]; v = r[n]
        q = Quaternion((d[6], *d[3:6])) @ Quaternion((v[6], *v[3:6]))
        r[n] = [v[0] + d[0], v[1] + d[1], v[2] + d[2], q.x, q.y, q.z, q.w, v[7] + d[7], v[8] + d[8], v[9] + d[9]]
    return r
idles = {'base': author_pose(row0)}
for fam in FAMILIES:
    idles[fam] = author_pose(apply_first_key(row0, PATCH['profiles'][fam]['idle']['tracks']))
idle = idles['base']
G0 = idle['WPN_root']; R0 = rest['WPN_root']; GI = G0.inverted()
BIND_TO_IDLE = G0 @ R0.inverted()
finger_names = {s: [n for n in names if n.endswith('_' + s) and n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))] for s in 'lr'}

barrel = (idle['WPN_FrontSight'].translation - idle['WPN_RearSight'].translation).normalized()
FORWARD = Vector((barrel.x, barrel.y, 0)).normalized(); RIGHT = FORWARD.cross(UP).normalized()
local_rest = {n: rest[parents[n]].inverted() @ rest[n] if parents[n] else rest[n] for n in names}

# --- Game camera reconstructed for the Super90 hip framing (R4 trace).
CAMERA = json.loads((S / 'Super90LoaderRepair20261008/author_geometry_r3.json').read_text())['camera']
CQ = Quaternion(CAMERA['rotation']); CP = Vector(CAMERA['location'])
TAN_V = math.tan(math.radians(37.5)); TAN_H = TAN_V * 16 / 9
def cam(p): return CP + CQ @ Vector((p.x * 100, -p.y * 100, p.z * 100))
def native_delta(v):
    p = CQ.inverted() @ Vector(v); return Vector((p.x / 100, -p.y / 100, p.z / 100))
EYE = native_delta(-CP)
def screen(p):
    c = cam(p)
    if c.x < 1.: return (9., 9., c.x)
    return (c.y / (c.x * TAN_H), c.z / (c.x * TAN_V), c.x)
def on_screen(p, margin=0.):
    u, v, x = screen(p); return x > 4 and abs(u) <= 1 - margin and abs(v) <= 1 - margin

# --- Arm solver (native two-bone lengths, continuous pole, skin stations).
def segment_frame(direction, hinge):
    x = direction.normalized(); z = (hinge - x * hinge.dot(x)).normalized()
    return Matrix((x, z.cross(x).normalized(), z)).transposed().to_quaternion()
skin_stations = {}
for side in 'lr':
    d = rest['hand_' + side].translation - rest['lowerarm_' + side].translation
    skin_stations[side] = {pre + side: max(0., min(1., (rest[pre + side].translation - rest['lowerarm_' + side].translation).dot(d) / d.length_squared))
                           for pre in ('lowerarm_aux_', 'lowerarm_twist_02_', 'lowerarm_twist_01_')}
ARM_LEN = {s: (rest['lowerarm_' + s].translation - rest['upperarm_' + s].translation).length +
              (rest['hand_' + s].translation - rest['lowerarm_' + s].translation).length for s in 'lr'}
# Neutral wrist: the installed idle hand/forearm relation (swing reported relative to it).
PALM_AXIS = {s: idle['hand_' + s].to_quaternion().inverted() @ (idle['hand_' + s].translation - idle['lowerarm_' + s].translation).normalized() for s in 'lr'}
twist_context = {}; pole_context = {}; POLE_STEP = 5.0

def arm(p, source, target, side, pole_rotation=0., continuous=False, natural_axis=None, hint_weight=0., relax=0., home=0.):
    upper = 'upperarm_' + side; lower = 'lowerarm_' + side; hand = 'hand_' + side
    p['clavicle_' + side] = source['clavicle_' + side].copy()
    shoulder = source[upper].translation.copy(); elbow = source[lower].translation.copy(); wrist = source[hand].translation
    goal = target.translation; v = goal - shoulder; dist = v.length; axis = v.normalized()
    a = (rest[lower].translation - rest[upper].translation).length
    b = (rest[hand].translation - rest[lower].translation).length
    reach = (a + b) * .975
    if dist > reach:
        shift = axis * (dist - reach); shoulder += shift; p['clavicle_' + side].translation += shift; dist = reach
    dist = max(abs(a - b) + 1e-5, dist); along = (a * a - b * b + dist * dist) / (2 * dist)
    old_axis = (wrist - source[upper].translation).normalized()
    pole = elbow - source[upper].translation; pole -= old_axis * pole.dot(old_axis)
    pole = old_axis.rotation_difference(axis) @ pole
    if pole.length < 1e-6:
        pole = Vector((0, 0, -1)); pole -= axis * pole.dot(axis)
    if natural_axis is not None and hint_weight > 0:
        # Elbow on the exact two-bone circle nearest the natural wrist continuation.
        h = goal - natural_axis.normalized() * b - shoulder; h -= axis * h.dot(axis)
        if h.length > 1e-4:
            pole = Quaternion().slerp(pole.normalized().rotation_difference(h.normalized()), min(1., hint_weight)) @ pole.normalized()
    pole = Quaternion(axis, math.radians(pole_rotation)) @ pole
    if continuous:
        # Elbow continuity: at most POLE_STEP degrees of swing about the shoulder-wrist axis per frame.
        prev = pole_context.get(side)
        pole = pole.normalized()
        if prev is not None:
            pv = prev - axis * prev.dot(axis)
            if pv.length > 1e-6:
                pv.normalize(); ang = pv.angle(pole)
                if ang > math.radians(POLE_STEP):
                    pole = pv.slerp(pole, math.radians(POLE_STEP) / ang) if ang < math.pi - 1e-3 else pv
        pole_context[side] = pole.copy()
    knee = shoulder + axis * along + pole.normalized() * math.sqrt(max(0., a * a - along * along))
    u0 = elbow - source[upper].translation; f0 = wrist - elbow; h0 = u0.cross(f0)
    u = knee - shoulder; w = goal - knee; h = u.cross(w)
    qa = segment_frame(u, h) @ segment_frame(u0, h0).inverted()
    qb = segment_frame(w, h) @ segment_frame(f0, h0).inverted()
    upper_q = qa @ source[upper].to_quaternion(); lower_q = qb @ source[lower].to_quaternion()
    p[upper] = Matrix.LocRotScale(shoulder, upper_q, one)
    p[lower] = Matrix.LocRotScale(knee, lower_q, one)
    for n in names:
        if n.startswith('upperarm_twist') and n.endswith('_' + side):
            p[n] = p[upper] @ source[upper].inverted() @ source[n]
    fa = w.normalized()
    def axial(q):
        a = 2 * math.atan2(Vector((q.x, q.y, q.z)).dot(fa), q.w); return (a + math.pi) % (2 * math.pi) - math.pi
    # Carried: twist relative to the source hand transported by the forearm.
    carried = axial(target.to_quaternion() @ (qb @ source[hand].to_quaternion()).inverted())
    # Anatomical: pronation/supination relative to the native rest hand/forearm relation.
    neutral_hand = lower_q @ rest[lower].to_quaternion().inverted() @ rest[hand].to_quaternion()
    anatomical = axial(target.to_quaternion() @ neutral_hand.inverted())
    # Pronation is a bounded physical quantity: wrap into a fixed anatomical
    # window per side (no frame-to-frame unwrapping, which can drift a full turn).
    lo = math.radians(-300. if side == 'l' else -130.)
    anatomical = (anatomical - lo) % (2 * math.pi) + lo
    # Same measure on the installed source pose; only the CHANGE of pronation is
    # spread over the twist stations, on top of the accepted idle distribution.
    src_fa = (wrist - elbow).normalized()
    sq = source[hand].to_quaternion() @ (source[lower].to_quaternion() @ rest[lower].to_quaternion().inverted() @ rest[hand].to_quaternion()).inverted()
    a_src = 2 * math.atan2(Vector((sq.x, sq.y, sq.z)).dot(src_fa), sq.w)
    a_src = (a_src - lo) % (2 * math.pi) + lo
    delta = (anatomical - a_src + math.pi) % (2 * math.pi) - math.pi
    if continuous:
        # Skin twist is soft tissue: keep it continuous and rate-limited so a hold
        # whose idle pronation sits on the far side of the twist circle (angled
        # grip) eases over the off-screen frames instead of snapping per frame.
        key = side + '_delta'; prev_d = twist_context.get(key)
        if prev_d is not None:
            delta = prev_d + (delta - prev_d + math.pi) % (2 * math.pi) - math.pi
            step = delta - prev_d; lim = math.radians(8.)
            if abs(step) > lim: delta = prev_d + math.copysign(lim, step)
        twist_context[key] = delta
    for n, wgt in skin_stations[side].items():
        basis = p[lower] @ source[lower].inverted() @ source[n]
        bq = basis.to_quaternion(); tq = Quaternion(fa, delta * wgt) @ bq
        if home > 0:
            # The clip ends exactly on the idle pose; ease the skin twist onto it.
            if bq.dot(tq) < 0: tq.negate()
            tq = bq.slerp(tq, 1 - home)
        p[n] = Matrix.LocRotScale(basis.translation, tq, one)
    p[hand] = ortho(target)
    return {'reach': (goal - source[upper].translation).length / ARM_LEN[side], 'twist_deg': math.degrees(carried),
            'pronation_deg': math.degrees(anatomical), 'pronation_delta_deg': math.degrees(delta),
            'shoulder_shift_cm': 100 * (shoulder - source[upper].translation).length}

def twist_slerp(qa, qb, axis, t, sign=0):
    """Interpolate qa->qb, turning about `axis` in a chosen direction (+1 pronate, -1 supinate)."""
    r = qb @ qa.inverted()
    if r.w < 0: r.negate()
    axis = axis.normalized(); v = Vector((r.x, r.y, r.z)); proj = v.dot(axis)
    ang = 2 * math.atan2(proj, r.w)
    ang = (ang + math.pi) % (2 * math.pi) - math.pi
    # Force the anatomical direction only for large turns; small ones stay shortest.
    # A forced twist longer than ~180 deg corkscrews the wrist the wrong way
    # (angled-grip idle: 235 deg), so it falls back to the shortest direction.
    if sign > 0 and ang < -math.radians(60):
        if ang + 2 * math.pi <= math.radians(170): ang += 2 * math.pi
    if sign < 0 and ang > math.radians(60):
        if ang - 2 * math.pi >= -math.radians(170): ang -= 2 * math.pi
    twist = Quaternion(axis, ang); swing = r @ twist.inverted()
    if swing.w < 0: swing.negate()
    # Swing is clamped; the twist may overshoot slightly with eased (settle) inputs.
    return Quaternion().slerp(swing, max(0., min(1., t))) @ Quaternion(axis, ang * t) @ qa

def wrist_swing(p, side):
    fa = (p['hand_' + side].translation - p['lowerarm_' + side].translation).normalized()
    return math.degrees(fa.angle(p['hand_' + side].to_quaternion() @ PALM_AXIS[side]))

# --- Grip post grasp (fit_knob_grasp.py) and finger channels.
GRASP = json.loads((O / 'knob_grasp.json').read_text())
HAND_IN_POST = Matrix(GRASP['hand_in_post'])
POST_FINGERS = {n: Matrix(v) for n, v in GRASP['finger_local'].items()}
PUSH = Vector(GRASP['push_direction_in_post']); POST = GRASP['post']
# Natural wrist for the post: the vertical-foregrip donor hand/forearm relation.
_DONOR = json.loads((S / 'Super90LoaderRebuild20261007/grasp_skin_inputs.json').read_text())['grasp']
_dh = Matrix(_DONOR['hand_l']); _dl = Matrix(_DONOR['lowerarm_l'])
POST_FOREARM_AXIS = _dh.to_quaternion().inverted() @ (_dh.translation - _dl.translation).normalized()
def anatomical_twist(hand_m, lower_m, side='l'):
    fa = (hand_m.translation - lower_m.translation).normalized()
    neutral = lower_m.to_quaternion() @ rest['lowerarm_' + side].to_quaternion().inverted() @ rest['hand_' + side].to_quaternion()
    q = hand_m.to_quaternion() @ neutral.inverted()
    a = 2 * math.atan2(Vector((q.x, q.y, q.z)).dot(fa), q.w); return math.degrees((a + math.pi) % (2 * math.pi) - math.pi)
DONOR_PRONATION = anatomical_twist(_dh, _dl)
IDLE_PRONATION = anatomical_twist(idle['hand_l'], idle['lowerarm_l'])
def post_swing(p):
    fa = (p['hand_l'].translation - p['lowerarm_l'].translation).normalized()
    return math.degrees(fa.angle(p['hand_l'].to_quaternion() @ POST_FOREARM_AXIS))
def finger_local(pose, n): return pose[parents[n]].inverted() @ pose[n]
OPEN = {}; SPLAY = {}
for n in finger_names['l']:
    pp, qq, ss = finger_local(idle, n).decompose(); rq = local_rest[n].to_quaternion()
    amt = 0. if 'metacarpal' in n else (.60 if n.startswith('thumb') else .85)
    OPEN[n] = Matrix.LocRotScale(pp, qq.slerp(rq, amt), ss)
    # Flick: fully extended with a slight hyperextension past the rest pose.
    ax, ang = (qq.inverted() @ rq).to_axis_angle()
    SPLAY[n] = Matrix.LocRotScale(pp, qq @ Quaternion(ax, 0. if 'metacarpal' in n else ang * 1.12), ss)
HOOK = {}
for n in finger_names['l']:
    curl = .62 if n.startswith(('index', 'middle')) else (.42 if n.startswith(('ring', 'pinky')) else .25)
    HOOK[n] = mix(OPEN[n], POST_FINGERS.get(n, OPEN[n]), 0. if 'metacarpal' in n else curl)
DIGIT_ORDER = {'index': 0, 'middle': 1, 'ring': 2, 'pinky': 3, 'thumb': 4}

# --- Clock (60 Hz source; gameplay base rate 1.3x).
INSERT = 90; STEP = 4; SHOW_BEGIN = 74; HIDE_TAIL = 13; NORMAL_TAIL = 32; EMPTY_TAIL = 68
RELEASE_TAIL = 48; CYCLE_START_TAIL = 16; CYCLE_FRAMES = 66; PLAY_RATE = 1.3
def last_frame(count): return INSERT + STEP * (count - 1)
def duration(count, empty): return last_frame(count) + (EMPTY_TAIL if empty else NORMAL_TAIL)

# --- Geometry anchors in native bind space (+Y muzzle, +X right, +Z up).
MOUTH = Vector((0., -.035, -.792))
BUTT_BIND = Vector((0., -.4895, -.8266))     # stock butt-pad centre (measured); stays in the shoulder pocket
POST_OFFSET = -POST['tube_axis_z_m']       # post centre to tube axis distance
PLUNGER_DRIVER = 'WPN_SOCKET_Magazine'
BOLT_OPEN = .1065
HANDLE_OPEN_BIND = Vector((.030, .0155 - BOLT_OPEN, -.7515))   # locked-back charging handle centre (measured)

LAYOUT = json.loads((O / 'layout.json').read_text()) if (O / 'layout.json').exists() else {}
def L(key, default): return LAYOUT.get(key, default)
STROKE_REAR = .025; STROKE_FRONT = .040
def tube_len(lay=None): return (lay or LAYOUT).get('tube_len', .450)
def stroke_len(lay=None): return tube_len(lay) - STROKE_REAR - STROKE_FRONT
TUBE_LEN = tube_len(); STROKE = stroke_len()

def tube_bind(lay=None):
    lay = lay or LAYOUT
    return T(MOUTH) @ Matrix.Rotation(math.radians(lay.get('tube_yaw', 0.)), 4, 'Y') @ Matrix.Rotation(math.radians(lay.get('tube_pitch', 52.)), 4, 'X')

def post_in_tube(s, lay=None):
    """Grip-post frame in tube space; s = slide distance from the rear stop."""
    lay = lay or LAYOUT
    psi = math.radians(lay.get('post_psi', 0.))
    radial = (Vector((0, 0, -1)) * math.cos(psi) + Vector((-1, 0, 0)) * math.sin(psi)).normalized()
    yt = Vector((0, 1, 0))
    # Post frame basis: PUSH -> tube +Y, Z -> radial, Z x PUSH -> radial x Y.
    src = Matrix((PUSH, Vector((0, 0, 1)).cross(PUSH).normalized(), Vector((0, 0, 1)))).transposed()
    dst = Matrix((yt, radial.cross(yt).normalized(), radial)).transposed()
    rot = (dst @ src.inverted()).to_4x4()
    origin = radial * POST_OFFSET + yt * (-tube_len(lay) + STROKE_REAR + s)
    return T(origin) @ rot

def push_fraction(f):
    """Shells pass the latch on the native contact clock (90 + 4 i). Break-away start,
    a click (speed dip) at every shell, full speed into the last one and a hard stop
    (the stop is wherever the count ends; the gun takes the seat kick)."""
    x = max(0., min(7., (f - 86) / STEP)); i = min(6, int(x)); t = x - i
    speeds = (.10, .85, 1.25, 1.30, 1.30, 1.30, 1.30, 1.30)
    a = speeds[i]; b = speeds[i + 1]
    t = (-2 * t ** 3 + 3 * t * t) + (t ** 3 - 2 * t * t + t) * a + (t ** 3 - t * t) * b
    if i > 0: t = t - .30 * math.sin(2 * math.pi * t) / (2 * math.pi)      # latch click per shell
    return (i + t) / 7.
