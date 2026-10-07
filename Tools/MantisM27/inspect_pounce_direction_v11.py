"""User-requested offline inspection of blade direction and phase continuity."""
from pathlib import Path
import json
import math
import sys
import bpy
import numpy as np
from mathutils import Vector

BASE = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
REV = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'PounceV11'
OUT = BASE / 'PounceV11/Inspection' / REV
OUT.mkdir(parents=True, exist_ok=True)
source = BASE / REV / 'Delivery' / ('MantisM27_' + REV + '.blend')
if REV == 'PounceV10':
    source = BASE.parents[1] / 'trash/mantis-m27-retired-20261007/SourceAssets/MantisM27/PounceV10/Delivery/MantisM27_PounceV10.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
for track in rig.animation_data.nla_tracks:
    track.mute = True
weights = np.load(BASE / 'BindingV2/binding_weights_v2.npz')
topo = np.load(BASE / 'BindingV2/connected_source.npz')
points = topo['points']
points = np.column_stack((points[:, 0], -points[:, 2], points[:, 1] - points[:, 1].min())) * 100
wi = {n: i for i, n in enumerate(weights['names'])}
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
axes = {}
for side in ['l', 'r']:
    cloud = points[weights['weights'][:, wi['blade_root_' + side]] > .999]
    _, _, vt = np.linalg.svd(cloud - cloud.mean(axis=0), full_matrices=False)
    chord = rest['blade_tip_' + side].translation - rest['blade_root_' + side].translation
    bend = rest['blade_mid_' + side].translation - rest['blade_root_' + side].translation
    bend -= chord * (bend.dot(chord) / chord.length_squared)
    axes[side] = {'normal': Vector(vt[-1]), 'chord': chord.normalized(), 'bend': bend.normalized()}

# Diagnostic clay with individually colored rigid blades: geometry and pose
# come from the actual production source, with no silhouette replacement.
for ob in scene.objects:
    if ob.type not in ['MESH', 'ARMATURE']:
        ob.hide_render = True
    if ob.type == 'MESH' and ob != body:
        ob.hide_render = True
body.hide_render = False
body.data.materials.clear()
for name, color in [('Body', (.40, .43, .46, 1)), ('LeftBlade', (.14, .65, .30, 1)), ('RightBlade', (.60, .24, .70, 1))]:
    mat = bpy.data.materials.new('Inspection_' + name)
    mat.diffuse_color = color
    body.data.materials.append(mat)
vg = {g.index: g.name for g in body.vertex_groups}
labels = []
for v in body.data.vertices:
    best = max(v.groups, key=lambda g: g.weight, default=None)
    name = vg[best.group] if best else ''
    labels.append(1 if name == 'blade_root_l' else 2 if name == 'blade_root_r' else 0)
for p in body.data.polygons:
    ids = [labels[v] for v in p.vertices]
    p.material_index = max(set(ids), key=ids.count)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.show_object_outline = True
scene.display.shading.background_type = 'WORLD'
if not scene.world:
    scene.world = bpy.data.worlds.new('InspectionWorld')
scene.world.color = (.12, .12, .12)
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
cam_data = bpy.data.cameras.new('DirectionInspection')
cam = bpy.data.objects.new('DirectionInspection', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 355
cam_data.clip_end = 2000
target = Vector((0, -40, 137))
report = {'revision': REV, 'basis': 'Blender model: +X anatomical left; -Y forward; +Z up', 'samples': []}
poses = [('PounceWindup', .60), ('PounceFlight', .20), ('PounceFlight', .48),
         ('PounceFlight', .65), ('PounceLand', .0), ('PounceLand', .10)]
for role, t in poses:
    action = bpy.data.actions['A_M27_' + role + '_' + REV]
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(round(t * 60) + 1)
    entry = {'role': role, 'time': t, 'sides': {}}
    lateral = rig.pose.bones['upperarm_l'].matrix.translation - rig.pose.bones['upperarm_r'].matrix.translation
    lateral.z = 0.
    lateral.normalize()
    for side in ['l', 'r']:
        m = rig.pose.bones['blade_root_' + side].matrix
        rotation = m.to_quaternion() @ rest['blade_root_' + side].to_quaternion().inverted()
        entry['sides'][side] = {k: [round(x, 4) for x in rotation @ v] for k, v in axes[side].items()}
        normal = rotation @ axes[side]['normal']
        entry['sides'][side]['blade_plane_error_deg'] = round(math.degrees(math.acos(min(1., abs(normal.dot(lateral))))), 3)
        entry['sides'][side]['joints'] = {part: [round(v, 2) for v in rig.pose.bones[part + '_' + side].matrix.translation]
            for part in ['upperarm', 'lowerarm', 'hand', 'blade_root', 'blade_mid', 'blade_tip']}
        p = {part: rig.pose.bones['blade_' + part + '_' + side].matrix.translation.copy() for part in ['root', 'mid', 'tip']}
        chord = (p['tip'] - p['root']).normalized()
        bend = p['mid'] - p['root']
        bend = (bend - chord * bend.dot(chord)).normalized()
        entry['sides'][side]['helper_axes'] = {'chord': list(chord), 'bend': list(bend)}
    report['samples'].append(entry)
    if '--metrics-only' in sys.argv:
        continue
    for view, location in [('front', (0, -650, 137)), ('side', (650, -40, 137))]:
        cam.location = location
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(OUT / ('%s_%03d_%s.png' % (role, round(t * 1000), view)))
        bpy.ops.render.render(write_still=True)
report['continuity'] = {}
endpoints = {}
for role, count in [('PounceWindup', 37), ('PounceFlight', 40), ('PounceLand', 49)]:
    action = bpy.data.actions['A_M27_' + role + '_' + REV]
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    previous = {}
    maximum = {'degrees': 0., 'side': None, 'frame': None}
    for frame in range(count):
        scene.frame_set(frame + 1)
        for side in ['l', 'r']:
            q = rig.pose.bones['blade_root_' + side].matrix.to_quaternion()
            if side in previous:
                angle = math.degrees(2. * math.acos(min(1., abs(q.dot(previous[side])))))
                if angle > maximum['degrees']:
                    maximum = {'degrees': angle, 'side': side, 'frame': frame}
            previous[side] = q.copy()
            if frame in [0, count - 1]:
                endpoints[(role, frame == 0, side)] = q.copy()
    report['continuity'][role] = maximum
report['boundary_angles_deg'] = {}
for first, second in [('PounceWindup', 'PounceFlight'), ('PounceFlight', 'PounceLand')]:
    report['boundary_angles_deg'][first + '_to_' + second] = {
        side: math.degrees(2. * math.acos(min(1., abs(endpoints[(first, False, side)].dot(endpoints[(second, True, side)])))))
        for side in ['l', 'r']}
(OUT / 'directions.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('M27_DIRECTION_INSPECTION ' + REV, flush=True)
