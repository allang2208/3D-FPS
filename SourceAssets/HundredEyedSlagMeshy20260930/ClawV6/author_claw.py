"""Adapt the existing ClawC shoulder/elbow motion onto Slag's large right forelimb.

Keeps the V4 bind, geometry, UVs, material, bones and non-target actions.
This is a quadruped adaptation of an existing licensed donor, not a direct mocap import.
"""
import ast, bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
V4 = ROOT / 'HeroHandV4'
V3 = ROOT / 'RuntimeV3'
DELIVERY = OUT / 'Delivery'
(DELIVERY / 'Animations').mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(V4 / 'HundredEyedSlag_HeroHandV4.blend'))
scene = bpy.context.scene
scene.render.fps = 30
scene.render.fps_base = 1
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
mesh = next(o for o in scene.objects if o.type == 'MESH')
rig.animation_data.action = None
for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
scene.frame_set(1)
arm = rig.data
rest = {b.name: b.matrix_local.copy() for b in arm.bones}
inv = {n: m.inverted() for n, m in rest.items()}
spec = json.loads((ROOT / 'AuthoringV1/skeleton_spec.json').read_text())
byname = {row['name']: row for row in spec}
meta = json.loads((ROOT / 'AuthoringV1/source_geometry.json').read_text())
limbs = {}
for key, pad in meta['feet_centres_m'].items():
    kind, side = key.split('.')
    names = [f'{kind}_{part}.{side}' for part in ('upper', 'lower', 'palm')]
    d = {k: Vector(byname[n]['head']) for k, n in zip(('shoulder', 'elbow', 'wrist'), names)}
    d.update(pad=Vector(pad), bones=names, parent=byname[names[0]]['parent'])
    d['a'] = (d['elbow'] - d['shoulder']).length
    d['b'] = (d['wrist'] - d['elbow']).length
    d['axis'] = (d['wrist'] - d['shoulder']).normalized()
    pole = d['elbow'] - d['shoulder']
    pole -= d['axis'] * pole.dot(d['axis'])
    d['pole'] = pole.normalized()
    d['min_reach'] = math.sqrt(d['a']**2 + d['b']**2 + 2*d['a']*d['b']*math.cos(math.radians(112)))
    d['max_reach'] = math.sqrt(d['a']**2 + d['b']**2 + 2*d['a']*d['b']*math.cos(math.radians(8)))
    d['toes'] = [row['name'] for row in spec if row['name'].startswith(kind+'_digit_') and row['name'].endswith('.'+side)]
    limbs[key] = d
d = limbs['front.R']
namespace = dict(np=np, math=math, Matrix=Matrix, Vector=Vector, Quaternion=Quaternion,
                 arm=arm, rest=rest, inv=inv, limbs=limbs, keys=list(limbs))
for filename, wanted in [(V3/'author_runtime.py', {'smooth', 'step', 'rotation', 'around', 'track', 'aim', 'solve'}),
                         (V4/'author_hero_hand.py', {'core', 'support_bones'})]:
    for node in ast.parse(filename.read_text()).body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(filename), 'exec'), namespace)
smooth, step, rotation, around, track, aim, solve, core, supports = [namespace[n] for n in
    ('smooth', 'step', 'rotation', 'around', 'track', 'aim', 'solve', 'core', 'support_bones')]

# Rebuild only the right limb/attachment from the original geodesic region weights.
# The six V4 helpers remain neutral and retain their original bind and parent chain.
v = np.empty(len(mesh.data.vertices)*3, dtype=np.float32)
mesh.data.vertices.foreach_get('co', v)
v = v.reshape(-1, 3)
old_skin = np.load(V4/'skin_weights.npz')
base_skin = np.load(V3/'skin_weights.npz')
names = [str(n) for n in old_skin['bone_names']]
rows = np.arange(len(v))[:, None]
old = np.zeros((len(v), len(names)), dtype=np.float32)
old[rows, old_skin['indices']] = old_skin['weights']
base = np.zeros_like(old)
mapped = np.asarray([names.index(str(n)) for n in base_skin['bone_names']])
base[rows, mapped[base_skin['indices']]] = base_skin['weights']
def col(name): return names.index(name)
helpers = ['front_shoulder.R', 'front_upper_twist.R', 'front_lower_twist_01.R',
           'front_lower_twist_02.R', 'front_elbow_support.R', 'front_wrist_support.R']
