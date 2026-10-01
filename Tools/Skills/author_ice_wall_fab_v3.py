"""Author thick fractured ice modules for the imported Fab ice maps; no rendering."""
import json
import math
import random
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'SourceAssets/IceWall20260930/FabIceV3'
DEST.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'
manifest = []

for index in range(1, 5):
    rng = random.Random(93030 + index)
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object
    ob.name = f'SM_IceBlock_{index:02d}'
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    # Unequal planar cleavage at the front/back shoulders; retain the central
    # Y/Z bearing faces so the instances form a continuous wall and support top.
    for xsign in (-1, 1):
        for axis in (1, 2):
            for sign in (-1, 1):
                normal = Vector((xsign, 0, 0))
                normal[axis] = sign * rng.uniform(.45, .85)
                distance = .5 + abs(normal[axis]) * .5 - rng.uniform(.025, .085)
                result = bmesh.ops.bisect_plane(
                    bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                    dist=1e-6, plane_co=normal * (distance / normal.length_squared),
                    plane_no=normal, clear_outer=True)
                cut_edges = [e for e in result['geom_cut'] if isinstance(e, bmesh.types.BMEdge) and e.is_boundary]
                if cut_edges:
                    bmesh.ops.holes_fill(bm, edges=cut_edges)
        # One asymmetric corner fracture, rather than a uniform rounded bevel.
        normal = Vector((xsign, rng.choice((-1, 1)) * .7, rng.choice((-1, 1)) * .65))
        distance = .5 + .35 + .325 - rng.uniform(.09, .17)
        result = bmesh.ops.bisect_plane(
            bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-6,
            plane_co=normal * (distance / normal.length_squared), plane_no=normal, clear_outer=True)
        cut_edges = [e for e in result['geom_cut'] if isinstance(e, bmesh.types.BMEdge) and e.is_boundary]
        if cut_edges:
            bmesh.ops.holes_fill(bm, edges=cut_edges)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(ob.data)
    bm.free()
    bevel = ob.modifiers.new('SmallCleavageHighlights', 'BEVEL')
    bevel.width = .0018
    bevel.segments = 2
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = .35
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=3, use_grid_fill=True)
    # Subtle broad melt relief on the main faces, fading before each bearing edge.
    for v in bm.verts:
        x, y, z = v.co
        if abs(x) > .498:
            envelope = max(0, 1 - (abs(y) / .5) ** 4) * max(0, 1 - (abs(z) / .5) ** 4)
            relief = (.004 + .004 * math.sin(y * 5.3 + index) * math.cos(z * 4.7 - index)) * envelope
            v.co.x -= math.copysign(relief, x)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(ob.data)
    bm.free()
    mesh = ob.data
    mesh.update()
    adjacent = [[] for _ in mesh.vertices]
    for face in mesh.polygons:
        face.use_smooth = True
        for vi in face.vertices:
            adjacent[vi].append(face)
    normals = []
    uv = mesh.uv_layers.new(name='IceMeters')
    frost = mesh.color_attributes.new(name='Frost', type='BYTE_COLOR', domain='CORNER')
    for face in mesh.polygons:
        n = face.normal
        axis = max(range(3), key=lambda a: abs(n[a]))
        a, b = ((1, 2), (0, 2), (0, 1))[axis]
        for li in face.loop_indices:
            vi = mesh.loops[li].vertex_index
            co = mesh.vertices[vi].co
            average = Vector((0, 0, 0))
            for other in adjacent[vi]:
                if n.dot(other.normal) > math.cos(math.radians(32)):
                    average += other.normal * other.area
            normals.append(tuple(average.normalized()))
            uv.data[li].uv = (co[a] + .5, co[b] + .5)
            edge = max(0, min(1, (max(abs(co.y), abs(co.z)) - .445) / .055))
            patch = .5 + .5 * math.sin(co.y * 11 + co.z * 7 + index * 1.7)
            frost.data[li].color = (edge * patch * .45, max(0, co.z - .26) * patch, 0, 1)
    mesh.normals_split_custom_set(normals)
    bpy.ops.export_scene.fbx(
        filepath=str(DEST / (ob.name + '.fbx')), use_selection=True,
        object_types={'MESH'}, add_leaf_bones=False, axis_forward='-Y', axis_up='Z',
        apply_unit_scale=True, bake_anim=False, mesh_smooth_type='FACE')
    manifest.append({'mesh': ob.name, 'triangles': len(mesh.polygons),
                     'unit': 'meters', 'interfaces': 'flat center Y/Z bearings; chipped X shoulders',
                     'uv': 'face projection, one repeat per authoring meter'})
    ob.hide_set(True)
    ob.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(DEST / 'IceWallFabV3.blend'))
(DEST / 'geometry.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
