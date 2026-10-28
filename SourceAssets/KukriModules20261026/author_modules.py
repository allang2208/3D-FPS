"""Split the accepted Kukri into factory modules without changing its grip or silhouette.

Blender background authoring only: preserves original UVs and corner normals, seals
the two mating cuts, exports FBX and a complete editable assembly. No preview/test.
"""
import bpy
import json
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

P = Path(__file__).resolve().parent
SOURCE = P.parent / 'Kukri20261020' / 'Kukri_Editable.blend'
DEST = '/Game/Weapons/Kukri20261020/Modules20261026'
CUT = -0.075  # metres: below the accepted fist, above the flared butt / lanyard hole
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
source = bpy.data.objects['SM_Kukri']
mesh = source.data
normals = [Vector(n.vector) for n in mesh.corner_normals]
uvs = mesh.uv_layers.active.data
adj = [set() for _ in mesh.vertices]
for e in mesh.edges:
    a, b = e.vertices
    adj[a].add(b)
    adj[b].add(a)
unseen = set(range(len(mesh.vertices)))
islands = []
while unseen:
    seed = unseen.pop()
    group, todo = {seed}, [seed]
    while todo:
        neighbors = adj[todo.pop()] & unseen
        unseen -= neighbors
        group |= neighbors
        todo.extend(neighbors)
    islands.append(group)
# Identify the source surfaces by geometry, not a material/vertex ordering.
steel = max(islands, key=lambda g: max(mesh.vertices[i].co.z for i in g))
cord = min(islands, key=lambda g: min(mesh.vertices[i].co.z for i in g))
wood = next(g for g in islands if g is not steel and g is not cord)
ids = {v: name for name, group in [('steel', steel), ('wood', wood), ('cord', cord)] for v in group}
faces = {name: [] for name in ('steel', 'wood', 'cord')}
for poly in mesh.polygons:
    corners = [(mesh.vertices[mesh.loops[i].vertex_index].co.copy(), uvs[i].uv.copy(), normals[i].copy()) for i in poly.loop_indices]
    faces[ids[poly.vertices[0]]].append(corners)

def clip(poly, above):
    out = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        da, db = a[0].z - CUT, b[0].z - CUT
        ina, inb = (da >= 0, db >= 0) if above else (da <= 0, db <= 0)
        if ina:
            out.append(a)
        if ina != inb:
            t = da / (da - db)
            co = a[0].lerp(b[0], t)
            co.z = CUT
            out.append((co, a[1].lerp(b[1], t), a[2].lerp(b[2], t).normalized()))
    return out

def split_closed(polys, above):
    """Clip triangles with interpolated corner data; add caps only on the new cut."""
    result = []
    boundary = {}
    positions = {}
    def key(p):
        return tuple(round(v, 7) for v in p)
    for poly in polys:
        cut = clip(poly, above)
        if len(cut) < 3:
            continue
        result.append(cut)
        for a, b in zip(cut, cut[1:] + cut[:1]):
            if abs(a[0].z - CUT) < 1e-8 and abs(b[0].z - CUT) < 1e-8:
                ka, kb = key(a[0]), key(b[0])
                if ka == kb:
                    continue
                positions[ka], positions[kb] = a, b
                boundary.setdefault(ka, set()).add(kb)
                boundary.setdefault(kb, set()).add(ka)
    remaining = set(boundary)
    loops = []
    while remaining:
        start = next(iter(remaining))
        loop, previous, current = [], None, start
        while True:
            loop.append(current)
            remaining.discard(current)
            following = next(k for k in boundary[current] if k != previous)
            previous, current = current, following
            if current == start:
                break
        loops.append(loop)
    n = Vector((0, 0, -1 if above else 1))
    for loop in loops:
        coords = [positions[k][0] for k in loop]
        center = sum(coords, Vector()) / len(coords)
        uv_center = sum((positions[k][1] for k in loop), Vector((0, 0))) / len(loop)
        # This cut is above the stock through-hole, so each surface has a simple ring.
        for tri in tessellate_polygon([coords]):
            tri = [coords[i] for i in tri] if isinstance(tri[0], int) else list(tri)
            if (tri[1] - tri[0]).cross(tri[2] - tri[0]).dot(n) < 0:
                tri.reverse()
            # New cap faces get a non-degenerate planar UV patch. Surface UVs above
            # were interpolated directly from the source and remain unchanged.
            result.append([(p.copy(), uv_center + Vector((p.x-center.x, p.y-center.y))*2, n.copy()) for p in tri])
    return result, [[list(positions[k][0] * 100) for k in loop] for loop in loops]

steel_upper, steel_ring = split_closed(faces['steel'], True)
steel_tail, _ = split_closed(faces['steel'], False)
wood_upper, wood_ring = split_closed(faces['wood'], True)
wood_tail, _ = split_closed(faces['wood'], False)
# The attachment point is the top centre of the existing cord loop, not its bounds centre.
cord_top = max(mesh.vertices[i].co.z for i in cord)
cord_anchor = sum((mesh.vertices[i].co for i in cord if mesh.vertices[i].co.z > cord_top - .0006), Vector())
cord_anchor /= sum(1 for i in cord if mesh.vertices[i].co.z > cord_top - .0006)
origins = {'blade_1': Vector(), 'grip': Vector(), 'pommel': Vector((0, 0, CUT)), 'lanyard': cord_anchor}
specs = {'blade_1': steel_upper, 'grip': wood_upper, 'pommel': wood_tail + steel_tail, 'lanyard': faces['cord']}
names = {'blade_1': 'Blade', 'grip': 'Grip', 'pommel': 'Pommel', 'lanyard': 'Lanyard'}
receipt = {'source': str(SOURCE), 'cut_z_cm': CUT * 100, 'parts': {}, 'interfaces': {'steel_pommel_ring_cm': steel_ring, 'wood_pommel_ring_cm': wood_ring}, 'runtime_tested': False}
out = P / 'Export'
out.mkdir(parents=True, exist_ok=True)
for slot, polygons in specs.items():
    verts, lookup, indices, corner_data = [], {}, [], []
    origin = origins[slot]
    for poly in polygons:
        ix = []
        for co, uv, normal in poly:
            key = tuple(round(v, 7) for v in co)
            if key not in lookup:
                lookup[key] = len(verts)
                verts.append(tuple(co - origin))
            ix.append(lookup[key])
        if len(set(ix)) < 3:
            continue
        indices.append(ix)
        corner_data.extend((uv, normal) for co, uv, normal in poly)
    name = 'SM_Kukri_' + names[slot] + '_Factory'
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], indices)
    data.materials.append(mesh.materials[0])
    data.update()
    layer = data.uv_layers.new(name='UVMap')
    for i, (uv, normal) in enumerate(corner_data):
        layer.data[i].uv = uv
    for poly in data.polygons:
        poly.use_smooth = True
    data.normals_split_custom_set([tuple(n) for uv, n in corner_data])
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(out / (name + '.fbx')), use_selection=True, object_types={'MESH'},
        mesh_smooth_type='FACE', use_tspace=True, path_mode='STRIP', apply_unit_scale=True,
        bake_space_transform=False, add_leaf_bones=False)
    obj.location = origin
    receipt['parts'][slot] = {'mesh': DEST + '/' + name + '.' + name, 'origin_cm': list(origin * 100),
        'triangles': sum(len(p.vertices) - 2 for p in data.polygons), 'fbx': str(out / (name + '.fbx'))}
source.hide_render = True
source.hide_set(True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'Kukri_Modules_Editable.blend'))
(P / 'modules.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('KUKRI_MODULES_AUTHORED ' + json.dumps(receipt['parts']))