right_base = base[:, [col(n) for n in d['bones']]].sum(axis=1)
right_old = old[:, [col(n) for n in d['bones'] + helpers]].sum(axis=1)
shoulder_dist2 = ((v - np.asarray(d['shoulder']))**2).sum(axis=1)
region = (right_base > .015) | ((shoulder_dist2 < .18**2) & (right_old > .06) & (v[:, 1] < -.16))
w = old.copy()
w[region] = base[region]

def projected(a, b):
    a, axis = np.asarray(a), np.asarray(b)-np.asarray(a)
    return np.clip(((v-a)*axis).sum(axis=1)/(axis@axis), 0, 1)
tu = projected(d['shoulder'], d['elbow'])
tl = projected(d['elbow'], d['wrist'])
def transfer(source, destination, field):
    part = w[:, col(source)] * field * region
    w[:, col(source)] -= part
    w[:, col(destination)] += part
transfer('front_upper.R', 'front_upper_twist.R', .20*smooth(.20, .75, tu)*(1-smooth(.88, 1., tu)))
lower = w[:, col('front_lower.R')].copy()
f1 = .22*smooth(.12, .30, tl)*(1-smooth(.48, .72, tl))*region
f2 = .26*smooth(.42, .65, tl)*(1-smooth(.87, 1., tl))*region
w[:, col('front_lower.R')] -= lower*(f1+f2)
w[:, col('front_lower_twist_01.R')] += lower*f1
w[:, col('front_lower_twist_02.R')] += lower*f2
for centre, helper, influenced, radius, maximum in [
    (d['elbow'], 'front_elbow_support.R', d['bones'][:2]+['front_upper_twist.R', 'front_lower_twist_01.R'], .065, .28),
    (d['wrist'], 'front_wrist_support.R', d['bones'][1:]+['front_lower_twist_01.R', 'front_lower_twist_02.R'], .045, .22)]:
    field = maximum*np.exp(-((v-np.asarray(centre))**2).sum(axis=1)/(2*radius**2))
    for n in influenced: transfer(n, helper, field)
scapula = .28*np.exp(-shoulder_dist2/(2*.105**2))*smooth(.12, .25, -v[:, 1])
for n in ('chest', 'front_upper.R', 'spine'): transfer(n, 'front_shoulder.R', scapula)
# Keep the existing claw-tip influence instead of transferring the whole palm to fingers.
toe_old = old[:, [col(n) for n in d['toes']]]
toe_total = toe_old.sum(axis=1)
amount = np.minimum(toe_total, w[:, col('front_palm.R')])*region
w[:, col('front_palm.R')] -= amount
for i, name in enumerate(d['toes']):
    w[region, col(name)] = (amount*toe_old[:, i]/np.maximum(toe_total, 1e-10))[region]
new_indices = np.argpartition(w[region], -4, axis=1)[:, -4:]
new_values = np.take_along_axis(w[region], new_indices, axis=1)
new_values /= np.maximum(new_values.sum(axis=1, keepdims=True), 1e-10)
indices = old_skin['indices'].copy()
values = old_skin['weights'].copy()
indices[region], values[region] = new_indices, new_values
mesh.vertex_groups.clear()
for i, name in enumerate(names):
    group = mesh.vertex_groups.new(name=name)
    rr, cc = np.nonzero(indices == i)
    for vertex, slot in zip(rr, cc):
        value = float(values[vertex, slot])
        if value > 1e-6: group.add([int(vertex)], value, 'REPLACE')
for modifier in mesh.modifiers:
    if modifier.type == 'ARMATURE': modifier.use_deform_preserve_volume = False
np.savez_compressed(OUT/'skin_weights.npz', bone_names=np.asarray(names), indices=indices, weights=values)
print('CLAW_V6_RIGHT_LIMB_WEIGHTS_AUTHORED vertices=' + str(int(region.sum())), flush=True)

