"""Author five M27 clips from native arm chains, without a prescribed blade arc.

This is production authoring/export, not a render or acceptance test.
"""
from pathlib import Path
import json
import math
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

BASE = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
OUT = BASE / 'ArmChainV15/Delivery'
OUT.mkdir(parents=True, exist_ok=True)
BEAST = json.loads((BASE / 'Beast06V1/native_poses.json').read_text())['clips']
POUNCE = json.loads((BASE / 'PounceV5/native_pounce_poses.json').read_text())['clips']
bpy.ops.wm.open_mainfile(filepath=str(BASE / 'PounceV11/Delivery/MantisM27_PounceV11.blend'))
scene = bpy.context.scene
scene.render.fps = FPS = 60
scene.render.fps_base = 1.
rig = next(obj for obj in scene.objects if obj.type == 'ARMATURE')
for track in rig.animation_data.nla_tracks:
    track.mute = True
names = [bone.name for bone in rig.data.bones]
parent = {bone.name: bone.parent.name if bone.parent else None for bone in rig.data.bones}
rest = {bone.name: bone.matrix_local.copy() for bone in rig.data.bones}
local = {n: rest[parent[n]].inverted() @ rest[n] if parent[n] else rest[n].copy() for n in names}
reflection = Matrix.Diagonal((1., -1., 1.))
# The rigid blade is a branch of lowerarm, not a hand-held object. Keep its
# mount fixed. Hand motion can be retained without inventing a blade wrist.
fixed_helper = lambda n: n.startswith(('blade_', 'ball_', 'headfront', 'head_tip', 'chain_', 'membrane_'))
upper_names = {n for n in names if n.startswith(('spine_', 'neck_', 'clavicle_', 'upperarm_', 'lowerarm_', 'hand_')) or n == 'head'}

def smooth(x):
    x = min(1., max(0., x))
    return x*x*(3.-2.*x)

def curve(t, keys):
    xs = np.asarray([k[0] for k in keys]); ys = np.asarray([k[1] for k in keys])
    if t <= xs[0]: return float(ys[0])
    if t >= xs[-1]: return float(ys[-1])
    sec = np.diff(ys)/np.diff(xs); slopes = np.zeros(len(xs))
    for i in range(1, len(xs)-1):
        if sec[i-1]*sec[i] > 0:
            h0, h1 = xs[i]-xs[i-1], xs[i+1]-xs[i]
            slopes[i] = 3*(h0+h1)/((2*h1+h0)/sec[i-1]+(h1+2*h0)/sec[i])
    i = int(np.searchsorted(xs, t)-1); h = xs[i+1]-xs[i]; x = (t-xs[i])/h
    return float((2*x**3-3*x*x+1)*ys[i]+(x**3-2*x*x+x)*h*slopes[i]
                 +(-2*x**3+3*x*x)*ys[i+1]+(x**3-x*x)*h*slopes[i+1])

def activate(action):
    rig.animation_data.action = action
    if action.slots: rig.animation_data.action_slot = action.slots[0]

def capture(action_name, count):
    activate(bpy.data.actions[action_name]); poses = []
    for i in range(count):
        scene.frame_set(i+1)
        poses.append({n: rig.pose.bones[n].matrix.copy() for n in names})
    return poses

idle = capture('A_M27_Idle_BindingV2', 1)[0]
idle_local = {n: idle[parent[n]].inverted() @ idle[n] if parent[n] else idle[n].copy() for n in names}
pounce_base = {role: capture('A_M27_'+role+'_PounceV11', round(info['seconds']*FPS)+1)
               for role, info in POUNCE.items()}
# Load only the established melee guard; no V14 attack tracks are reused.
with bpy.data.libraries.load(str(BASE/'ClawV14/Delivery/MantisM27_ClawV14.blend'), link=False) as (src, dst):
    dst.actions = ['A_M27_LeftSlash_ClawV14']
guard = capture(dst.actions[0].name, 1)[0]
guard_local = {n: guard[parent[n]].inverted() @ guard[n] if parent[n] else guard[n].copy() for n in names}

