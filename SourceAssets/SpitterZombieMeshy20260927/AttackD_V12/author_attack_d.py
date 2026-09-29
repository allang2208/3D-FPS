"""Adapt the complete Attack_D to the retained Meshy skin; no test or render.

The native UE retarget is the clean motion input. Local fitting preserves its
timing, shoulder-driven strike and recovery, using the original bind lengths.
"""
import bpy, json, math, statistics
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
OUT = ROOT / 'Final'
OUT.mkdir(parents=True, exist_ok=True)
NAME = 'A_Spitter_AttackD_V12'
FPS = 60
SECONDS = 2.0
SIDES = ['Left', 'Right']

# Only run the retained setup and helper definitions, never its V7 production.
helper = BASE / 'LibraryMotionV7/author_library_motion.py'
prefix = helper.read_text(encoding='utf-8').split("report={'movement':{}")[0]
prefix = prefix.replace('for role,spec in metadata.items():',
    "for role,spec in [('Attack_D', metadata['Attack_D'])]:")
ns = {'__file__': str(helper), '__name__': 'attack_d_source_helpers'}
exec(compile(prefix, str(helper), 'exec'), ns)
rig, meshes, scene = ns['rig'], ns['meshes'], ns['scene']
ns['ROOT'], ns['OUT'] = ROOT, OUT
apply, sample, point = ns['apply'], ns['sample'], ns['point']
wm, move_hips, set_rotation, aim = ns['wm'], ns['move_hips'], ns['set_rotation'], ns['aim']
rig.animation_data_clear()
rig.animation_data_create()
count = round(SECONDS * FPS) + 1

def smooth(x):
    x = max(0., min(1., x))
    return x*x*x*(x*(x*6-15)+10)

def ramp(a, b, t):
    return smooth((t-a)/(b-a))

def curve_pose(poses, index):
    index = max(0., min(index, len(poses)-1))
    lo = int(index)
    return ns['mix'](poses[lo], poses[min(lo+1, len(poses)-1)], index-lo)

foot_vertices = {}
for mesh in meshes:
    names = {g.index: g.name for g in mesh.vertex_groups}
    foot_vertices[mesh.name] = {side: [v.index for v in mesh.data.vertices
        if sum(g.weight for g in v.groups if names[g.group] in
               [side+'Foot', side+'ToeBase']) > .60] for side in SIDES}

def sole_heights():
    heights = {side: float('inf') for side in SIDES}
    deps = bpy.context.evaluated_depsgraph_get()
    for mesh in meshes:
        obj = mesh.evaluated_get(deps)
        skin = obj.to_mesh()
        try:
            for side in SIDES:
                heights[side] = min(heights[side], min(
                    (obj.matrix_world @ skin.vertices[i].co).z
                    for i in foot_vertices[mesh.name][side]))
        finally:
            obj.to_mesh_clear()
    return heights

def solve_leg(side, target, pole, rotation):
    upper, lower, tip = [side+p for p in ['UpLeg', 'Leg', 'Foot']]
    a, b, c = point(upper), point(lower), point(tip)
    l1, l2 = (b-a).length, (c-b).length
    axis = (target-a).normalized()
    distance = max(abs(l1-l2)+.001, min((target-a).length, (l1+l2)*.995))
    across = pole-a-axis*(pole-a).dot(axis)
    if across.length < 1e-5:
        across = Vector((0, -1, 0))-axis*axis.dot(Vector((0, -1, 0)))
    across.normalize()
    along = (l1*l1-l2*l2+distance*distance)/(2*distance)
    joint = a+axis*along+across*math.sqrt(max(0., l1*l1-along*along))
    aim(upper, b-a, joint-a)
    aim(lower, point(tip)-point(lower), a+axis*distance-point(lower))
    set_rotation(tip, rotation)

def segments(mask):
    spans, start = [], None
    for i, enabled in enumerate(mask+[False]):
        if enabled and start is None:
            start = i
        if not enabled and start is not None:
            if i-start >= 4:
                spans.append(list(range(start, i)))
            start = None
    return spans

apply(sample('Attack_D', 0.))
origin = point('Hips').copy()
apply(sample('Attack_D', SECONDS))
drift = point('Hips')-origin
anchor = ns['idle_world']['Hips'].translation
raw_poses = []
for i in range(count):
    apply(sample('Attack_D', i/FPS))
    # Remove net travel, retaining the step's within-clip weight transfer.
    move_hips(Vector((anchor.x-origin.x-drift.x*i/(count-1),
                      anchor.y-origin.y-drift.y*i/(count-1), 0)))
    raw_poses.append(ns['snapshot']())

poses = []
for i in range(count):
    # One-frame local smoothing avoids damping the source strike acceleration.
    neighbors = ns['mix'](raw_poses[max(0, i-1)], raw_poses[min(count-1, i+1)], .5)
    poses.append(ns['mix'](raw_poses[i], neighbors, .25))

raw, axes = [], {side: [] for side in SIDES}
for pose in poses:
    apply(pose)
    raw.append(dict(sole=sole_heights(),
        feet={s: point(s+'Foot').copy() for s in SIDES},
        knees={s: point(s+'Leg').copy() for s in SIDES},
        foot_q={s: wm(s+'Foot').to_quaternion() for s in SIDES},
        hands={s: point(s+'Hand').copy() for s in SIDES}))
    for side in SIDES:
        a, b, c = [point(side+p) for p in ['Arm', 'ForeArm', 'Hand']]
        axis = (b-a).cross(c-b)
        axes[side].append((axis.length, wm(side+'ForeArm').to_quaternion().inverted() @ axis.normalized()))