donors = json.loads((OUT/'donor_motion.json').read_text())
donor = donors['C']
motion = [{n: Matrix(m) for n, m in frame.items()} for frame in donor['frames']]
def body_frame(pose):
    right = (pose['RightArm'].translation-pose['LeftArm'].translation).normalized()
    up = ((pose['RightArm'].translation+pose['LeftArm'].translation)*.5-pose['Hips'].translation).normalized()
    up = (up-right*up.dot(right)).normalized()
    forward = up.cross(right).normalized()
    return Matrix((forward, right, up)).transposed()
canonical = Matrix((Vector((1,0,0)), Vector((0,-1,0)), Vector((0,0,1)))).transposed()

def sample_source(time):
    at = max(0., min(30., time*60.))
    a, b = int(at), min(30, int(at)+1)
    return {n: motion[a][n].lerp(motion[b][n], at-a) for n in motion[a]}

# Match the donor's contact plane to Slag's forward strike lane. Its asymmetrical
# shoulder proportions otherwise turn the useful claw stroke far out to the side.
# A rigid yaw preserves segment lengths and the donor elbow angle; no hand IK pull.
contact_source = sample_source(11/60)
contact_mapping = canonical @ body_frame(contact_source).inverted()
contact_upper = (contact_mapping @ (contact_source['RightForeArm'].translation-contact_source['RightArm'].translation)).normalized()
contact_lower = (contact_mapping @ (contact_source['RightHand'].translation-contact_source['RightForeArm'].translation)).normalized()
contact_reach = contact_upper*d['a']+contact_lower*d['b']
contact_yaw = math.atan2(.16,1.)-math.atan2(contact_reach.y,contact_reach.x)
contact_alignment = Quaternion((0,0,1),contact_yaw).to_matrix()

def source_time(t):
    return track(t, [(0,(0,0,0)), (.40,(0,0,0)), (.54,(.065,0,0)),
                     (.64,(11/60,0,0)), (.73,(.30,0,0)), (.96,(.50,0,0)), (1.4,(.50,0,0))]).x

def joint_orientation(bone, direction):
    original = (arm.bones[bone].tail_local-arm.bones[bone].head_local).normalized()
    return original.rotation_difference(direction.normalized()) @ rest[bone].to_quaternion()