def build(rotations, hip):
    out = {}
    for n in names:
        rel = Matrix.LocRotScale(local[n].translation, rotations[n], Vector((1., 1., 1.)))
        out[n] = out[parent[n]] @ rel if parent[n] else rel
        if n == 'pelvis': out[n].translation = hip
    return out

def rebuild(pose, changes):
    out = {}
    for n in names:
        rel = pose[parent[n]].inverted() @ pose[n] if parent[n] else pose[n].copy()
        out[n] = out[parent[n]] @ rel if parent[n] else rel
        if n in changes:
            p = out[n].translation.copy()
            out[n] = changes[n].to_matrix().to_4x4(); out[n].translation = p
    return out

def native(clip):
    out = []
    for frame in clip['frames']:
        world = {}
        for n in names:
            m = world[parent[n]] @ local[n] if parent[n] else local[n].copy()
            if not fixed_helper(n):
                delta = Quaternion(frame[n]['q']) @ Quaternion(clip['reference'][n]['q']).inverted()
                q = (reflection @ delta.to_matrix() @ reflection).to_quaternion() @ rest[n].to_quaternion()
                p = m.translation.copy(); m = q.to_matrix().to_4x4(); m.translation = p
            if n == 'pelvis':
                m.translation = rest[n].translation + reflection @ (Vector(frame[n]['p'])-Vector(clip['reference'][n]['p']))
            world[n] = m
        q = {n: (world[parent[n]].inverted() @ world[n] if parent[n] else world[n]).to_quaternion() for n in names}
        if out:
            for n in names:
                if q[n].dot(out[-1][0][n]) < 0: q[n].negate()
        out.append((q, world['pelvis'].translation.copy()))
    return out

native_pounce = {role: native(info) for role, info in POUNCE.items()}
native_melee = {role: native(BEAST[source]) for role, source in [('LeftSlash', 'Attack1'), ('RightSlash', 'Attack6')]}

def sample(frames, t):
    f = min(len(frames)-1., max(0., t*FPS)); i = int(f); j = min(i+1, len(frames)-1)
    return ({n: frames[i][0][n].slerp(frames[j][0][n], f-i) for n in names}, frames[i][1].lerp(frames[j][1], f-i))

# Actual rigid blade surface is represented by short bounding spheres plus
# vertices for ground clearance. No fixed left/right half-space or target arc.
weights = np.load(BASE/'BindingV2/binding_weights_v2.npz')
topology = np.load(BASE/'BindingV2/connected_source.npz')
p = topology['points']; points = np.column_stack((p[:,0], -p[:,2], p[:,1]-p[:,1].min()))*100.
wi = {n:i for i,n in enumerate(weights['names'])}
cages = {}; spheres = {}; signed_axes = {}; feet = {}; anchors = {}; floor = {}
for side in ['l', 'r']:
    n = 'blade_root_'+side; cloud = points[weights['weights'][:,wi[n]] > .999]
    normal = Vector(np.linalg.svd(cloud-cloud.mean(0), full_matrices=False)[2][-1])
    chord = rest['blade_tip_'+side].translation-rest[n].translation
    chord = (chord-normal*chord.dot(normal)).normalized(); bend = normal.cross(chord).normalized()
    if bend.dot(rest['blade_mid_'+side].translation-rest[n].translation) < 0: bend.negate()
    signed_axes[side] = {'chord': list(chord), 'convex_bulge': list(bend), 'cutting_side': list(-bend)}
    inv = np.asarray(rest[n].inverted()); cloud = cloud @ inv[:3,:3].T + inv[:3,3]
    axis = np.linalg.svd(cloud-cloud.mean(0), full_matrices=False)[2][0]; distance = cloud @ axis
    bins = np.minimum(19, ((distance-distance.min())/np.ptp(distance)*20).astype(int))
    centers = []; radii = []; cage = []
    for k in range(20):
        section = cloud[bins == k]
        if not len(section): continue
        lo, hi = section.min(0), section.max(0); center = (lo+hi)*.5
        centers.append(center); radii.append(float(np.linalg.norm(section-center, axis=1).max()))
        cage.extend((x,y,z) for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]])
    cages[side] = np.asarray(cage); spheres[side] = (np.asarray(centers), np.asarray(radii))
    n = 'foot_'+side; cloud = points[weights['weights'][:,wi[n]] > .999]
    inv = np.asarray(rest[n].inverted()); feet[side] = cloud @ inv[:3,:3].T + inv[:3,3]
    matrix = np.asarray(guard[n]); world = feet[side] @ matrix[:3,:3].T + matrix[:3,3]
    chosen = (world[:,1] <= np.quantile(world[:,1], .12)) & (world[:,2] <= np.quantile(world[:,2], .40))
    if not np.any(chosen): chosen = world[:,1] <= np.quantile(world[:,1], .12)
    pivot = Vector(world[chosen].mean(0)); anchors[side] = (pivot, guard[n].inverted() @ pivot)
    floor[side] = float(world[:,2].min())

