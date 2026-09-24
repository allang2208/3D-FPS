"""PKM PSO: extracted scope body on a purpose-built top-rail mount.

Source is the SEAM-REPAIRED PKM PSO assembly (PSOSeamRepair20260923 synchronised the
three PSO1_*_Editable.blend files: only the 15 axis-covering triangles stay on the glass
material, the 340 ring/mechanical triangles use the body material). Building from
PSO_SourceRoot.blend instead is what kept re-introducing the see-through ring, because
that raw source still carries the old all-glass partition.

So: keep the body + lens objects with their repaired per-face materials, drop the
factory side clamp and its adapter pieces, tuck the leftover foot, add a rail clamp /
post / ring, then rebase to the mount-local convention the working PKM optics use.
"""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Matrix, Vector

O = Path(__file__).parent
E = O / 'Exports'
REPAIRED = O / 'before-topmount/PSO1_PKM_Editable.blend'
OLD_DELTA = Vector((0.075, 0.035, 0.035))      # placement baked into the repaired blend
markers = json.loads((O.parent / 'SVDCompletion20260923/authoring.json').read_text())['markers_root_m']

DELTA = Vector((0.002, -0.0313, 0.06135))
SEAT = 0.1124
MOUNT_Y = -0.0793
TUBE_Z = 0.1637
TUBE_R = 0.0203
FOOT_MAX_Z = 0.072
JAW_OUT, JAW_IN = 0.021, 0.0105

bpy.ops.wm.open_mainfile(filepath=str(REPAIRED))
scene = bpy.context.scene
KEEP = ('PSO_ScopeBody', 'PSO_ScopeLens')
optic = []
for ob in list(scene.objects):
    if ob.type != 'MESH':
        continue
    if ob.name in KEEP:
        ob.data.transform(ob.matrix_world)          # bake scene transform into the data
        ob.matrix_world = Matrix.Identity(4)
        ob.data.transform(Matrix.Translation(-OLD_DELTA))   # back to source coordinates
        optic.append(ob)
    else:
        bpy.data.objects.remove(ob, do_unlink=True)
body = next(o for o in optic if 'Body' in o.name)
lens = next(o for o in optic if 'Lens' in o.name)
adaptermat = bpy.data.materials.get('PSO1_PKM_Adapter')
print('KEEP', [o.name for o in optic], 'slots_body', [m.name for m in body.data.materials],
      'slots_lens', [m.name for m in lens.data.materials], 'adapter_mat', bool(adaptermat), flush=True)

bm = bmesh.new(); bm.from_mesh(body.data)
foot = [v for v in bm.verts if v.co.z < FOOT_MAX_Z and -0.095 < v.co.y < 0.05]
print('TUCK_FOOT_VERTS', len(foot), 'of', len(bm.verts), flush=True)
for v in foot:
    v.co.x *= 0.45
    v.co.z = min(v.co.z, 0.079)
# The body mesh also carries the factory clamp's left-hand jaw plates (+X side) further
# up the tube; they read as loose connector blocks. A flat x limit is not enough (the tube
# is a cylinder, so it is narrower off the axis plane) and moving only the far verts left
# spikes where the moved faces met the unmoved ones. So: take every vert outside the tube
# cylinder on that side, add their one-ring neighbours, and project the whole patch onto
# the cylinder - the transition stays continuous, so no burrs remain.
AXIS_Z, R_TUBE_IN = 0.1024, 0.0200
primary = [v for v in bm.verts
           if v.co.x > 0.0195 and -0.16 < v.co.y < 0.06 and v.co.z < 0.135]
patch = set(primary)
for v in primary:
    for e in v.link_edges:
        patch.add(e.other_vert(v))
print('TUCK_LEFT_LUGS', len(primary), 'patch', len(patch), flush=True)
for v in patch:
    dx, dz = v.co.x, v.co.z - AXIS_Z
    r = math.hypot(dx, dz)
    if r > R_TUBE_IN:
        k = R_TUBE_IN / r
        v.co.x = dx * k
        v.co.z = AXIS_Z + dz * k
bm.to_mesh(body.data); bm.free()

for ob in optic:
    ob.data.transform(Matrix.Translation(DELTA))

pieces = []
tile = (.024, .05)


def finish(ob):
    bpy.ops.object.select_all(action='DESELECT'); ob.hide_set(False); ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    ob.data.materials.clear(); ob.data.materials.append(adaptermat)
    bevel = ob.modifiers.new('Machined edges', 'BEVEL'); bevel.width = .0004; bevel.segments = 3
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for f in ob.data.polygons:
        f.use_smooth = True
    weight = ob.modifiers.new('Area normals', 'WEIGHTED_NORMAL'); weight.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier=weight.name)
    tri = ob.modifiers.new('Export triangles', 'TRIANGULATE'); bpy.ops.object.modifier_apply(modifier=tri.name)
    ob.data.transform(ob.matrix_world); ob.matrix_world = Matrix.Identity(4)
    for layer in list(ob.data.uv_layers):
        ob.data.uv_layers.remove(layer)
    uvl = ob.data.uv_layers.new(name='HostCoatingUV')
    for face in ob.data.polygons:
        axis = max(range(3), key=lambda i: abs(face.normal[i])); axes = [i for i in range(3) if i != axis]
        for li in face.loop_indices:
            v = ob.data.vertices[ob.data.loops[li].vertex_index].co
            uvl.data[li].uv = (v[axes[0]] / tile[0] + .5, v[axes[1]] / tile[1] + .5)
    pieces.append(ob); return ob


