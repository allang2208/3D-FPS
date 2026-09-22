"""Split the SVD body and its PSO-1 scope into mechanical parts by regrouping shells.

Nothing is cut: whole shells move between objects, which keeps every surface closed and
every UV intact. Regions come from measurements (Scripts/list_lower_shells.py,
analyze_scope_shells.py):

  rifle body (source frame: muzzle +Y, up +Z, receiver centred on x~0.169)
    charging handle   xmax >= 0.198                       (protrudes right of the receiver)
    magazine          y in [-0.270, -0.130], zmax <= 0.125, x in [0.140, 0.190]
    trigger           y in [-0.300, -0.255], z in [0.055, 0.100], xmax <= 0.190
    safety lever      xmin >= 0.185, z in [0.125, 0.160], thin in x, y in [-0.40, -0.25]

  PSO-1 scope (tube axis at z~0.259, objective at +Y end, eyepiece at -Y end)
    mount             the left-side clamp: xmax <= 0.156 and zmax <= 0.23
    lens              flat optical discs inside the tube: zero thickness along Y,
                      diameter 2-7 cm, centred on the tube axis

Groups are assigned as material slots and split with separate(type='MATERIAL') - reusing
polygon indices after a split is unsafe because Blender rebuilds the arrays.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <case_root>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

BODY_GROUPS = ['SM_SVD_Body', 'SM_SVD_Magazine', 'SM_SVD_Trigger', 'SM_SVD_ChargingHandle',
               'SM_SVD_SafetyLever']
SCOPE_GROUPS = ['SM_SVD_ScopeBody', 'SM_SVD_ScopeMount', 'SM_SVD_ScopeLens']
PART_COLORS = {
    'SM_SVD_Body': (0.30, 0.30, 0.33),
    'SM_SVD_Magazine': (0.95, 0.55, 0.10),
    'SM_SVD_Trigger': (0.95, 0.15, 0.15),
    'SM_SVD_ChargingHandle': (0.15, 0.75, 0.25),
    'SM_SVD_SafetyLever': (0.20, 0.45, 0.95),
    'SM_SVD_ScopeBody': (0.18, 0.18, 0.20),
    'SM_SVD_ScopeMount': (0.95, 0.75, 0.15),
    'SM_SVD_ScopeLens': (0.45, 0.85, 1.0),
}


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def shells(obj):
    mesh = obj.data
    parent = list(range(len(mesh.vertices)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for edge in mesh.edges:
        ra, rb = find(edge.vertices[0]), find(edge.vertices[1])
        if ra != rb:
            parent[rb] = ra
    poly_of = {}
    for poly in mesh.polygons:
        poly_of[poly.index] = find(poly.vertices[0])
    table = {}
    mw = obj.matrix_world
    for poly in mesh.polygons:
        root = poly_of[poly.index]
        entry = table.setdefault(root, {'polys': [], 'min': [1e9] * 3, 'max': [-1e9] * 3})
        entry['polys'].append(poly.index)
        for vi in poly.vertices:
            p = mw @ mesh.vertices[vi].co
            for i in range(3):
                entry['min'][i] = min(entry['min'][i], p[i])
                entry['max'][i] = max(entry['max'][i], p[i])
    return table


def classify_body(entry):
    mn, mx = entry['min'], entry['max']
    cy = (mn[1] + mx[1]) / 2
    cz = (mn[2] + mx[2]) / 2
    if mx[0] >= 0.198:
        return 'SM_SVD_ChargingHandle'
    if -0.270 <= cy <= -0.130 and mx[2] <= 0.125 and mn[0] >= 0.140 and mx[0] <= 0.190:
        return 'SM_SVD_Magazine'
    if -0.300 <= cy <= -0.255 and 0.055 <= cz <= 0.100 and mx[0] <= 0.190:
        return 'SM_SVD_Trigger'
    if mn[0] >= 0.185 and 0.125 <= cz <= 0.160 and (mx[0] - mn[0]) <= 0.012 and -0.40 <= cy <= -0.25:
        return 'SM_SVD_SafetyLever'
    return 'SM_SVD_Body'


def classify_scope(entry):
    mn, mx = entry['min'], entry['max']
    size = [mx[i] - mn[i] for i in range(3)]
    cx = (mn[0] + mx[0]) / 2
    cz = (mn[2] + mx[2]) / 2
    if mx[0] <= 0.156 and mx[2] <= 0.23:
        return 'SM_SVD_ScopeMount'
    # optical discs: flat along the tube axis, circular, centred on the tube axis
    if (size[1] <= 0.0015 and 0.02 <= max(size[0], size[2]) <= 0.07
            and abs(size[0] - size[2]) <= 0.006 and abs(cx - 0.169) <= 0.01
            and abs(cz - 0.259) <= 0.02):
        return 'SM_SVD_ScopeLens'
    return 'SM_SVD_ScopeBody'


def apply_transforms(objs):
    for o in objs:
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.context.view_layer.update()


def split_object(obj, classifier, groups):
    """Assign one material slot per group, then split the object by material."""
    table = shells(obj)
    assignment = {name: [] for name in groups}
    detail = {name: [] for name in groups}
    for root, entry in table.items():
        part = classifier(entry)
        if part not in assignment:
            raise RuntimeError('classifier returned unknown group %r' % part)
        assignment[part].extend(entry['polys'])
        if part != groups[0]:
            detail[part].append({
                'island': root, 'polys': len(entry['polys']),
                'center': [round((entry['max'][i] + entry['min'][i]) / 2, 4) for i in range(3)],
                'size': [round(entry['max'][i] - entry['min'][i], 4) for i in range(3)],
            })
    mesh = obj.data
    mesh.materials.clear()
    slot_of = {}
    for name in groups:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mesh.materials.append(mat)
        slot_of[name] = len(mesh.materials) - 1
    for name in groups:
        for poly_index in assignment[name]:
            mesh.polygons[poly_index].material_index = slot_of[name]

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.mode_set(mode='OBJECT')

    created = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in created:
        if not o.material_slots or not o.material_slots[0].material:
            continue
        slot_name = o.material_slots[0].material.name
        if slot_name in groups:
            o.name = slot_name
            o.data.name = slot_name
    return detail, {name: len(assignment[name]) for name in groups}


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    cfg = json.loads((case / 'Config' / 'svd.json').read_text(encoding='utf-8-sig'))
    target_length = float(cfg['real_world']['length_m'])
    glb = case / 'Source' / 'svd_source.glb'

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    bpy.context.view_layer.update()
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    body = max(meshes, key=lambda o: len(o.data.polygons))
    scope = min(meshes, key=lambda o: len(o.data.polygons))
    body.name = 'SM_SVD_Body'
    body.data.name = 'SM_SVD_Body'
    scope.name = 'SM_SVD_Scope'
    scope.data.name = 'SM_SVD_Scope'
    apply_transforms([body, scope])

    body_detail, body_counts = split_object(body, classify_body, BODY_GROUPS)
    scope_detail, scope_counts = split_object(scope, classify_scope, SCOPE_GROUPS)
    print('CLASSIFY body', json.dumps(body_counts))
    print('CLASSIFY scope', json.dumps(scope_counts))

    parts = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    expected = set(BODY_GROUPS) | set(SCOPE_GROUPS)
    names = {o.name for o in parts}
    missing = expected - names
    if missing:
        raise RuntimeError('missing parts after split: %s (have %s)' % (sorted(missing), sorted(names)))

    apply_transforms(parts)
    mn0, mx0 = bounds(parts)
    scale = target_length / (mx0.y - mn0.y)
    for o in parts:
        o.rotation_euler = (0.0, 0.0, math.radians(180.0))
        o.scale = (scale, scale, scale)
    bpy.context.view_layer.update()
    apply_transforms(parts)
    mn1, mx1 = bounds(parts)
    shift = Vector((-(mn1.x + mx1.x) / 2.0, -(mn1.y + mx1.y) / 2.0, -(mn1.z + mx1.z) / 2.0))
    for o in parts:
        o.location = shift
    bpy.context.view_layer.update()
    apply_transforms(parts)

    receipt = {'scale_factor': round(scale, 8), 'method': 'shell regrouping (no cutting)',
               'body_regions': body_detail, 'scope_regions': scope_detail, 'parts': {}}
    outdir = case / 'Authored'
    outdir.mkdir(parents=True, exist_ok=True)
    total = 0
    for o in sorted(parts, key=lambda m: m.name):
        o.data.calc_loop_triangles()
        mn, mx = bounds([o])
        fbx = outdir / (o.name + '.fbx')
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
                                 axis_forward='-Y', axis_up='Z', bake_anim=False,
                                 mesh_smooth_type='FACE', use_tspace=True, add_leaf_bones=False)
        tris = len(o.data.loop_triangles)
        total += tris
        receipt['parts'][o.name] = {
            'fbx': str(fbx), 'tris': tris, 'verts': len(o.data.vertices),
            'size_m': [round(mx[i] - mn[i], 5) for i in range(3)],
            'bbox_min': [round(v, 5) for v in mn], 'bbox_max': [round(v, 5) for v in mx],
        }
        print('PART %-26s tris=%-6d size=%s' % (o.name, tris, receipt['parts'][o.name]['size_m']))
    receipt['total_tris'] = total
    bpy.ops.wm.save_as_mainfile(filepath=str(outdir / 'SVD_Mechanical.blend'))

    for o in parts:
        mat = bpy.data.materials.new('v_' + o.name)
        mat.use_nodes = True
        colour = PART_COLORS.get(o.name, (0.9, 0.9, 0.2))
        mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*colour, 1)
        mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.55
        o.data.materials.clear()
        o.data.materials.append(mat)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 18
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1500
    scene.render.resolution_y = 700
    world = bpy.data.worlds.new('W4')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.25, 0.26, 0.28, 1)
    sun = bpy.data.objects.new('Sun4', bpy.data.lights.new('Sun4', type='SUN'))
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(52), 0, math.radians(38))
    scene.collection.objects.link(sun)
    cam_data = bpy.data.cameras.new('Cam4')
    cam_data.type = 'ORTHO'
    cam = bpy.data.objects.new('Cam4', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    prev = case / 'Previews' / 'mechanical'
    prev.mkdir(parents=True, exist_ok=True)
    for name, centre, ortho, direction, rot in [
        ('parts_full', (0.0, 0.0, -0.02), 1.35, (1, 0, 0), (math.radians(90), 0, math.radians(90))),
        ('parts_receiver', (0.0, 0.10, -0.04), 0.62, (1, 0, 0), (math.radians(90), 0, math.radians(90))),
        ('parts_quarter', (0.0, 0.05, -0.02), 0.75, (0.85, -0.45, 0.28), (math.radians(72), 0, math.radians(59))),
        ('scope_side', (0.0, 0.02, 0.10), 0.45, (1, 0, 0), (math.radians(90), 0, math.radians(90))),
        ('scope_front', (0.0, 0.02, 0.10), 0.30, (0.6, 0.75, 0.2), (math.radians(80), 0, math.radians(38))),
    ]:
        cam.data.ortho_scale = ortho
        cam.location = Vector(centre) + Vector(direction) * 4.0
        cam.rotation_euler = rot
        scene.render.filepath = str(prev / name)
        bpy.ops.render.render(write_still=True)

    (case / 'Receipts' / 'parts.json').write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')
    print('SEPARATE_SVD_DONE total_tris=%d parts=%d' % (total, len(receipt['parts'])))


main()