bend_axes = {s: max(axes[s], key=lambda p: p[0])[1] for s in SIDES}
strike_side = max(SIDES, key=lambda s: sum(
    (raw[i]['hands'][s]-raw[i-1]['hands'][s]).length for i in range(12, 40)))
floors = {s: sorted(r['sole'][s] for r in raw)[int(count*.08)] for s in SIDES}
height_offset = .004-statistics.mean(floors.values())
contacts = {}
for side in SIDES:
    velocity = [(raw[min(count-1, i+1)]['feet'][side]-raw[max(0, i-1)]['feet'][side]).xy.length*FPS*.5
                for i in range(count)]
    mask = [r['sole'][side] < floors[side]+.035 and velocity[i] < .45 for i, r in enumerate(raw)]
    # Remove one-frame contact chatter without joining the actual lifted step.
    for i in range(1, count-1):
        if not mask[i] and mask[i-1] and mask[i+1]:
            mask[i] = True
    contacts[side] = segments(mask)

targets = {s: [r['feet'][s]+Vector((0, 0, height_offset)) for r in raw] for s in SIDES}
for side in SIDES:
    for span in contacts[side]:
        center = sum((raw[i]['feet'][side] for i in span), Vector())/len(span)
        for j, i in enumerate(span):
            entering = 1. if span[0] == 0 else smooth((j+1)/6)
            leaving = 1. if span[-1] == count-1 else smooth((len(span)-j)/6)
            weight = entering*leaving
            targets[side][i].x += (center.x-targets[side][i].x)*weight*.8
            targets[side][i].y += (center.y-targets[side][i].y)*weight*.8
            targets[side][i].z += (.004-raw[i]['sole'][side]-height_offset)*weight
    # Foot-only clearance corrects the ankle, never pumps the entire pelvis.
    for i in range(count):
        bottom = raw[i]['sole'][side]+targets[side][i].z-raw[i]['feet'][side].z
        targets[side][i].z += max(0., .003-bottom)

fitted = []
for i, pose in enumerate(poses):
    t = i/FPS
    apply(pose)
    move_hips(Vector((0, 0, height_offset)))
    envelope = ramp(.06, .22, t)*(1-ramp(1.0, 1.45, t))
    for side in SIDES:
        # Keep the striking arm on-time; only the recovery gets wrist follow-through.
        lag_weight = ramp(.62, .76, t)*(1-ramp(1.15, 1.5, t)) if side == strike_side else envelope
        for part, delay, amount in [('ForeArm', .025, .22), ('Hand', .045, .32)]:
            bone = rig.pose.bones[side+part]
            lag = curve_pose(poses, i-delay*FPS)[bone.name].to_quaternion()
            basis = bone.matrix_basis.copy()
            bone.matrix_basis = Matrix.LocRotScale(basis.translation,
                basis.to_quaternion().slerp(lag, amount*lag_weight), basis.to_scale())
        ns['update']()
        q = wm(side+'ForeArm').to_quaternion()
        set_rotation(side+'ForeArm', Quaternion(q @ bend_axes[side], math.radians(3.)*envelope) @ q)
    # Partial compensation keeps the head directed at the opponent with source
    # nod/tilt still present. This is baked facing, not runtime eye tracking.
    ns['gaze'](.68)
    for side in SIDES:
        solve_leg(side, targets[side][i], raw[i]['knees'][side]+Vector((0, 0, height_offset)), raw[i]['foot_q'][side])
    fitted.append(ns['snapshot']())

# Match the existing idle only at the boundaries; preserve the full D strike.
for i in range(count):
    t = i/FPS
    weight = ramp(0., .12, t)*(1-ramp(1.65, SECONDS, t))
    fitted[i] = ns['mix'](ns['idle'], fitted[i], weight)

action = ns['new_action'](NAME, FPS, SECONDS)
previous = {}
for i, pose in enumerate(fitted):
    scene.frame_set(i)
    apply(pose)
    ns['key_pose'](i, previous)
entry = ns['export'](NAME, action, FPS, False,
    ns['metadata']['Attack_D']['source']+'; native UE retarget; original Meshy bind lengths and skin; per-foot support fitting, elbow softness, recovery follow-through and partial forward gaze')
entry.update(revision='AttackD_V12-20260929', contact_seconds=.47, contact_end_seconds=.67,
    recovery_seconds=.35, attack_range_base_cm=145., attack_damage=30., damage_type='physical_melee',
    attack_mode='physical_melee_attack_d', projectiles=False, poison=True, poison_stacks_per_hit=1)
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SpitterZombie_AttackD_V12.blend'))
report = dict(attack=entry, source_interval_seconds=[0., SECONDS], source_play_rate=1.,
    strike_side=strike_side, body_height_offset_cm=round(height_offset*100, 3),
    support_intervals={s: [[span[0]/FPS, span[-1]/FPS] for span in spans] for s, spans in contacts.items()},
    mesh_or_skin_modified=False, source_pack_assets_modified=False, runtime_tested=False,
    preview_rendered=False, movement_assets_modified=False, native_changed=False)
(ROOT/'authoring.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('SPITTER_ATTACK_D_V12_AUTHORED '+json.dumps(report), flush=True)