def pose(t):
    load = track(t, [(0,(0,0,0)), (.34,(1,0,0)), (.54,(.85,0,0)),
                     (.73,(-.5,0,0)), (.98,(-.2,0,0)), (1.4,(0,0,0))]).x
    shift = track(t, [(0,(0,0,0)), (.34,(-.025,.028,-.018)),
                      (.64,(.025,.025,-.025)), (.90,(.018,.01,-.014)), (1.4,(0,0,0))])
    target = {n: m.copy() for n, m in rest.items()}
    G = around((0,0,.66), shift, rotation(0,.020*load,-.045*load))
    target.update(core(G, rotation(0,.012,.025*load), rotation(0,-.018,-.035*load),
                       rotation(-.020*load,-.025,-.115*load), rotation(0,0,-.020*load)))
    parents = {key: target[limb['parent']] @ inv[limb['parent']] for key, limb in limbs.items()}
    # The other three limbs own support and remain on their original contact pads.
    lo, hi = -.14, .12
    for key, limb in limbs.items():
        if key == 'front.R': continue
        sh = parents[key] @ limb['shoulder']
        wr = limb['pad'] + limb['wrist']-limb['pad']
        horizontal, vertical = (sh-wr).to_2d().length, sh.z-wr.z
        lo = max(lo, math.sqrt(max(0., limb['min_reach']**2-horizontal**2))-vertical)
        hi = min(hi, math.sqrt(max(0., limb['max_reach']**2-horizontal**2))-vertical)
    dz = max(lo, min(0., hi)) if lo <= hi else min(0., hi)
    for n in target:
        if n != 'root': target[n].translation.z += dz
    for parent in parents.values(): parent.translation.z += dz
    for key, limb in limbs.items():
        if key == 'front.R': continue
        sh, elbow, wrist, _ = solve(limb, parents[key], limb['pad'], Quaternion())
        upper, lower, palm = limb['bones']
        target[upper] = aim(upper, sh, elbow)
        target[lower] = aim(lower, elbow, wrist)
        target[palm] = Matrix.Translation(wrist) @ rest[palm].to_3x3().to_4x4()
        for toe in limb['toes']: target[toe] = target[palm] @ inv[palm] @ rest[toe]

    source = sample_source(source_time(t))
    frame = body_frame(source)
    chest_delta = target['chest'].to_quaternion() @ rest['chest'].to_quaternion().inverted()
    mapping = chest_delta.to_matrix() @ contact_alignment @ canonical @ frame.inverted()
    upper_dir = (mapping @ (source['RightForeArm'].translation-source['RightArm'].translation)).normalized()
    lower_dir = (mapping @ (source['RightHand'].translation-source['RightForeArm'].translation)).normalized()
    bend = upper_dir.angle(lower_dir)
    if bend > math.radians(105):
        axis = upper_dir.cross(lower_dir).normalized()
        lower_dir = Quaternion(axis, math.radians(105)) @ upper_dir
    blend = float(smooth(.025,.34,t)*(1-smooth(.96,1.4,t)))
    upper_rest = chest_delta @ (d['elbow']-d['shoulder']).normalized()
    lower_rest = chest_delta @ (d['wrist']-d['elbow']).normalized()
    upper_q = joint_orientation('front_upper.R', upper_rest).slerp(joint_orientation('front_upper.R', upper_dir), blend)
    lower_q = joint_orientation('front_lower.R', lower_rest).slerp(joint_orientation('front_lower.R', lower_dir), blend)
    shoulder = parents['front.R'] @ d['shoulder']
    scapula = chest_delta @ Vector((.012*blend, -.014*blend, .018*blend))
    shoulder += scapula
    upper_dir = upper_q @ Vector((0,1,0))
    lower_dir = lower_q @ Vector((0,1,0))
    elbow = shoulder+upper_dir*d['a']
    wrist = elbow+lower_dir*d['b']
    target['front_upper.R'] = Matrix.LocRotScale(shoulder, upper_q, Vector((1,1,1)))
    target['front_lower.R'] = Matrix.LocRotScale(elbow, lower_q, Vector((1,1,1)))
    lower_delta = lower_q @ rest['front_lower.R'].to_quaternion().inverted()
    flex = track(t, [(0,(0,0,0)),(.34,(.20,0,0)),(.54,(.08,0,0)),
                     (.64,(-.16,0,0)),(.80,(-.06,0,0)),(1.05,(.08,0,0)),(1.4,(0,0,0))]).x
    palm_q = lower_delta @ rest['front_palm.R'].to_quaternion() @ Quaternion((1,0,0),flex)
    target['front_palm.R'] = Matrix.LocRotScale(wrist,palm_q,Vector((1,1,1)))
    for toe in d['toes']:
        m = target['front_palm.R'] @ inv['front_palm.R'] @ rest[toe]
        q = m.to_quaternion() @ Quaternion((0,1,0), .16*blend)
        target[toe] = Matrix.LocRotScale(m.translation,q,Vector((1,1,1)))
    target['ash_origin'] = target['front_plate'] @ inv['front_plate'] @ rest['ash_origin']
    target['attack_origin'] = target['front_palm.R'] @ inv['front_palm.R'] @ rest['attack_origin']
    supports(target)
    # Let the attachment cap follow part of the upper-arm swing instead of staying rigid.
    upper_delta = upper_q @ rest['front_upper.R'].to_quaternion().inverted()
    if chest_delta.dot(upper_delta) < 0: upper_delta.negate()
    scapula_q = chest_delta.slerp(upper_delta,.22) @ rest['front_shoulder.R'].to_quaternion()
    target['front_shoulder.R'] = Matrix.LocRotScale(shoulder,scapula_q,Vector((1,1,1)))
    return target

