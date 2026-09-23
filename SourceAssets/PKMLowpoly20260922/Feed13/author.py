"""One visible belt pitch per PKM shot; animation-only revision of Wrist12."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

O = Path(__file__).parent
R = O.parent
E = O / 'Exports'
E.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(R / 'Wrist12/PKM_WristContact_Editable.blend'))
s = bpy.context.scene
r = bpy.data.objects['PKM_Manny_Rig']
fit = Matrix(json.loads((R / 'Animation03/animation_manifest.json').read_text())['fit_matrix'])
layout = json.loads((R / 'Belt08/belt_layout.json').read_text())
centers = [Vector(p) for p in layout['centers']]
N = len(centers)
FPS = 240
SOURCE_FPS = 60
DURATION = .1
rest = {b.name: b.matrix_local.copy() for b in r.data.bones}
parent = {b.name: b.parent.name if b.parent else None for b in r.data.bones}
local_rest = {n: rest[parent[n]].inverted() @ m if parent[n] else m.copy() for n, m in rest.items()}
round_names = [f'PKM_Belt_{i:02}' for i in range(N)]
link_names = [f'PKM_Belt_Link_{i:02}' for i in range(N - 1)]
changed = set(round_names + link_names)


def action(a):
    r.animation_data.action = a
    r.animation_data.action_slot = a.slots[0]


def curves(a):
    for layer in a.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield bag


def smooth(x):
    x = max(0., min(1., x))
    return x * x * (3. - 2. * x)


def frame(p, direction):
    x = direction.normalized()
    y = Vector((0, 1, 0))
    z = x.cross(y).normalized()
    y = z.cross(x).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = p
    return m


frames = [frame(c, centers[min(i + 1, N - 1)] - centers[max(0, i - 1)]) for i, c in enumerate(centers)]
link_frames = [frame((a + b) * .5, b - a) for a, b in zip(centers, centers[1:])]
lengths = [(b - a).length for a, b in zip(centers, centers[1:])]


def belt_point(index):
    """C1 path through the current belt centers, preserving endpoint slots."""
    i = min(N - 2, max(0, int(math.floor(index))))
    u = max(0., min(1., index - i))
    p = centers[i]
    q = centers[i + 1]
    a = (q - centers[i - 1]) * .5 if i > 0 else q - p
    b = (centers[i + 2] - p) * .5 if i + 2 < N else q - p
    return (2*u**3 - 3*u**2 + 1)*p + (u**3 - 2*u**2 + u)*a + (-2*u**3 + 3*u**2)*q + (u**3-u**2)*b


def recycled(start, end, u, time):
    """Advance under the closed cover, hide locally, then refill inside the box.

    Only the single already-occluded unit is hidden. The visible belt and gun
    never inherit this scale or the hidden recycling translation.
    """
    m = start.copy()
    direction = (centers[0] - centers[1]).normalized()
    m.translation += direction * (lengths[0] * u)
    if u < .66:
        scale = 1. - smooth((u - .58) / .08)
    else:
        m = end.copy()
        scale = smooth((time - .086) / .010)
    return m, max(.00001, scale)


records = {}
for key in ['fire', 'aim_fire']:
    src = bpy.data.actions[f'PKM_Game_{key}_Wrist12']
    action(src)
    s.render.fps = SOURCE_FPS
    s.render.fps_base = 1
    samples = []
    for f in range(round(DURATION * FPS) + 1):
        source_frame = f * SOURCE_FPS / FPS
        s.frame_set(int(source_frame), subframe=source_frame % 1)
        bpy.context.view_layer.update()
        samples.append({b.name: b.matrix.copy() for b in r.pose.bones})
    out = src.copy()
    out.name = f'PKM_Game_{key}_Feed13'
    out.use_fake_user = True
    # Preserve every non-belt channel, with an equivalent time base at 240 Hz.
    for bag in curves(out):
        for curve in list(bag.fcurves):
            if any(curve.data_path.startswith(f'pose.bones["{n}"]') for n in changed):
                bag.fcurves.remove(curve)
                continue
            for point in curve.keyframe_points:
                point.co.x *= FPS / SOURCE_FPS
                point.handle_left.x *= FPS / SOURCE_FPS
                point.handle_right.x *= FPS / SOURCE_FPS
    action(out)
    s.render.fps = FPS
    previous = {}
    for f, row in enumerate(samples):
        t = f / FPS
        # A brief impulse, one forward feed, then a settling window before reset.
        u = smooth((t - .012) / .068)
        W = row['WPN_root'] @ fit
        points = [belt_point(max(0., i - u)) for i in range(N)]
        # Receiver and box ends remain anchored. The free bend follows the tug.
        for i in range(1, layout['inlet_index']):
            envelope = math.sin(math.pi * i / layout['inlet_index'])
            pulse = math.sin(math.pi * u) * math.sin(2*math.pi * t / DURATION - i*.33)
            points[i] += Vector((0., .00065 * pulse * envelope, .00045 * pulse * envelope))
        desired = {}
        for i, n in enumerate(round_names):
            if i == 0:
                recycle, scale = recycled(frames[0], frames[-1], u, t)
                m = recycle @ frames[0].to_3x3().transposed().to_4x4()
                m.translation = recycle.translation
                m = m @ Matrix.Diagonal((scale, scale, scale, 1.))
            else:
                qa = frames[i].to_quaternion()
                qb = frames[i - 1].to_quaternion()
                q = qa.slerp(qb, u)
                m = q.to_matrix().to_4x4() @ frames[i].to_3x3().transposed().to_4x4()
                m.translation = points[i]
            desired[n] = W @ m
        for i, n in enumerate(link_names):
            if i == 0:
                m, scale = recycled(link_frames[0], link_frames[-1], u, t)
                length_scale = lengths[-1] / lengths[0] if u >= .66 else 1.
                m = m @ Matrix.Diagonal((scale * length_scale, scale, scale, 1.))
            else:
                # Both adjacent cartridges advance toward the preceding slot.
                a, b = points[i], points[i + 1]
                m = frame((a + b) * .5, b - a)
                m = m @ Matrix.Diagonal(((b - a).length / lengths[i], 1., 1., 1.))
            desired[n] = W @ m
        for n, m in desired.items():
            local = row[parent[n]].inverted() @ m
            loc, q, scale = (local_rest[n].inverted() @ local).decompose()
            if n in previous and previous[n].dot(q) < 0:
                q.negate()
            previous[n] = q.copy()
            bone = r.pose.bones[n]
            bone.location = loc
            bone.rotation_mode = 'QUATERNION'
            bone.rotation_quaternion = q
            bone.scale = scale
            for prop in ['location', 'rotation_quaternion', 'scale']:
                bone.keyframe_insert(prop, frame=f, group=n)
    for bag in curves(out):
        for curve in bag.fcurves:
            if any(curve.data_path.startswith(f'pose.bones["{n}"]') for n in changed):
                for point in curve.keyframe_points:
                    point.interpolation = 'LINEAR'
    s.frame_start = 0
    s.frame_end = round(DURATION * FPS)
    s.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    r.hide_set(False)
    r.select_set(True)
    bpy.context.view_layer.objects.active = r
    bpy.ops.export_scene.fbx(filepath=str(E / f'A_PKM_{key}.fbx'), use_selection=True,
        object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
        bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0, bake_anim_step=1)
    records[key] = {'action': out.name, 'seconds': DURATION, 'fps': FPS}
    print('PKM13_EXPORTED', key, flush=True)

# Blender stores FPS per scene. Keep the complete editable source at its
# original 60 Hz so Wrist12/reload clips remain correctly timed when selected.
# The exported firing FBXs above retain their independent 240 Hz sample rate.
for record in records.values():
    a = bpy.data.actions[record['action']]
    for bag in curves(a):
        for curve in bag.fcurves:
            for point in curve.keyframe_points:
                point.co.x *= SOURCE_FPS / FPS
                point.handle_left.x *= SOURCE_FPS / FPS
                point.handle_right.x *= SOURCE_FPS / FPS
s.render.fps = SOURCE_FPS
action(bpy.data.actions[records['fire']['action']])
s.frame_start = 0
s.frame_end = round(DURATION * SOURCE_FPS)
s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'PKM_FiringFeed_Editable.blend'))
(O / 'authoring.json').write_text(json.dumps({
    'source': 'Wrist12/PKM_WristContact_Editable.blend',
    'clips': {key: DURATION for key in records}, 'actions': records,
    'export_fps': FPS, 'editable_scene_fps': SOURCE_FPS,
    'bones_changed': sorted(changed), 'visible_pitch_per_shot': 1,
    'feed_begin_seconds': .012, 'feed_end_seconds': .080,
    'hidden_unit_restore_seconds': .096,
    'mesh_changed': False, 'materials_changed': False, 'reload_changed': False,
    'runtime_tested': False,
}, indent=2), encoding='utf-8')
print('PKM13_AUTHOR_COMPLETE', flush=True)