def support_feet(pose, t, active):
    rotations = {}
    for side in ['l', 'r']:
        rear = side != active
        heel = curve(t, [(0.,0.),(.12,0.),(.24,17. if rear else 0.),(.33,19. if rear else 0.),(.43,12. if rear else 0.),(.59,0.),(.65,0.)])
        yaw = curve(t, [(0.,0.),(.14,0.),(.29,11. if rear else -4.),(.40,9. if rear else -3.),(.61,0.),(.65,0.)])
        if active == 'r': yaw = -yaw
        a,b,c = [part+'_'+side for part in ['thigh','calf','foot']]
        q = Quaternion((0,0,1), math.radians(yaw)) @ Quaternion((1,0,0), math.radians(heel)) @ guard[c].to_quaternion()
        pivot, offset = anchors[side]; target = pivot-q@offset
        target.z = floor[side]-float((feet[side] @ np.asarray(q.to_matrix()).T)[:,2].min())
        hip = pose[a].translation; direction = target-hip; axis = direction.normalized()
        l1 = (rest[b].translation-rest[a].translation).length; l2 = (rest[c].translation-rest[b].translation).length
        distance = max(abs(l1-l2)+.01, min(direction.length, l1+l2-.01))
        pole = pose[b].translation-hip; pole -= axis*pole.dot(axis)
        if pole.length < .01:
            pole = guard[b].translation-guard[a].translation; pole -= axis*pole.dot(axis)
        pole.normalize(); along = (l1*l1-l2*l2+distance*distance)/(2*distance)
        knee = hip+axis*along+pole*math.sqrt(max(0., l1*l1-along*along))
        rotations[a] = (pose[b].translation-hip).rotation_difference(knee-hip) @ pose[a].to_quaternion()
        rotations[b] = (pose[c].translation-pose[b].translation).rotation_difference(target-knee) @ pose[b].to_quaternion()
        rotations[c] = q
    return rebuild(pose, rotations)

CLOCKS = {
    'LeftSlash': [(0.,0.),(.10,.08),(.18,.267),(.265,.417),(.34,.48),(.44,.55),(.65,2/3)],
    'RightSlash': [(0.,0.),(.10,.025),(.175,.06),(.26,.206),(.32,.29),(.425,.41),(.54,.57),(.65,2/3)],
}

def melee_pose(role, t):
    source, hip = sample(native_melee[role], curve(t, CLOCKS[role]))
    initial, origin = native_melee[role][0]
    amount = smooth(t/.08)*(1.-smooth((t-.49)/.16))
    # A single neutral calibration, then full source rotation deltas. There is
    # no per-joint attenuation or blade-orientation replacement during the cut.
    rotations = {n: guard_local[n].to_quaternion() @ Quaternion().slerp(initial[n].inverted() @ source[n], amount)
                 if not fixed_helper(n) else guard_local[n].to_quaternion() for n in names}
    pose = build(rotations, guard['pelvis'].translation+(hip-origin)*(.65*amount))
    return support_feet(pose, t, 'l' if role == 'LeftSlash' else 'r')

def pounce_pose(role, index):
    t = index/FPS; pose = pounce_base[role][index]
    source = native_pounce[role][index][0]; initial = native_pounce['PounceWindup'][0][0]
    amount = smooth(t/.14) if role == 'PounceWindup' else 1.-smooth((t-.62)/.18) if role == 'PounceLand' else 1.
    rotations = {n: (pose[parent[n]].inverted() @ pose[n] if parent[n] else pose[n]).to_quaternion() for n in names}
    for n in upper_names:
        rotations[n] = idle_local[n].to_quaternion() @ Quaternion().slerp(initial[n].inverted() @ source[n], amount)
    return build(rotations, pose['pelvis'].translation)

