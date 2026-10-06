"""Geometry-only closeups and contact measurements of the current UE assets."""
import bpy, json
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent
host = json.loads((O / 'host_geometry.json').read_text())
optic = json.loads((O / 'holographic_geometry.json').read_text())
ref = {k: np.array(v) for k, v in host['reference'].items()}
up = ref['WPN_root'][:3, 2]
up /= np.linalg.norm(up)
forward = ref['WPN_FrontSight'][:3, 3] - ref['WPN_RearSight'][:3, 3]
forward -= up * np.dot(up, forward)
forward /= np.linalg.norm(forward)
right = np.cross(up, forward)
right /= np.linalg.norm(right)
origin = ref['WPN_RearSight'][:3, 3] + forward * 1.6 + up * .45
mount = np.eye(4)
mount[:3, :3] = np.stack((forward, right, np.cross(forward, right)), axis=1)
mount[:3, 3] = origin
hv = np.array(host['vertices_cm'])
hv = (np.column_stack((hv, np.ones(len(hv)))) @ np.linalg.inv(mount).T)[:, :3] / 100
ov = np.array(optic['vertices_cm']) / 100
# Return the UE left-handed frame to Blender coordinates for both meshes.
hv[:, 1] *= -1
ov[:, 1] *= -1
host_faces = [t for t, m in zip(host['triangles'], host['materials']) if host['material_paths'][m].split('/')[-1].startswith('M_G18_')]
body_faces = [t for t, m in zip(optic['triangles'], optic['materials']) if optic['slots'][m] == 'M_HoloBody']
seat_faces = [t for t, m in zip(optic['triangles'], optic['materials']) if optic['slots'][m] == 'M_G18_AttachmentFinish']
if not host_faces or not body_faces or not seat_faces:
    raise RuntimeError('Current source material layout no longer identifies the contact surfaces')
trees = {k: BVHTree.FromPolygons(v.tolist(), f, all_triangles=True)
         for k, v, f in (('host', hv, host_faces), ('body', ov, body_faces), ('seat', ov, seat_faces))}


def zhit(tree, x, y, from_above):
    hit = tree.ray_cast(Vector((x, y, .1 if from_above else -.1)), Vector((0, 0, -1 if from_above else 1)))[0]
    return hit.z if hit is not None else None


rows = []
for x in np.linspace(-.0035, .0135, 35):
    for y in np.linspace(-.0098, .0098, 41):
        bottom = zhit(trees['seat'], x, y, False)
        roof = zhit(trees['host'], x, y, True)
        top = zhit(trees['seat'], x, y, True)
        foot = zhit(trees['body'], x, y, False)
        rows.append({'x_mm': x * 1000, 'y_mm': y * 1000,
                     'lower_gap_mm': (bottom - roof) * 1000 if bottom is not None and roof is not None else None,
                     'upper_gap_mm': (foot - top) * 1000 if foot is not None and top is not None else None})
summary = {'source': 'Current UE mesh geometry and current reference bones; mount matches SetM1911Optic',
           'scope': 'static seating, no firing or reload test', 'mount_cm': mount.tolist(), 'samples': len(rows),
           'gap_sign': 'positive = air gap; negative = embed', 'geometry_faces': {
               'gun': len(host_faces), 'optic_body': len(body_faces), 'seat': len(seat_faces)}}
for key in ('lower_gap_mm', 'upper_gap_mm'):
    values = [r[key] for r in rows if r[key] is not None]
    summary[key] = {'valid_samples': len(values), 'missing_samples': len(rows) - len(values),
                    'min': min(values), 'max': max(values), 'median': float(np.median(values)),
                    'air_gap_over_0_1mm_samples': sum(v > .1 for v in values)}
(O / 'seat_measurements.json').write_text(json.dumps({'summary': summary, 'samples': rows}, indent=2))
print(json.dumps(summary), flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
for name, vertices, faces, color in (
    ('Gun', hv, host_faces, (.24, .27, .30, 1)),
    ('OpticHousing', ov, body_faces, (.42, .46, .50, 1)),
    ('SeatHighlighted', ov, seat_faces, (.88, .42, .10, 1)),
):
    mesh = bpy.data.meshes.new(name)
    # Reflecting Y reverses winding from the original UE triangles.
    mesh.from_pydata(vertices.tolist(), [], [tuple(reversed(t)) for t in faces])
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(ob)
    ob.color = color
    for face in mesh.polygons:
        face.use_smooth = True
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'OBJECT'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.show_specular_highlight = False
scene.display.shading.background_type = 'WORLD'
scene.world = bpy.data.worlds.new('InspectionBackground')
scene.world.color = (.055, .065, .080)
scene.render.resolution_x = 1400
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
camera = bpy.data.objects.new('InspectionCamera', bpy.data.cameras.new('InspectionCamera'))
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = 'ORTHO'
camera.data.clip_start = .001
camera.data.clip_end = 10
for name, position, target, size in (
    ('seat_side', (.005, -.13, .006), (.005, 0, -.004), .078),
    ('seat_rear', (-.07, -.085, .030), (.005, 0, -.002), .080),
    ('seat_front', (.080, -.090, .030), (.005, 0, -.002), .080),
    ('seat_front_detail', (.032, -.060, .007), (.0115, -.0075, .0006), .034),
):
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = size
    scene.render.filepath = str(O / (name + '.png'))
    bpy.ops.render.render(write_still=True)
print('G18_SEAT_CLOSEUPS_RENDERED', flush=True)