contract = next(dict(c) for c in json.loads((V4/'animation_contract.json').read_text())['actions'] if c['name']=='AttackSweep_R')
contract.update(action='A_HundredEyedSlag_AttackSweep_R_V6', file='Animations/A_HundredEyedSlag_AttackSweep_R_V6.fbx',
                intent='Lift the large right arm, forward/down claw strike, return to the contact pad',
                donor_role='ClawC', donor_source=str(donor['file']), donor_action=donor['action'])
action = bpy.data.actions.new(contract['action'])
action.use_fake_user = True
rig.animation_data.action = action
previous = {}
palm_positions = []
for f in range(1,44):
    target = pose((f-1)/30.)
    palm_positions.append(list(target['front_palm.R'].translation))
    for bone in arm.bones:
        matrix = inv[bone.name] @ rest[bone.parent.name] @ target[bone.parent.name].inverted() @ target[bone.name] if bone.parent else inv[bone.name] @ target[bone.name]
        pb = rig.pose.bones[bone.name]
        pb.rotation_mode = 'QUATERNION'
        pb.matrix_basis = matrix
        if bone.name in previous and pb.rotation_quaternion.dot(previous[bone.name]) < 0: pb.rotation_quaternion.negate()
        previous[bone.name] = pb.rotation_quaternion.copy()
        pb.scale = (1,1,1)
        for channel in ('location','rotation_quaternion','scale'): pb.keyframe_insert(channel,frame=f)
    if not rig.animation_data.action_slot: rig.animation_data.action_slot = action.slots[0]
for curve in action.layers[0].strips[0].channelbag(action.slots[0]).fcurves:
    for point in curve.keyframe_points: point.interpolation = 'LINEAR'
rig.animation_data.action = None
for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
scene.frame_set(1)
mesh.name = 'SK_HundredEyedSlag_ClawV6'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_ClawV6.blend'))
options = dict(use_selection=True, add_leaf_bones=False, use_armature_deform_only=False,
    axis_forward='-Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
    bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_use_all_bones=True,
    bake_anim_force_startend_keying=True, bake_anim_step=1., bake_anim_simplify_factor=0.)
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True); mesh.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(DELIVERY/'SK_HundredEyedSlag_ClawV6.fbx'), object_types={'ARMATURE','MESH'},
    bake_anim=False, use_mesh_modifiers=False, mesh_smooth_type='OFF', path_mode='AUTO', embed_textures=False, **options)
mesh.select_set(False)
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_end = 43
scene.frame_set(1)
bpy.ops.export_scene.fbx(filepath=str(DELIVERY/'Animations'/Path(contract['file']).name),object_types={'ARMATURE'},bake_anim=True,**options)
(OUT/'animation_contract.json').write_text(json.dumps({'actions':[contract], 'targeted_roles':['AttackSweep_R'],
    'bone_count':len(arm.bones), 'max_influences':4, 'rest_and_hierarchy_preserved':True,
    'non_target_animation_keys_preserved':True},indent=2))
p = np.asarray(palm_positions)
(OUT/'authoring_receipt.json').write_text(json.dumps({'revision':'ClawV6', 'donor':'existing Mutant3 ClawC / licensed Khaimera',
    'adaptation':'lift entry, source shoulder/elbow directions, quadruped supports, limited wrist flex, return to pad',
    'authored_weight_vertices':int(region.sum()), 'upper_twist_weight_limit':.20, 'elbow_support_weight_limit':.28,
    'wrist_support_weight_limit':.22, 'right_palm_bounds_cm':(np.asarray([p.min(axis=0),p.max(axis=0)])*100).tolist(),
    'strike_lane_yaw_degrees':math.degrees(contact_yaw),
    'active_palm_path_cm':(p[16:23]*100).tolist(),
    'game_triangles':len(mesh.data.polygons), 'bone_count':len(arm.bones), 'new_bones':0,
    'runtime_tested':False, 'preview_rendered':False},indent=2))
print('CLAW_V6_AUTHORED_AND_EXPORTED ' + json.dumps((p.max(axis=0)*100).tolist()),flush=True)