def cap(q, degrees):
    if q.w < 0: q.negate()
    angle = q.angle
    return Quaternion().slerp(q, min(1., math.radians(degrees)/max(1.e-8, angle)))

def clearance_envelope(role, t):
    if role == 'PounceWindup': return smooth(t/.10)
    if role == 'PounceLand': return 1.-smooth((t-.60)/.20)
    if role in CLOCKS: return smooth(t/.08)*(1.-smooth((t-.49)/.16))
    return 1.

def fit(pose, role, t, duration, seeds=None):
    turns = {s: seeds[s].copy() if seeds else Quaternion() for s in ['l','r']}
    # Blend the small clearance adaptation into the preserved guard endpoints.
    envelope = clearance_envelope(role, t)
    limit = 24.*envelope
    shoulders = {s: np.asarray(pose['upperarm_'+s].translation) for s in ['l','r']}
    original = {}; vertices = {}
    for s in ['l','r']:
        m = np.asarray(pose['blade_root_'+s]); centers, radii = spheres[s]
        original[s] = centers @ m[:3,:3].T+m[:3,3]-shoulders[s]
        vertices[s] = cages[s] @ m[:3,:3].T+m[:3,3]-shoulders[s]
    chest_a = np.asarray(pose['spine_01'].translation); chest_b = np.asarray(pose['neck_01'].translation)
    chest_axis = chest_b-chest_a; chest_length2 = max(.01, float(chest_axis@chest_axis))
    def move(side, point, normal, gap):
        lever = Vector(point-shoulders[side]); axis = lever.cross(Vector(normal))
        if axis.length < 1.e-5: return
        amount = min(math.radians(3.), gap/max(1.,axis.length)*.70)
        turns[side] = cap(Quaternion(axis.normalized(), amount) @ turns[side], limit)
    for _ in range(18):
        centers = {s: original[s] @ np.asarray(turns[s].to_matrix()).T+shoulders[s] for s in ['l','r']}
        for s in ['l','r']:
            if role != 'PounceFlight':
                points = vertices[s] @ np.asarray(turns[s].to_matrix()).T+shoulders[s]
                low = points[np.argmin(points[:,2])]
                if low[2] < 6.: move(s, low, np.array([0.,0.,1.]), 6.-low[2])
            # A narrow torso capsule, not an infinite plane blocking every
            # cross-body slash. The rigid scythe may pass in front of the body.
            alpha = np.clip(((centers[s]-chest_a)@chest_axis)/chest_length2, 0., 1.)
            closest = chest_a+alpha[:,None]*chest_axis
            delta = centers[s]-closest; lengths = np.linalg.norm(delta, axis=1)
            gaps = 17.+spheres[s][1]-lengths; k = int(np.argmax(gaps))
            if gaps[k] > 0 and lengths[k] > .01: move(s, centers[s][k], delta[k]/lengths[k], float(gaps[k]))
        centers = {s: original[s] @ np.asarray(turns[s].to_matrix()).T+shoulders[s] for s in ['l','r']}
        delta = centers['l'][:,None,:]-centers['r'][None,:,:]; lengths = np.linalg.norm(delta, axis=2)
        gaps = spheres['l'][1][:,None]+spheres['r'][1][None,:]+2.-lengths
        i,j = np.unravel_index(np.argmax(gaps), gaps.shape)
        if gaps[i,j] > 0 and lengths[i,j] > .01:
            normal = delta[i,j]/lengths[i,j]; gap = float(gaps[i,j])*.5
            move('l', centers['l'][i], normal, gap); move('r', centers['r'][j], -normal, gap)
    return turns

roles = [('LeftSlash',.65),('RightSlash',.65),('PounceWindup',.60),('PounceFlight',.65),('PounceLand',.80)]
authored = {}
for role, duration in roles:
    frames = []
    for i in range(round(duration*FPS)+1):
        pose = melee_pose(role, i/FPS) if role in CLOCKS else pounce_pose(role, i)
        frames.append({'pose': pose, 'time': i/FPS, 'limit': 24.*clearance_envelope(role,i/FPS),
                       'turns': fit(pose,role,i/FPS,duration)})
    authored[role] = frames