def cube(name, p, size):
    bpy.ops.mesh.primitive_cube_add(size=1, location=p)
    ob = bpy.context.object; ob.name = name; ob.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(ob)


cube('PKM_ClampPlate', (0.0, MOUNT_Y, SEAT + 0.013), (0.042, 0.058, 0.010))
cube('PKM_ClampJawL', ((JAW_OUT + JAW_IN) / 2, MOUNT_Y, SEAT - 0.004), (JAW_OUT - JAW_IN, 0.058, 0.024))
cube('PKM_ClampJawR', (-(JAW_OUT + JAW_IN) / 2, MOUNT_Y, SEAT - 0.004), (JAW_OUT - JAW_IN, 0.058, 0.024))
cube('PKM_TopPost', (0.0, MOUNT_Y, SEAT + 0.023), (0.024, 0.040, 0.014))
cube('PKM_TopStop', (0.0, MOUNT_Y - 0.031, SEAT + 0.011), (0.034, 0.006, 0.018))
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=TUBE_R + 0.005, depth=0.026,
                                    location=(0.0, MOUNT_Y, TUBE_Z), rotation=(0, math.pi / 2, 0))
ring = bpy.context.object; ring.name = 'PKM_TubeRing'
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=TUBE_R + 0.0005, depth=0.032,
                                    location=(0.0, MOUNT_Y, TUBE_Z), rotation=(0, math.pi / 2, 0))
bore = bpy.context.object
md = ring.modifiers.new('Ring bore', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = bore
bpy.context.view_layer.objects.active = ring
bpy.ops.object.modifier_apply(modifier=md.name)
bpy.data.objects.remove(bore, do_unlink=True)
finish(ring)
for j, dy in enumerate((-0.019, 0.019)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=.0035, depth=.048,
                                        location=(0.0, MOUNT_Y + dy, SEAT - 0.004), rotation=(0, math.pi / 2, 0))
    bolt = bpy.context.object; bolt.name = 'PKM_ClampBolt_%d' % j; finish(bolt)
    for k, dx in enumerate((-JAW_OUT - 0.002, JAW_OUT + 0.002)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=.0055, depth=.004,
                                            location=(dx, MOUNT_Y + dy, SEAT - 0.004), rotation=(0, math.pi / 2, 0))
        head = bpy.context.object; head.name = 'PKM_ClampBoltHead_%d_%d' % (j, k); finish(head)
optic.extend(pieces)

MOUNT_REF = Vector((0.0, MOUNT_Y, SEAT - 0.002))
for ob in optic:
    ob.data.transform(Matrix.Translation(-MOUNT_REF))

canonical = Matrix.Rotation(math.pi / 2, 4, 'Z')
for ob in optic:
    ob.data.transform(canonical)


def marker(key):
    p = canonical @ (Vector(markers[key]) + Vector(DELTA) - MOUNT_REF)
    return [p.x * 100, -p.y * 100, p.z * 100]


sockets = {'AimCenter': marker('WPN_RearSight'), 'AimFront': marker('WPN_FrontSight')}
bpy.ops.object.select_all(action='DESELECT')
for ob in optic:
    ob.hide_set(False); ob.select_set(True)
bpy.context.view_layer.objects.active = optic[0]
E.mkdir(exist_ok=True)
name = 'SM_PSO1_PKM'
bpy.ops.export_scene.fbx(filepath=str(E / (name + '.fbx')), use_selection=True, object_types={'MESH'},
                         axis_forward='-Y', axis_up='Z', bake_anim=False, mesh_smooth_type='FACE', use_tspace=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'PSO1_PKM_Editable.blend'))

report = json.loads((O / 'authoring.json').read_text()) if (O / 'authoring.json').exists() else {'hosts': {}}
report['hosts']['PKM'] = {'mesh': name, 'translation_root_m': list(DELTA), 'sockets_cm': sockets,
                          'bone': 'PKM_Cover', 'frame': 'mount-local: seating plane z=0, clamp centre at origin',
                          'source': 'before-topmount/PSO1_PKM_Editable.blend (seam-repaired partition)',
                          'yaw_degrees': 90, 'relative_scale': .01, 'coating_tile_m': list(tile),
                          'seat_z_m': SEAT, 'tube_axis_z_m': TUBE_Z, 'tube_radius_m': TUBE_R, 'mount_y_m': MOUNT_Y,
                          'extracted': 'PSO_ScopeMount + side adapter dropped; repaired lens/ring partition kept',
                          'triangles': sum(sum(len(f.vertices) - 2 for f in ob.data.polygons) for ob in optic)}
(O / 'authoring.json').write_text(json.dumps(report, indent=2))
print('PSO1_PKM_TOPMOUNT_AUTHORED', json.dumps(sockets), flush=True)
