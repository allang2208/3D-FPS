"""Save editable source actions and the installed native V9 skin; no rendering."""
import bisect
import gzip
import json
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

O = Path(__file__).parent
I = O / 'Inputs'
load = lambda name: json.load(gzip.open(I / (name + '.json.gz'), 'rt'))
motion, weapon, arms = [load(n) for n in ('motion', 'svch', 'arms')]
profile = json.loads((O / 'profile_reload_grip.json').read_text())
names = motion['names']
indices = {n: i for i, n in enumerate(names)}
parents = [indices.get(p, -1) for p in motion['parents']]
C = Matrix.Diagonal((100., -100., 100., 1.))
CI = C.inverted()


def transform(v):
    return Matrix.LocRotScale(Vector(v[:3]), Quaternion((v[6], *v[3:6])).normalized(), Vector(v[7:10]))


def sample(track, time):
    times, values = track['times'], track['values']
    if len(times) == 1:
        return values[:10]
    i = max(0, min(len(times) - 2, bisect.bisect_left(times, time) - 1))
    w = max(0., min(1., (time - times[i]) / (times[i + 1] - times[i])))
    a, b = values[i * 10:(i + 1) * 10], values[(i + 1) * 10:(i + 2) * 10]
    v = [x * (1 - w) + y * w for x, y in zip(a, b)]
    q = Quaternion((a[6], *a[3:6])).slerp(Quaternion((b[6], *b[3:6])), w)
    v[3:7] = [q.x, q.y, q.z, q.w]
    return v


bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(O.parent / 'R8Surface/SVCH_R8Surface.blend'))
scene = bpy.context.scene
rig = bpy.data.objects['SK_M4_Infima']
rig.data.pose_position = 'POSE'
skin_rig = rig.copy()
skin_rig.data = rig.data.copy()
skin_rig.name = 'SVCH_NativeV9_EditableRig'
scene.collection.objects.link(skin_rig)
skin_rig.animation_data_clear()

# Copy the current native V9 coordinates and weights into its own source rig.
# Each rig uses its own UE inverse bind during pose conversion, as the runtime
# follower does. Neither the R8 weapon nor the installed V9 asset is rewritten.
mesh = bpy.data.meshes.new('SVCH_NativeV9_Skin')
mesh.from_pydata([tuple(CI @ Vector(p)) for p in arms['positions']], [],
                 [tuple(reversed(t)) for t in arms['triangles']])
mesh.update()
skin = bpy.data.objects.new('SVCH_NativeV9_SourceSkin', mesh)
scene.collection.objects.link(skin)
for slot in arms['materials']:
    material = bpy.data.materials.new(slot + '_SourceDisplay')
    material.diffuse_color = (.58, .36, .23, 1.)
    mesh.materials.append(material)
for polygon, slot in zip(mesh.polygons, arms['material_ids']):
    polygon.material_index = slot
    polygon.use_smooth = True
for name in arms['weight_bones']:
    skin.vertex_groups.new(name=name)
for index, weights in enumerate(arms['weights']):
    for bone, weight in weights:
        skin.vertex_groups[bone].add([index], weight, 'REPLACE')
modifier = skin.modifiers.new('NativeV9Skin', 'ARMATURE')
modifier.object = skin_rig
skin['ue_asset'] = arms['path']
skin['ue_sha256'] = arms['sha256']
skin['display_materials_only'] = True
hidden = []
for obj in list(scene.objects):
    if obj.type != 'MESH' or obj == skin:
        continue
    weighted = {obj.vertex_groups[g.group].name for v in obj.data.vertices for g in v.groups if g.weight > .001}
    if weighted and not any(n.startswith('WPN_') for n in weighted):
        obj.hide_set(True)
        obj.hide_render = True
        hidden.append(obj.name)

