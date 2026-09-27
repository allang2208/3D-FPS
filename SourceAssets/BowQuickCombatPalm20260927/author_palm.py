"""V5 bow quick combat: native V7 open palm drives the upper riser.

The existing source clock, horizontal bow path and left grasp are unchanged.
Palm-push semantics follow CastingPalmPush V9; no Manny bone transforms are
copied into the native bow rig. Run with Blender in background.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector

P = Path(__file__).parent
ROOT = P.parents[1]
PREVIOUS = P.parent / 'BowQuickCombatContact20260927'
previous_script = PREVIOUS / 'generated_contact_v4.py'
previous = {'__file__': str(previous_script)}
exec(compile(previous_script.read_text().split('bpy.ops.wm.open_mainfile')[0],
             str(previous_script), 'exec'), previous)
for key in ('rest', 'local', 'parent', 'order', 'mat', 'smooth', 'hand_path',
            'blend_frame', 'world_to_blender', 'limb_frame', 'anatomy', 'R',
            'idle', 'idle_local', 'idle_bow', 'bow_at', 'timing',
            'L', 'G', 'C', 'HIT', 'F', 'RELEASE', 'keys'):
    globals()[key] = previous[key]
base = previous['ns']
FPS = 240
OUT = P / 'Export'
OUT.mkdir(parents=True, exist_ok=True)

# Bow-local frame. Once the bow is horizontal, fingers point up with a mild
# forward inclination, palm forward and hand back visible to the player.
finger_forward = Vector((.18, -.978, .10)).normalized()
hand_dorsal = Vector((-1., -.18, 0.)).normalized()
hand_delta = base['hand_basis']('r', finger_forward, hand_dorsal)
hand_rotation = hand_delta @ rest['hand_r'].to_3x3()
native_f = (R @ Vector(anatomy['r']['forward'])).normalized()
native_d = R @ Vector(anatomy['r']['dorsal'])
native_d = (native_d-native_f*native_f.dot(native_d)).normalized()
native_a = native_f.cross(native_d).normalized()

# Semantic open hand, not an opened version of the old fitted fist. Preserve
# all native translations and metacarpals. Four fingers fan mildly, with small
# independent bends; thumb spreads from the base and retains its nail roll.
digit_settings = {
    'index':  {'splay': 9.,   'flex': (2., 5., 9.)},
    'middle': {'splay': 0.,   'flex': (1., 4., 8.)},
    'ring':   {'splay': -8.,  'flex': (4., 8., 13.)},
    'pinky':  {'splay': -17., 'flex': (7., 12., 17.)},
    'thumb':  {'splay': 53.,  'flex': (11., 14., 19.)},
}
digit_info = {d['bone']: d for d in anatomy['r']['digits']}
open_world = {n:m.copy() for n,m in rest.items()}
right_open_local = {}
right_tree = {'hand_r'}
for n in order:
    if parent[n] not in right_tree:
        continue
    right_tree.add(n)
    current = open_world[parent[n]] @ local[n]
    if n in digit_info:
        d = digit_info[n]
        settings = digit_settings[d['digit']]
        splay = math.radians(settings['splay'])
        flex = math.radians(settings['flex'][d['segment']-1])
        aim = ((native_f*math.cos(splay)+native_a*math.sin(splay))*math.cos(flex)
               - native_d*math.sin(flex)).normalized()
        original_axis = (R @ Vector(d['axis'])).normalized()
        original_dorsal = (R @ Vector(d['dorsal'])).normalized()
        dorsal = native_d
        if d['digit'] == 'thumb':
            # Preserve the thumb's anatomical opposition / nail orientation.
            dorsal = original_axis.rotation_difference(aim) @ original_dorsal
        delta = limb_frame(aim, dorsal) @ limb_frame(original_axis, original_dorsal).transposed()
        current = mat(current.translation, delta @ rest[n].to_3x3())
    open_world[n] = current
    right_open_local[n] = open_world[parent[n]].inverted() @ current

# Fit translation only after defining the complete palm. The heel bears on
# the rear surface of the upper riser ~30 cm above the left support grip.
# Fit from the actual V7 skinned surface, retaining the visible open silhouette.
contact_wrist = Vector((-9., 4., 30.8))
fit_path = P / 'palm-fit.json'
if fit_path.exists():
    contact_wrist = Vector(json.loads(fit_path.read_text())['wrist_bow_cm'])
right_contact = mat(contact_wrist, hand_rotation)

def right_target(t, bow):
    target = bow @ right_contact
    if t < G:
        # Come up on the camera side of the bow. Open / turn the palm before
        # contact, then take up the final 1.5 cm instead of sweeping through it.
        at_grip = bow_at(G) @ right_contact
        p = hand_path([
            (0., idle['hand_r'].translation),
            (.065, at_grip.translation + Vector((-11., 3., -9.))),
            (.105, target.translation + Vector((-4., .7, -1.5))),
            (G, target.translation),
        ], t)
        q = idle['hand_r'].to_quaternion().slerp(target.to_quaternion(), smooth(t/.10))
        target = mat(p, q.to_matrix())
    elif t > RELEASE:
        # Release contact first, then let the wrist rotate and fingers relax.
        detach = smooth((t-RELEASE)/.07)
        target.translation += Vector((-7., 1.5, -1.))*detach
        target = blend_frame(target, idle['hand_r'], smooth((t-RELEASE-.055)/(L-RELEASE-.055)))
    return target

def pose(t):
    w = previous['pose'](t)
    bow = bow_at(t)
    target = right_target(t, bow)
    load = smooth(t/G)*(1.-smooth((t-RELEASE)/(L-RELEASE)))
    active = smooth(t/.085)*(1.-smooth((t-RELEASE-.06)/(L-RELEASE-.06)))
    drive = bow.translation-idle_bow.translation
    clav, up, low, hand = 'clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r'
    shoulder = idle[up].translation + drive*.20 + Vector((7.,-23.,3.))*load
    wrist = target.translation
    l1, l2 = local[low].translation.length, local[hand].translation.length
    axis = (wrist-shoulder).normalized()
    distance = (wrist-shoulder).length
    reach = (l1+l2)*.945
    if distance > reach:
        shoulder += axis*(distance-reach)
        distance = reach
    # Elbow under the palm, with the shoulder participating in the extension.
    pole = idle[low].translation.lerp(Vector((17.,-10.,-35.))+drive*.18, load)
    bend = pole-shoulder-axis*(pole-shoulder).dot(axis)
    bend.normalize()
    along = (l1*l1-l2*l2+distance*distance)/(2.*distance)
    elbow = shoulder+axis*along+bend*math.sqrt(max(0.,l1*l1-along*along))
    delta = target.to_3x3() @ rest[hand].to_3x3().transposed()
    ru, rl = rest[low].translation-rest[up].translation, rest[hand].translation-rest[low].translation
    ud, ld = (elbow-shoulder).normalized(), (wrist-elbow).normalized()
    across = R @ Vector(anatomy['r']['across'])
    lower_delta = limb_frame(ld, delta@across) @ limb_frame(rl, across).transposed()
    upper_delta = limb_frame(ud, ud.cross(ld)) @ limb_frame(ru, ru.cross(rl)).transposed()
    compatible = limb_frame(ud, delta@across) @ limb_frame(ru, across).transposed()
    upper_delta = upper_delta.to_quaternion().slerp(compatible.to_quaternion(), .20*load).to_matrix()
    w[clav] = idle[clav].copy()
    w[clav].translation = shoulder-w[clav].to_3x3()@local[up].translation
    w[up], w[low], w[hand] = (mat(shoulder, upper_delta@rest[up].to_3x3()),
                             mat(elbow, lower_delta@rest[low].to_3x3()), target)
    descendants = {up, low, hand}
    for n in order:
        if parent[n] in descendants and n not in (low, hand, 'bow_nock'):
            descendants.add(n)
            value = local[n].copy()
            if n in right_open_local:
                value = blend_frame(idle_local[n], right_open_local[n], active)
            w[n] = w[parent[n]] @ value
    # Inherit the native idle shoulder/wrist frames smoothly at both ends.
    edge = smooth(t/.045)*(1.-smooth((t-(L-.075))/.075))
    if edge < 1.:
        sampled = {n:m.copy() for n,m in w.items()}
        for n in order:
            if n not in descendants and n != clav:
                continue
            rel = sampled[parent[n]].inverted()@sampled[n]
            w[n] = w[parent[n]] @ blend_frame(idle_local[n], rel, edge)
    return w

bpy.ops.wm.open_mainfile(filepath=str(previous['BASE']/'Bow_SupportClearanceV11.blend'))
bpy.context.preferences.filepaths.save_version = 0
rig = bpy.data.objects['Bow_V7_Native']
arm = rig.data
scene = bpy.context.scene
scene.render.fps = FPS
rig.animation_data_create()
action = bpy.data.actions.new('A_Bow_QuickCombat')
rig.animation_data.action = action
scene.frame_start, scene.frame_end = 0, round(L*FPS)
last = {}
for frame in range(scene.frame_end+1):
    world = pose(frame/FPS)
    for n in order:
        b = rig.pose.bones[n]
        relative = world_to_blender(world[parent[n]]).inverted()@world_to_blender(world[n]) if parent[n] else world_to_blender(world[n])
        restlocal = arm.bones[parent[n]].matrix_local.inverted()@arm.bones[n].matrix_local if parent[n] else arm.bones[n].matrix_local
        b.rotation_mode = 'QUATERNION'
        b.matrix_basis = restlocal.inverted()@relative
        if frame and b.rotation_quaternion.dot(last[n]) < 0:
            b.rotation_quaternion.negate()
        last[n] = b.rotation_quaternion.copy()
        for prop in ('location','rotation_quaternion','scale'):
            b.keyframe_insert(prop,frame=frame)
scene.frame_set(0)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'A_Bow_QuickCombat.fbx'),use_selection=True,
    object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_QuickCombat.blend'))
(P/'authoring.json').write_text(json.dumps({
    'fps':FPS,'timing_seconds':timing,
    'asset':'/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat',
    'source_binding':'ContactV9 / V7 native bow arms / V11 idle',
    'right_hand':'Open five fingers; heel on rear upper riser; palm forward; fingers up; elbow underneath',
    'digit_settings':digit_settings,'wrist_bow_cm':list(contact_wrist),
    'source_length':L,'runtime_retiming':'BowQuickCombatMotion unchanged, 0.570833 sec miss / 0.605833 sec hit',
    'reference':'CastingPalmPush20260921/ImpactV9 semantic palm pose; native bow joint axes',
    'bow_keys':keys,'runtime_tested':False},indent=2),encoding='utf-8')
print('BOW_PALM_PUSH_AUTHORED',str(OUT/'A_Bow_QuickCombat.fbx'))
