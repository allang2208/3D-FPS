"""Editable Blender source: five ClothReload44 actions on the ClothFeed33 rig scene.

blender -b --factory-startup --python author_scene.py
The scene's gun parts are the Install30 authoring shells (for context only);
the saved UE body is SurfaceReform42.  Tracks are the exact authored keys.
"""
import bpy, json, gzip
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

O = Path(__file__).parent
C33 = O.parent / 'ClothFeed33'
d = json.loads((C33 / 'inputs.json').read_text())['meshes']['201']
info = json.loads((O / 'motion.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(C33 / 'LMG201_Cloth33_Editable.blend'), use_scripts=False)
bpy.context.preferences.filepaths.save_version = 0
rig = bpy.data.objects['SK_M4_Infima']
rig.data.pose_position = 'POSE'
rig.animation_data_create()
names = d['names']
parents = {n: names[i] if i >= 0 else None for n, i in zip(names, d['parents'])}


def ue(v):
    return Matrix.LocRotScale(Vector(v[:3]), Quaternion((v[6], v[3], v[4], v[5])), Vector(v[7:10]))


def blender(m):
    p, q, s = m.decompose()
    return Matrix.LocRotScale(Vector((p.x, -p.y, p.z)) * .01, Quaternion((q.w, -q.x, q.y, -q.z)), s * .01)


rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
localrest = {b.name: b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local.copy() for b in rig.data.bones}
sc = bpy.context.scene
count = round(info['phases']['duration'] * 120) + 1
sc.render.fps, sc.frame_start, sc.frame_end = 120, 0, count - 1
# normal and empty clips, both with the BeltFit53 belt/link patch as installed
for family in [f + e for f in ('base', 'vertical', 'canted', 'prism', 'angled') for e in ('', '_empty')]:
    with gzip.open(O / 'Tracks' / (family + '_b53_tracks.json.gz'), 'rt', encoding='utf8') as f:
        tracks = json.load(f)
    action = bpy.data.actions.new('A_LMG201_Reload44_' + family)
    rig.animation_data.action = action
    rig.pose.bones['WPN_root'].keyframe_insert(data_path='location', frame=0)
    bag = action.layers[0].strips[0].channelbags[0]
    for curve in list(bag.fcurves):
        bag.fcurves.remove(curve)
    rows = {n: [] for n in rest}
    last = {}
    for i in range(count):
        worlds = {}
        for n in names:
            m = ue(tracks[n][i])
            worlds[n] = worlds[parents[n]] @ m if parents[n] else m
        targets = {n: blender(worlds[n]) for n in rest}
        for n in rest:
            parent = rig.data.bones[n].parent
            m = localrest[n].inverted() @ (targets[parent.name].inverted() @ targets[n] if parent else targets[n])
            p, q, s = m.decompose()
            if n in last and q.dot(last[n]) < 0:
                q.negate()
            last[n] = q.copy()
            rows[n].append((tuple(p), tuple(q), tuple(s)))
    for n, values in rows.items():
        rig.pose.bones[n].rotation_mode = 'QUATERNION'
        for prop, components, col in [('location', 3, 0), ('rotation_quaternion', 4, 1), ('scale', 3, 2)]:
            for j in range(components):
                curve = bag.fcurves.new(data_path='pose.bones["' + n + '"].' + prop, index=j)
                curve.keyframe_points.add(len(values))
                curve.keyframe_points.foreach_set('co', [x for i, v in enumerate(values) for x in (i, v[col][j])])
                for k in curve.keyframe_points:
                    k.interpolation = 'LINEAR'
                curve.update()
    action.use_fake_user = True
    print('RELOAD44_EDITABLE_ACTION', family, flush=True)
for a in list(bpy.data.actions):
    if a.name.startswith('A_LMG201_Cloth33_'):
        a.use_fake_user = False
        bpy.data.actions.remove(a)
rig.animation_data.action = bpy.data.actions['A_LMG201_Reload44_base']
if rig.animation_data.action.slots:
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
for key in ['cover_open', 'box_out', 'old_hidden', 'new_visible', 'box_seat', 'belt_seat', 'cover_close', 'return_start']:
    sc.timeline_markers.new(key, frame=round(info['phases'][key] * 120))
sc.frame_set(0)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'LMG201_ClothReload44_Animated.blend'))
print('RELOAD44_ANIMATED_SOURCE_SAVED', flush=True)
