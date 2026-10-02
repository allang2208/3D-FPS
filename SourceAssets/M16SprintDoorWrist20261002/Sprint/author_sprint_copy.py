"""Copy the saved M4 complete sprint left chain to the existing M16 clips.

Animation-only production. Existing M16 right-arm, receiver and mechanics stay
on their existing source trajectories. No wrist design, IK, twist reset, mesh
import, runtime test or render. Run with Blender --background --python.
"""
import bpy
import hashlib
import json
from pathlib import Path
from mathutils import Matrix, Vector

O = Path(__file__).resolve().parent
S = O.parents[1]
bpy.context.preferences.filepaths.save_version = 0
FAMILIES = ('Base', 'Drum', 'Angled', 'Vertical', 'Canted', 'Prism')
KINDS = (('Enter', 18), ('Loop', 36), ('Exit', 18))
STEP = .5

def sample(rig, action, frame):
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
    bpy.context.view_layer.update()
    return {bone.name: bone.matrix.copy() for bone in rig.pose.bones}

def smooth(x):
    x = max(0., min(1., x))
    return x*x*(3.-2.*x)

def mix(a, b, weight):
    if weight <= 0.: return a.copy()
    if weight >= 1.: return b.copy()
    p, q, scale = a.decompose()
    p1, q1, scale1 = b.decompose()
    return Matrix.LocRotScale(p.lerp(p1, weight), q.slerp(q1, weight), scale.lerp(scale1, weight))