world_samples = {}
for role in ('reload', 'reload_empty'):
    clip = motion['clips'][role]
    layer = next(c for c in profile['clips'] if c['base'] == clip['path'])
    samples = []
    for raw, time in zip(clip['frames'], clip['times']):
        local = [transform(row) for row in raw]
        for track in layer['tracks']:
            j = indices[track['bone']]
            delta = sample(track, time)
            row = raw[j]
            q = Quaternion((delta[6], *delta[3:6])) @ Quaternion((row[6], *row[3:6]))
            local[j] = Matrix.LocRotScale(Vector(row[:3]) + Vector(delta[:3]), q.normalized(),
                                          Vector(row[7:10]) + Vector(delta[7:10]))
        world = []
        for j, parent in enumerate(parents):
            world.append(world[parent] @ local[j] if parent >= 0 else local[j])
        samples.append(world)
    world_samples[role] = samples

report = {'saved': False, 'runtime_tested': False, 'preview_rendered': False,
          'weapon_source': str(O.parent / 'R8Surface/SVCH_R8Surface.blend'),
          'native_v9_source': arms['path'], 'native_v9_sha256': arms['sha256'],
          'native_v9_geometry_weights_preserved': True, 'hidden_embedded_source_arms': hidden,
          'source_display_materials': 'Neutral colors only; game materials remain in UE unchanged',
          'fps': 120, 'clips': []}
scene.render.fps = 120
scene.render.fps_base = 1.

for target, data, label in ((rig, weapon, 'Weapon'), (skin_rig, arms, 'NativeV9')):
    target.animation_data_create()
    target.animation_data.use_nla = False
    world_inv = target.matrix_world.inverted()
    rest = {b.name: target.matrix_world @ b.matrix_local for b in target.data.bones}
    local_inv = {b.name: (b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).inverted()
                 for b in target.data.bones}
    native_inv = [transform(t).inverted() for t in data['reference']]
    bone_names = [n for n in names if n in rest]
    default = None
    for role in ('reload', 'reload_empty'):
        clip = motion['clips'][role]
        rows = {n: [] for n in bone_names}
        previous = {}
        for world in world_samples[role]:
            converted = {n: world_inv @ CI @ world[indices[n]] @ native_inv[indices[n]] @ C @ rest[n] for n in bone_names}
            for n in bone_names:
                parent = target.data.bones[n].parent
                local = converted[parent.name].inverted() @ converted[n] if parent else converted[n]
                p, q, s = (local_inv[n] @ local).decompose()
                if n in previous and q.dot(previous[n]) < 0:
                    q.negate()
                previous[n] = q.copy()
                rows[n].append((tuple(p), tuple(q), tuple(s)))
        action = bpy.data.actions.new('SVCH_R9_' + label + '_' + role)
        action.use_fake_user = True
        target.animation_data.action = action
        for n in bone_names:
            bone = target.pose.bones[n]
            bone.rotation_mode = 'QUATERNION'
            for prop in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(prop, frame=0.)
        curves = {(c.data_path, c.array_index): c for layer in action.layers
                  for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}
        for n, values in rows.items():
            for prop, field, count in (('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)):
                for axis in range(count):
                    curve = curves[(f'pose.bones["{n}"].{prop}', axis)]
                    curve.keyframe_points.clear()
                    curve.keyframe_points.add(len(values))
                    curve.keyframe_points.foreach_set('co', [v for i, row in enumerate(values)
                                                           for v in (clip['times'][i] * 120, row[field][axis])])
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
                    curve.update()
        action.use_frame_range = True
        action.frame_start = 0.
        action.frame_end = clip['duration'] * 120.
        action['ue_source'] = clip['path']
        action['profile_source'] = str(O / 'profile_reload_grip.json')
        report['clips'].append({'action': action.name, 'source': clip['path'], 'keys': len(clip['times'])})
        if role == 'reload':
            default = action
        print('SVCH_EDITABLE_ACTION', action.name, flush=True)
    target.animation_data.action = default

scene.frame_start = 0
scene.frame_end = 400
scene.frame_set(220)
scene['SVCHReloadGripRuntimeTested'] = False
scene['SVCHReloadGripSource'] = str(O)
dest = O / 'SVCH_R9_ReloadGrip_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
report.update(saved=True, editable_blend=str(dest))
(O / 'editable_source.json').write_text(json.dumps(report, indent=2))
print('SVCH_EDITABLE_SAVED', str(dest), flush=True)
