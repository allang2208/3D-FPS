"""Carry the accepted AKM support chain with the already transferred whole hand.

The current M870 hand, fingers, gun, right arm and clip clocks are inputs.
Only the left shoulder, elbow and native forearm skin stations are authored.
No pole search, wrist cap, digit fitting, mesh edits or rendering is performed.
"""
import ast
import json
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

O = Path(__file__).parent
PREV = O.parent / 'M870AKMGrip20261016'
BASE = O.parent / 'M870Tactical20261015'
X = O / 'Exports'
(X / 'Animations').mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(PREV / 'M870_AKMGrip_Editable.blend'), use_scripts=False)
r = bpy.data.objects['SK_Super90']
s = bpy.context.scene
rest = {b.name: b.matrix_local.copy() for b in r.data.bones}
parents = {b.name: b.parent.name if b.parent else None for b in r.data.bones}
local_rest = {n: rest[parents[n]].inverted() @ m if parents[n] else m for n, m in rest.items()}
d = json.loads((PREV / 'akm_grip.json').read_text())
sr = {n: Matrix(m) for n, m in d['rest'].items()}
sp = {n: Matrix(m) for n, m in d['pose'].items()}


def palm(p):
    forward = (p['middle_01_l'].translation - p['hand_l'].translation).normalized()
    across = (p['index_01_l'].translation - p['pinky_01_l'].translation).normalized()
    normal = across.cross(forward).normalized()
    return Matrix((forward.cross(normal).normalized(), forward, normal)).transposed().to_quaternion()


bind_map = palm(rest) @ palm(sr).inverted()
source_palm = palm(sp)
upper_rest = rest['lowerarm_l'].translation - rest['upperarm_l'].translation
fore_rest = rest['hand_l'].translation - rest['lowerarm_l'].translation
source_upper = (sp['lowerarm_l'].translation - sp['upperarm_l'].translation).normalized()
source_fore = (sp['hand_l'].translation - sp['lowerarm_l'].translation).normalized()


def support(row):
    # The complete hand is immutable. Transfer the donor's arm directions in
    # its palm frame, using the target's native lengths, never the donor scale.
    carry = palm(row) @ source_palm.inverted()
    wrist = row['hand_l'].translation
    elbow = wrist - (carry @ source_fore) * fore_rest.length
    shoulder = elbow - (carry @ source_upper) * upper_rest.length

    def donor_rotation(name):
        return (carry @ sp[name].to_quaternion() @ sr[name].to_quaternion().inverted()
                @ bind_map.inverted() @ rest[name].to_quaternion())

    def segment(name, native_axis, direction, origin):
        q = donor_rotation(name)
        deformed_axis = q @ rest[name].to_quaternion().inverted() @ native_axis
        swing = deformed_axis.rotation_difference(direction)
        q = swing @ q
        row[name] = Matrix.LocRotScale(origin, q, Vector((1, 1, 1)))
        return swing

    segment('upperarm_l', upper_rest, elbow - shoulder, shoulder)
    fore_swing = segment('lowerarm_l', fore_rest, wrist - elbow, elbow)
    fore_delta = row['lowerarm_l'] @ rest['lowerarm_l'].inverted()
    # Native S90 stations are children of lowerarm, not a serial twist chain.
    # Transport the donor's authored station roll instead of redistributing
    # arbitrary fractions of wrist bend across these skinning bones.
    for name in ('lowerarm_aux_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l'):
        if name not in rest:
            continue
        position = fore_delta @ rest[name].translation
        q = fore_swing @ donor_rotation(name) if name in sp else (fore_delta @ rest[name]).to_quaternion()
        row[name] = Matrix.LocRotScale(position, q, Vector((1, 1, 1)))
    # First-person shoulder support can translate; preserve the native
    # clavicle-to-upperarm offset and leave the hand's contact track untouched.
    cq = donor_rotation('clavicle_l')
    offset = rest['upperarm_l'].translation - rest['clavicle_l'].translation
    cp = shoulder - cq @ rest['clavicle_l'].to_quaternion().inverted() @ offset
    row['clavicle_l'] = Matrix.LocRotScale(cp, cq, Vector((1, 1, 1)))


tree = ast.parse((BASE / 'author_m870.py').read_text())
selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('select', 'bake')]
authored = {}
exec(compile(ast.Module(body=selected, type_ignores=[]), str(BASE / 'author_m870.py'), 'exec'))
inputs = json.loads((PREV / 'authoring.json').read_text())['clips']
recipe = {}
for role, entry in inputs.items():
    action = bpy.data.actions[entry['action']]
    r.animation_data.action = action
    r.animation_data.action_slot = action.slots[0]
    count = round(entry['duration'] * 60) + 1
    rows = []
    for frame in range(count):
        s.frame_set(frame)
        row = {b.name: b.matrix.copy() for b in r.pose.bones}
        support(row)
        rows.append(row)
    bake(role, rows)
    recipe[role] = {'input_action': entry['action'], 'frames': count}

idle = bpy.data.actions[authored['idle']['action']]
r.animation_data.action = idle
r.animation_data.action_slot = idle.slots[0]
s.frame_set(0)
s.frame_start = 0
s.frame_end = round(authored['idle']['duration'] * 60)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'M870_AKMArmSupport_Editable.blend'))
(O / 'authoring.json').write_text(json.dumps({
    'clips': authored, 'recipe': recipe,
    'support_source': d['runtime_animation'], 'support_source_action': d['action'],
    'hand_source': str(PREV / 'M870_AKMGrip_Editable.blend'),
    'method': 'Accepted AKM arm directions and skin-station roll in the complete hand frame; native target segment lengths.',
    'scope': 'Left clavicle, upperarm, lowerarm and native forearm stations only; all hand matrices are input tracks.',
    'runtime_tested': False, 'visual_accepted': False
}, indent=2))
print('M870_AKM_ARM_SUPPORT_AUTHORED', len(authored), flush=True)