def file_info(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

# Cache actual saved donor action samples before opening the M16 source rig.
donors = {}
inputs = {}
for family in FAMILIES:
    source = S/'M4TacticalSprint20260915'/family/f'M4_TacticalSprint_{family}_Editable.blend'
    inputs[f'M4/{family}'] = file_info(source)
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    rig = bpy.data.objects['SK_M4_Infima']
    donors[family] = {kind: [sample(rig, bpy.data.actions[f'M4_TacticalSprint_{family}_{kind}'], j*STEP)
        for j in range(end*2+1)] for kind, end in KINDS}

held_manifest = json.loads((S/'M16UniversalAttachments20260920/authoring.json').read_text())
model_manifest = json.loads((S/'M16UniversalAttachments20260920/models.json').read_text())
build_manifest = json.loads((S/'M16Gameplay20260919/build.json').read_text())
support_shift = Vector(build_manifest['support_contact_shift_m'])
magazine_shift = Vector(build_manifest['magazine_contact_shift_m'])
report = {
    'revision': 2026100208,
    'production': 'saved M4 complete left-chain sprint transfer only',
    'inputs': inputs,
    'right_arm_weapon_mechanics': 'existing saved M16 source animation retained for every sample',
    'left_arm_policy': 'full donor clavicle/upperarm/lowerarm/wrist/4 twist helpers/19 digits, no IK or helper reset',
    'contact_policy': 'existing M16 support offset or existing registered attachment grasp; complete local-chain handoff',
    'native_binding_policy': 'animation only; no skeletal-mesh or USkeleton reference changes; neutral digit mesh bindings retained',
    'm16_native_wrist_adaptation': 'common V7 wrist mesh binding authored separately in the sibling Wrist production',
    'tested': False, 'rendered': False, 'ue_imported': False, 'clips': {},
}

for family in FAMILIES:
    lower = family.lower()
    source = (S/'M16Gameplay20260919/M16_Manny_Editable.blend' if family == 'Base'
        else S/'M16UniversalAttachments20260920'/f'M16_{lower}_Animations_Editable.blend')
    report['inputs'][f'M16/{family}'] = file_info(source)
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    rig = bpy.data.objects['SK_M4_Infima']
    rig.data.pose_position = 'POSE'
    scene = bpy.context.scene
    scene.render.fps = 60
    rest = {bone.name: bone.matrix_local.copy() for bone in rig.data.bones}
    parents = {bone.name: bone.parent.name if bone.parent else None for bone in rig.data.bones}
    names = list(rest)
    local_rest = {name: rest[parents[name]].inverted()@rest[name] if parents[name] else rest[name] for name in names}
    left = [name for name in names if name.endswith('_l')]
    retained = {}
    for kind, end in KINDS:
        old_name = f'M16_sprint_{kind.lower()}' if family == 'Base' else f'M16_{lower}_Sprint{kind}'
        retained[kind] = [sample(rig, bpy.data.actions[old_name], j*STEP) for j in range(end*2+1)]

    held = None
    if family != 'Base':
        donor = held_manifest['donors'][lower]
        registration = (Matrix.Translation(magazine_shift) if family == 'Drum'
            else Matrix(model_manifest['grip_mount'])@Matrix(donor['mount']).inverted())
        held = {name: registration@Matrix(matrix) for name, matrix in donor['pose'].items() if name in left}

    dest = O/family
    (dest/'Animations').mkdir(parents=True, exist_ok=True)
    for kind, end in KINDS:
        rows = []
        previous = {}
        for j, old in enumerate(retained[kind]):
            frame = j*STEP
            donor = donors[family][kind][j]
            pose = {name: matrix.copy() for name, matrix in old.items()}
            # Reuse saved donor matrices directly, including every helper roll.
            # The old M16 shift_arm() is deliberately never called, even at zero
            # support displacement: it erased helpers on every Loop sample.
            for name in left:
                if name in donor: pose[name] = donor[name].copy()
            if family == 'Base':
                contact = 0. if kind == 'Loop' else (1.-smooth(frame/end) if kind == 'Enter' else smooth(frame/end))
                shift = pose['WPN_root'].to_3x3()@(support_shift*contact)
                # Existing support registration is a rigid whole-chain move;
                # it cannot introduce a new wrist angle or reset helper roll.
                for name in left: pose[name].translation += shift
            else:
                weight = (0. if kind == 'Loop' else (1.-smooth(frame/(end*.45)) if kind == 'Enter'
                    else smooth((frame-end*.55)/(end*.45))))
                if weight > 0.:
                    target = {name: pose['WPN_root']@matrix for name, matrix in held.items()}
                    # Same complete local-chain adaptation as the existing M16
                    # attachment transplant, now with the intact M4 sprint donor.
                    for name in left:
                        if name not in target: continue
                        parent = parents[name]
                        donor_local = donor[parent].inverted()@donor[name]
                        target_parent = target[parent] if parent in target else old[parent]
                        target_local = target_parent.inverted()@target[name]
                        pose[name] = pose[parent]@mix(donor_local, target_local, weight)
            row = {}
            for name in names:
                parent = parents[name]
                basis = local_rest[name].inverted()@(pose[parent].inverted()@pose[name] if parent else pose[name])
                location, rotation, scale = basis.decompose()
                if name in previous and previous[name].dot(rotation) < 0.: rotation.negate()
                previous[name] = rotation.copy()
                row[name] = (location, rotation, scale)
            rows.append(row)

        action = bpy.data.actions.new(f'M16_M4SprintLeftCopy_{family}_{kind}_20261002')
        action.use_fake_user = True
        rig.animation_data.action = action
        for name in names:
            bone = rig.pose.bones[name]
            bone.rotation_mode = 'QUATERNION'
            for prop in ('location', 'rotation_quaternion', 'scale'): bone.keyframe_insert(prop, frame=0)
        curves = {(curve.data_path, curve.array_index): curve
            for layer in action.layers for strip in layer.strips for bag in strip.channelbags for curve in bag.fcurves}
        for name in names:
            for prop, field, count in (('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)):
                for axis in range(count):
                    curve = curves[(f'pose.bones["{name}"].{prop}', axis)]
                    curve.keyframe_points.clear()
                    curve.keyframe_points.add(len(rows))
                    curve.keyframe_points.foreach_set('co', [value for j, row in enumerate(rows)
                        for value in (j*STEP, row[name][field][axis])])
                    for key in curve.keyframe_points: key.interpolation = 'LINEAR'
                    curve.update()
        rig.animation_data.action_slot = action.slots[0]
        scene.frame_start, scene.frame_end = 0, end
        scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT')
        rig.hide_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        name = f'A_M16_sprint_{kind.lower()}' if family == 'Base' else f'A_M16_{lower}_Sprint{kind}'
        file = dest/'Animations'/(name+'.fbx')
        folder = ('/Game/Weapons/M16A2/Gameplay20260919/Animations' if family == 'Base'
            else '/Game/Weapons/M16A2/UniversalAttachments20260920/Animations/'+lower)
        bpy.ops.export_scene.fbx(filepath=str(file), use_selection=True, object_types={'ARMATURE'},
            axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
            bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
            bake_anim_force_startend_keying=True, bake_anim_step=STEP, bake_anim_simplify_factor=0)
        report['clips'][family+'/'+kind] = {
            'family': lower, 'kind': kind, 'role': 'sprint_'+kind.lower(), 'name': name,
            'file': str(file), 'folder': folder, 'asset': folder+'/'+name,
            'action': action.name, 'source_action': (f'M16_sprint_{kind.lower()}' if family == 'Base'
                else f'M16_{lower}_Sprint{kind}'),
            'donor_action': f'M4_TacticalSprint_{family}_{kind}',
            'duration': end/60., 'samples': len(rows), 'sample_rate': 120,
        }
        (O/'authored.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('M16_M4_SPRINT_LEFT_COPIED', family, kind, flush=True)
    scene.frame_start, scene.frame_end = 0, 18
    rig.animation_data.action = bpy.data.actions[f'M16_M4SprintLeftCopy_{family}_Enter_20261002']
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
    scene.frame_set(0)
    blend = dest/f'M16_SprintLeftCopy_{family}_20261002.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report.setdefault('editable_sources', {})[family] = str(blend)
    (O/'authored.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
report['complete'] = True
(O/'authored.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('M16_M4_SPRINT_LEFT_COPY_AUTHORING_COMPLETE', len(report['clips']), flush=True)
