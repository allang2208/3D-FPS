"""Author real five-digit skin and a hooked rake, using the local Mutant3 hand recipe.

No preview, render or gameplay test. The Fab geometry and its UV atlas are retained.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
OUT = ROOT / 'Export'
OUT.mkdir(parents=True, exist_ok=True)
PROJECT = ROOT.parents[2]
DONOR = PROJECT / 'SourceAssets/Mutant3Khaimera20260923/claw_reference_20260923/claw_skin.json'
reference = json.loads(DONOR.read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(BASE / 'AzureDragonClaw.blend'))
mesh = bpy.data.objects['SM_AzureDragonClaw']
mesh.name = 'SK_AzureDragonClaw_RakeV9'
mesh.vertex_groups.clear()
landmarks = json.loads((BASE / 'Export/finger-landmarks.json').read_text(encoding='utf-8'))
low, high = -19.08791732788086, 20.21254539489746
scale = 125. / (high-low)
pivot = low + (high-low)*.36
height_center = (-3.97971248626709+5.481351852416992)*.5


def transform(p):
    return Vector(((p[2]-pivot)*scale, p[0]*scale, (p[1]-height_center)*scale))


def ease(t):
    t = min(1., max(0., t))
    return t*t*(3.-2.*t)


digits = []
labels = ['Pinky', 'Ring', 'Middle', 'Index', 'Thumb']
for i, landmark in enumerate(landmarks):
    outer = i in (0, 4)
    center = landmark['center']
    base = transform([center[0]*(.70 if outer else .90), .35, 2.5 if outer else 5.])
    nail = transform([center[0], .15, landmark['min'][2]+.35])
    tip = transform(landmark['tip'])
    # Keep the nail on its own terminal bone; bend the skin at actual knuckles.
    points = [base, base.lerp(nail, .49), nail, tip]
    donor = reference['chains']['Right'+labels[i]]
    digits.append({'name':f'digit_{i+1:02d}', 'points':points, 'outer':outer,
                   'donor_degrees':donor['curl_degrees'], 'label':labels[i]})

bpy.ops.object.select_all(action='DESELECT')
data = bpy.data.armatures.new('AzureDragonRakeSkeletonV9')
rig = bpy.data.objects.new('AzureDragonRakeRigV9', data)
bpy.context.collection.objects.link(rig)
rig.show_in_front = True
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
root = data.edit_bones.new('root')
root.head, root.tail = (-45,0,0), (-12,0,0)
root.align_roll(Vector((0,0,1)))
palm = data.edit_bones.new('palm')
palm.head, palm.tail, palm.parent = root.tail, (27,0,0), root
palm.align_roll(Vector((0,0,1)))
for digit in digits:
    parent = palm
    for j in range(3):
        bone = data.edit_bones.new(f'{digit["name"]}_{j+1:02d}')
        bone.head, bone.tail = digit['points'][j:j+2]
        bone.parent, bone.use_connect, bone.use_deform = parent, False, True
        bone.align_roll(Vector((0,0,1)))
        parent = bone
bpy.ops.object.mode_set(mode='OBJECT')
groups = {bone.name:mesh.vertex_groups.new(name=bone.name) for bone in data.bones}
counts = {name:0 for name in groups}


def add(index, name, value):
    if value > 1.e-6:
        groups[name].add([index], value, 'REPLACE')
        counts[name] += 1


for vertex in mesh.data.vertices:
    p = vertex.co
    if p.x < 3.:
        blend = ease((p.x+17.)/20.)
        add(vertex.index, 'root', 1.-blend)
        add(vertex.index, 'palm', blend)
        continue
    candidates = []
    for i, digit in enumerate(digits):
        a, b = digit['points'][0], digit['points'][2]
        d = b-a
        t = max(0., min(1., (p-a).dot(d)/d.length_squared))
        near = a+d*t
        # Separate digit assignment, continuous axial transitions, never smear a nail.
        candidates.append(((p.y-near.y)**2+.15*(p.x-near.x)**2, i, t))
    _, i, t = min(candidates)
    digit = digits[i]
    points = digit['points']
    strength = ease((p.x-points[0].x+4.)/9.)
    if p.x >= points[2].x-.35:
        add(vertex.index, digit['name']+'_03', 1.)
    else:
        a = ease((t-.40)/.18)
        b = ease((t-.88)/.12)
        add(vertex.index, 'palm', 1.-strength)
        for j, weight in enumerate((1.-a, a*(1.-b), a*b)):
            add(vertex.index, f'{digit["name"]}_{j+1:02d}', strength*weight)
modifier = mesh.modifiers.new('FiveDigitRakeSkinV9', 'ARMATURE')
modifier.object = rig
modifier.use_deform_preserve_volume = False
mesh.parent = rig
scene = bpy.context.scene
scene.render.fps, scene.frame_start, scene.frame_end = 60, 0, 36

# Pose 0 is already a relaxed hook. Contact never starts with five straight rods.
# Mutant3 concentrates flexion in PIP/DIP; keep an open palm, not a closed fist.
keys = [(0, .40, .45), (6, .25, .65), (11, .72, .15),
        (20, 1., -.35), (27, .85, -.18), (36, .40, .45)]
for i, digit in enumerate(digits):
    for j in range(3):
        pb = rig.pose.bones[f'{digit["name"]}_{j+1:02d}']
        direction = (digit['points'][j+1]-digit['points'][j]).normalized()
        curl = Vector((0, -.12 if i==4 else .0, -1.)).normalized()
        # Anatomical curl axis converted into THIS joint's binding frame.
        # Euler-X with an assumed bone roll can curl away from the palm.
        bend_axis = pb.bone.matrix_local.to_quaternion().inverted() @ direction.cross(curl).normalized()
        gather_axis = pb.bone.matrix_local.to_quaternion().inverted() @ Vector((0,0,1))
        pb.rotation_mode = 'QUATERNION'
        peak = float(digit['donor_degrees'][j])
        if j==0:
            peak = max(17., peak)
        if digit['outer'] and j==1:
            peak = min(62., max(48., peak))
        for frame, close, spread in keys:
            # Small distal delay gives the five fingers a living, sequential rake.
            stamp = frame if frame in (0,36) else min(35, frame+[1,0,-1,1,2][i])
            bend = peak*(close if j==0 else .35+.65*close)
            q = Quaternion(bend_axis, math.radians(bend))
            if j==0:
                side = -1. if i<2 else (1. if i>2 else 0.)
                # Positive gather narrows the gaps during the strike, retains clearance.
                q = Quaternion(gather_axis, math.radians(side*8.*spread)) @ q
            pb.rotation_quaternion = q
            pb.keyframe_insert('rotation_quaternion', frame=stamp, group=pb.name)
palm = rig.pose.bones['palm']
palm.rotation_mode = 'QUATERNION'
axis = palm.bone.matrix_local.to_quaternion().inverted() @ Vector((0,1,0))
for frame, degrees in [(0,0), (6,-9), (11,-5), (20,15), (27,9), (36,0)]:
    palm.rotation_quaternion = Quaternion(axis, math.radians(degrees))
    palm.keyframe_insert('rotation_quaternion', frame=frame, group='palm')
action = rig.animation_data.action
action.name = 'A_AzureDragonClaw_RakeV9'
action.use_fake_user = True
for slot in action.slots:
    bag = action.layers[0].strips[0].channelbag(slot)
    if bag:
        for curve in bag.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'

rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion()
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
mesh.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
common = dict(use_selection=True, object_types={'MESH','ARMATURE'}, axis_forward='-Y', axis_up='Z',
              add_leaf_bones=False, mesh_smooth_type='FACE', use_tspace=False,
              apply_scale_options='FBX_SCALE_ALL', armature_nodetype='NULL', embed_textures=False)
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_AzureDragonClaw_RakeV9.fbx'), bake_anim=False, **common)
rig.animation_data.action = action
if action.slots:
    rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.ops.export_scene.fbx(filepath=str(OUT/'A_AzureDragonClaw_RakeV9.fbx'), bake_anim=True,
                        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                        bake_anim_force_startend_keying=True, bake_anim_step=1., bake_anim_simplify_factor=0., **common)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'AzureDragonClaw_RakeV9.blend'))
manifest = dict(revision=9, reference=str(DONOR), bones=17, digits=5, joints_per_digit=3,
                animation_seconds=.6, weighted_vertices=counts,
                gesture='relaxed hook, wrist windup, gather fingers, diagonal rake, hooked recovery',
                finger_joints={d['name']:[list(p) for p in d['points']] for d in digits},
                mesh=str(OUT/'SK_AzureDragonClaw_RakeV9.fbx'), animation=str(OUT/'A_AzureDragonClaw_RakeV9.fbx'),
                source_author='CaptainHC', rendered=False, runtime_tested=False)
(OUT/'rig.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('AZURE_DRAGON_RAKE_V9_EXPORTED digits=5 joints=15', flush=True)