# Smooth only clearance corrections. Native elbow and shoulder motion is never
# filtered toward a synthetic blade target. Pounce corrections share boundaries.
groups = [authored['LeftSlash'], authored['RightSlash'], sum([authored[r] for r,_ in roles[2:]], [])]
for group in groups:
    for side in ['l','r']:
        original = [frame['turns'][side].copy() for frame in group]
        for i, frame in enumerate(group):
            center = original[i]; value = np.zeros(4)
            for step, weight in [(-2,1),(-1,4),(0,6),(1,4),(2,1)]:
                q = original[min(len(group)-1,max(0,i+step))].copy()
                if q.dot(center) < 0: q.negate()
                value += np.asarray(q)*weight
            frame['turns'][side] = cap(Quaternion(value).normalized(), frame['limit'])

report = {'revision':'ArmChainV15','status':'candidate_only','fps':FPS,'mesh_revision':'BindingV2','clips':{},
    'scope':'Both independent ground attacks and all three pounce arm phases',
    'design':'Full native local rotation deltas from one time per pose, neutral calibrated to M27; no prescribed blade orientation or half-space lanes',
    'melee_clocks':CLOCKS,'melee_contact_window_seconds':[.25,.30],
    'rigid_blade_parent':{s:parent['blade_root_'+s] for s in ['l','r']},'signed_blade_axes':signed_axes,
    'clearance_authoring':{'maximum_arm_correction_degrees':24.,'floor_cm':6.,'torso_capsule_radius_cm':17.,'blade_pair_margin_cm':2.,
        'scope':'Bounded production fitting only; no guarantee of collision-free frames or runtime acceptance'},
    'pelvis_translation_gain_melee':.65,'native_rotation_delta_gain':1.,
    'pounce_lower_body_source':'PounceV11','runtime_tested':False,'offline_validated':False,'rendered':False,'native_code_changed':False,
    'source_license':'Installed Fab Beast06 and local Epic Paragon Khaimera / Mutant3 derivatives; retain original provenance; not CC0'}
for role, duration in roles:
    action = bpy.data.actions.new('A_M27_'+role+'_ArmChainV15'); action.use_fake_user = True; activate(action)
    scene.frame_start,scene.frame_end = 1,len(authored[role]); previous = {}
    for i, frame in enumerate(authored[role]):
        pose = frame['pose']; changes = { 'upperarm_'+s:frame['turns'][s] @ pose['upperarm_'+s].to_quaternion() for s in ['l','r']}
        pose = rebuild(pose, changes)
        for n in names:
            rel = pose[parent[n]].inverted() @ pose[n] if parent[n] else pose[n]
            basis = local[n].inverted() @ rel; q = basis.to_quaternion()
            if n in previous and previous[n].dot(q) < 0: q.negate()
            previous[n] = q.copy(); pb = rig.pose.bones[n]
            pb.location = basis.translation; pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=q; pb.scale=basis.to_scale()
            for channel in ['location','rotation_quaternion','scale']: pb.keyframe_insert(channel,frame=i+1,group=n)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fcurve in bag.fcurves:
                    for key in fcurve.keyframe_points: key.interpolation='LINEAR'
    scene.frame_set(1); bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
    filename=action.name+'.fbx'
    bpy.ops.export_scene.fbx(filepath=str(OUT/filename),use_selection=True,object_types={'ARMATURE'},apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',global_scale=1.,axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0.)
    donor = BEAST['Attack1' if role=='LeftSlash' else 'Attack6'] if role in CLOCKS else POUNCE[role]
    report['clips'][role]={'file':filename,'seconds':duration,'frames':len(authored[role]),'source':donor['source'],
        'raw_asset':donor.get('raw_asset',donor.get('raw'))}
    print('M27_ARM_CHAIN_V15_EXPORTED '+role,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MantisM27_ArmChainV15.blend'))
(OUT/'motion_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M27_ARM_CHAIN_V15_AUTHORED',flush=True)
