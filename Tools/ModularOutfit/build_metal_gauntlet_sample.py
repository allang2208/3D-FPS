"""Author the stage-one right steel gauntlet in background Blender.

Uses the accepted V7-fitted full leather glove and M4 native rest skeleton.
Creates source geometry and an import payload; no renders or runtime changes.
All geometric authoring measurements below are in centimetres in UE space.
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from original_leather_gloves import PROJECT as P, read, write
import build_tailored_fingerless_candidate as leather

R = P / 'SourceAssets/MetalGauntlet20260927/RightSampleV1'
DONOR = P / 'SourceAssets/ModularOutfit20260927/OriginalLeatherV2/Baked/M4.json'
LEATHER = P / 'SourceAssets/ModularOutfit20260927/OriginalLeatherV2/Textures/M4'
MATERIAL = dict(base_color=[.32, .35, .38, 1.], metallic=1., roughness=.34)
PLATE_THICKNESS = .09
PLATE_GAP = .16
PARTS = []


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def to_blender(v):
    return Vector((v[0] * .01, -v[1] * .01, v[2] * .01))


def to_ue(v):
    return [v.x * 100, -v.y * 100, v.z * 100]


def right_liner(source):
    selected = {i for i, w in enumerate(source['weights'])
                if sum(v for n, v in w.items() if n.endswith('_r')) > .5}
    face_ids = [i for i, f in enumerate(source['triangles']) if all(v in selected for v in f)]
    vertex_ids = sorted({v for i in face_ids for v in source['triangles'][i]})
    remap = {v: i for i, v in enumerate(vertex_ids)}
    out = {k: source[k] for k in ('profile', 'source', 'binding_source', 'skeleton', 'base_mesh', 'bones')}
    out.update(positions=[source['positions'][v] for v in vertex_ids],
               weights=[source['weights'][v] for v in vertex_ids],
               triangles=[[remap[v] for v in source['triangles'][i]] for i in face_ids],
               normals=[source['normals'][i] for i in face_ids],
               uv=[source['uv'][i] for i in face_ids], triangle_materials=[0] * len(face_ids))
    return out


def mesh_object(name, positions, faces, material):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_blender(p) for p in positions], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def steel_material():
    mat = bpy.data.materials.new('Steel_StructuralSample')
    mat.use_nodes = True
    mat.diffuse_color = MATERIAL['base_color']
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = MATERIAL['base_color']
    bs.inputs['Metallic'].default_value = MATERIAL['metallic']
    bs.inputs['Roughness'].default_value = MATERIAL['roughness']
    return mat


def make_liner(d):
    maps = {c: leather.image(LEATHER / ('T_OriginalLeather_' + c + '.png'),
                            'sRGB' if c == 'BaseColor' else 'Non-Color')
            for c in ('BaseColor', 'Roughness', 'Normal')}
    mat = leather.baked_material(maps)
    mat.name = 'Accepted_TailoredLeather_Liner'
    obj = mesh_object('Right_LeatherLiner', d['positions'], d['triangles'], mat)
    uv = obj.data.uv_layers.new(name='BakedTailoringUV')
    for poly, coords in zip(obj.data.polygons, d['uv']):
        for li, (u, v) in zip(poly.loop_indices, coords):
            uv.data[li].uv = (u, 1 - v)
    obj.data.normals_split_custom_set([(n[0], -n[1], n[2]) for row in d['normals'] for n in row])
    activate(obj)
    rig = leather.rig(obj, d)
    obj['Construction'] = 'Unchanged fitted full-finger right leather liner; original soft weights'
    return obj, rig


def attach_rigid(obj, rig, bone):
    group = obj.vertex_groups.new(name=bone)
    group.add(list(range(len(obj.data.vertices))), 1., 'REPLACE')
    obj.parent = rig
    modifier = obj.modifiers.new('NativeRigidBinding', 'ARMATURE')
    modifier.object = rig
    obj['RigidBone'] = bone
    obj['WeightRule'] = 'Every vertex 100 percent to this bone; no gradient skin transfer'


def surface_object(name, grid, dorsal, bone, rig, mat, thickness=PLATE_THICKNESS):
    rows, cols = grid.shape[:2]
    positions = grid.reshape((-1, 3)).tolist()
    faces = []
    for y in range(rows - 1):
        for x in range(cols - 1):
            a = y * cols + x
            faces.append([a, a + 1, a + cols + 1, a + cols])
    # Reflection from UE to Blender reverses handedness; orient the open shell
    # explicitly before adding its inward wall thickness.
    q = [to_blender(positions[i]) for i in faces[len(faces) // 2]]
    if (q[1] - q[0]).cross(q[2] - q[0]).dot(to_blender(dorsal)) < 0:
        faces = [f[::-1] for f in faces]
    obj = mesh_object(name, positions, faces, mat)
    activate(obj)
    solid = obj.modifiers.new('SteelWall_0p9mm', 'SOLIDIFY')
    solid.thickness = thickness * .01
    solid.offset = -1.
    solid.use_even_offset = True
    bpy.ops.object.modifier_apply(modifier=solid.name)
    bevel = obj.modifiers.new('DressedEdges_0p16mm', 'BEVEL')
    bevel.width = .00016
    bevel.segments = 2
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = .65
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    uv = obj.data.uv_layers.new(name='SteelSampleUV')
    obj.data.uv_layers.active = uv
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=.012, area_weight=.2)
    bpy.ops.object.mode_set(mode='OBJECT')
    attach_rigid(obj, rig, bone)
    obj['WallThicknessCM'] = thickness
    obj['SurfaceGapCM'] = PLATE_GAP
    PARTS.append(dict(name=name, bone=bone, kind='steel_plate', object=obj,
                      thickness_cm=thickness, vertices=len(obj.data.vertices)))
    return obj


def rivet(name, center, normal, bone, rig, mat, radius=.125):
    normal = unit(normal)
    across = unit(np.cross(normal, [0., 0., 1.]) if abs(normal[2]) < .9 else np.cross(normal, [0., 1., 0.]))
    up = np.cross(normal, across)
    vertices = [np.asarray(center) + normal * .065]
    sides = 12
    for r, h in ((.56, .051), (.93, .023), (1., 0.), (.86, -.026)):
        for i in range(sides):
            t = i * math.tau / sides
            vertices.append(np.asarray(center) + normal * h + radius * r * (across * math.cos(t) + up * math.sin(t)))
    vertices.append(np.asarray(center) - normal * .026)
    faces = [[0, 1 + i, 1 + (i + 1) % sides] for i in range(sides)]
    for ring in range(3):
        for i in range(sides):
            a, b = 1 + ring * sides + i, 1 + ring * sides + (i + 1) % sides
            faces.append([a, a + sides, b + sides, b])
    for i in range(sides):
        faces.append([len(vertices) - 1, 1 + 3 * sides + (i + 1) % sides, 1 + 3 * sides + i])
    obj = mesh_object(name, vertices, faces, mat)
    activate(obj)
    # Closed lathed hardware needs consistent outward face orientation.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    uv = obj.data.uv_layers.new(name='SteelSampleUV')
    for poly in obj.data.polygons:
        for li in poly.loop_indices:
            p = obj.data.vertices[obj.data.loops[li].vertex_index].co - to_blender(center)
            uv.data[li].uv = (.5 + p.dot(to_blender(across).normalized()) / (radius * .024),
                              .5 + p.dot(to_blender(up).normalized()) / (radius * .024))
    attach_rigid(obj, rig, bone)
    PARTS.append(dict(name=name, bone=bone, kind='steel_rivet', object=obj,
                      vertices=len(obj.data.vertices)))


def ray_surface(tree, center, radial, reach):
    hit, _, _, _ = tree.ray_cast(Vector(center + radial * reach), Vector(-radial), reach * 2)
    if hit is None:
        raise RuntimeError('No liner surface at authoring coordinate: ' + str(center.tolist()))
    return np.asarray(hit)


def author_back(tree, anatomy, rig, mat):
    wrist = np.asarray(anatomy['wrist'])
    f, x, z = (unit(anatomy[k]) for k in ('forward', 'across', 'dorsal'))
    grid = []
    for v in np.linspace(0., 1., 25):
        row = []
        width = 2.40 + .83 * math.sin(v * math.pi * .70)
        for u in np.linspace(-1., 1., 21):
            # Narrow wrist, a broad metacarpal shield and a rounded knuckle edge.
            px = -.25 + .42 * v + width * u
            py = 1.15 + 6.65 * v - .55 * abs(u) ** 3 * v ** 4 + .30 * u * v ** 3
            center = wrist + x * px + f * py
            top = ray_surface(tree, center, z, 8.)
            keel = .12 * math.exp(-(u / .20) ** 2) * math.sin(math.pi * v)
            row.append(top + z * (PLATE_GAP + keel))
        grid.append(row)
    grid = np.asarray(grid)
    surface_object('Plate_HandBack', grid, z, 'hand_r', rig, mat)
    for i, (row, col) in enumerate(((3, 3), (3, 17), (20, 3), (20, 17))):
        rivet('Rivet_HandBack_%02d' % i, grid[row, col], z, 'hand_r', rig, mat)


def author_cuff(tree, anatomy, rig, mat):
    wrist = np.asarray(anatomy['wrist'])
    f, x, z = (unit(anatomy[k]) for k in ('forward', 'across', 'dorsal'))
    for name, a, b, bone, gap in (
            ('Plate_WristHand', -.48, 1.32, 'hand_r', PLATE_GAP + .03),
            ('Plate_CuffForearm', -3.72, -.68, 'lowerarm_twist_01_r', PLATE_GAP)):
        grid = []
        for v in np.linspace(0., 1., 11):
            row = []
            for angle in np.linspace(-1.43, 1.43, 25):
                radial = unit(z * math.cos(angle) + x * math.sin(angle))
                center = wrist + f * (a + (b - a) * v)
                top = ray_surface(tree, center, radial, 7.)
                lip = .035 * (math.exp(-(v / .10) ** 2) + math.exp(-((1 - v) / .10) ** 2))
                row.append(top + radial * (gap + lip))
            grid.append(row)
        grid = np.asarray(grid)
        surface_object(name, grid, z, bone, rig, mat)
        for i, (row, col) in enumerate(((2, 2), (2, 22))):
            radial = unit(grid[row, col] - (wrist + f * (a + (b - a) * row / 10)))
            rivet(name.replace('Plate', 'Rivet') + '_%02d' % i, grid[row, col], radial, bone, rig, mat)


def author_digit(d, anatomy, digit, rig, mat):
    vertices = np.asarray(d['positions'])
    selected = {i for i, w in enumerate(d['weights']) if sum(v for n, v in w.items() if n.startswith(digit + '_')) > .28}
    faces = [f for f in d['triangles'] if all(i in selected for i in f)]
    tree = BVHTree.FromPolygons([Vector(p) for p in vertices], faces, all_triangles=True)
    for section in (s for s in anatomy['digits'] if s['digit'] == digit):
        bone, segment = section['bone'], section['segment']
        head = np.asarray(d['bones'][bone]['position'])
        axis, dorsal, across = (unit(section[k]) for k in ('axis', 'dorsal', 'across'))
        length = section['length']
        radius = section['radius']
        # Retain the palmward surface and thumb web. The last plate ends before
        # the fingertip pad; the rounded leather tip remains free to contact.
        start = (.42 if digit == 'thumb' and segment == 1 else .12 if segment == 1 else .08) * length
        end = (.81 if segment == 3 else .94) * length
        grid = []
        for v in np.linspace(0., 1., 13):
            row = []
            for u in np.linspace(-1., 1., 17):
                angle = u * (1.02 if digit == 'thumb' and segment == 1 else 1.13)
                radial = unit(dorsal * math.cos(angle) + across * math.sin(angle))
                t = start + (end - start) * v
                # Rounded end corners remove side material near each hinge.
                t += .09 * abs(u) ** 3 * (1 - 2 * v)
                center = head + axis * t
                top = ray_surface(tree, center, radial, max(radius * 3., 3.))
                ridge = .032 * math.exp(-(u / .26) ** 2) * math.sin(math.pi * v)
                row.append(top + radial * (PLATE_GAP + ridge))
            grid.append(row)
        grid = np.asarray(grid)
        name = 'Plate_%s_%02d' % (digit.title(), segment)
        surface_object(name, grid, dorsal, bone, rig, mat)
        for i, col in enumerate((3, 13)):
            radial = unit(dorsal * math.cos((col / 8 - 1) * 1.13) + across * math.sin((col / 8 - 1) * 1.13))
            rivet(name.replace('Plate', 'Rivet') + '_%02d' % i, grid[2, col], radial, bone, rig, mat, radius=.09)
    if digit == 'index':
        # Separate rounded root cap, driven by the proximal phalanx. It sits
        # above its matching finger plate and the distal edge of the hand plate.
        s = next(s for s in anatomy['digits'] if s['bone'] == 'index_01_r')
        head = np.asarray(s['head']); axis = unit(s['axis']); z = unit(s['dorsal']); x = unit(s['across'])
        grid = []
        for v in np.linspace(0., 1., 9):
            row = []
            for u in np.linspace(-1., 1., 17):
                radial = unit(z * math.cos(u * 1.18) + x * math.sin(u * 1.18))
                t = .10 + v * .74
                top = ray_surface(tree, head + axis * t, radial, 3.8)
                row.append(top + radial * (.29 + .045 * math.sin(math.pi * v)))
            grid.append(row)
        surface_object('Plate_IndexKnuckleCap', np.asarray(grid), z, 'index_01_r', rig, mat)


def export_payload(liner):
    d = {k: (list(v) if isinstance(v, list) else v) for k, v in liner.items()}
    manifest = []
    for part in PARTS:
        obj = part['object']; mesh = obj.data
        mesh.calc_loop_triangles()
        base = len(d['positions']); first_face = len(d['triangles'])
        d['positions'].extend(to_ue(v.co) for v in mesh.vertices)
        d['weights'].extend({part['bone']: 1.} for _ in mesh.vertices)
        uv = mesh.uv_layers.active
        normals = mesh.corner_normals
        for face in mesh.loop_triangles:
            d['triangles'].append([base + i for i in face.vertices])
            d['normals'].append([[normals[i].vector.x, -normals[i].vector.y, normals[i].vector.z] for i in face.loops])
            d['uv'].append([[uv.data[i].uv.x, 1 - uv.data[i].uv.y] for i in face.loops])
            d['triangle_materials'].append(1)
        manifest.append({**{k: v for k, v in part.items() if k != 'object'},
                         'first_vertex': base, 'first_triangle': first_face,
                         'triangles': len(mesh.loop_triangles)})
    d['contract'] = 'Stage-one right sample only; original M4 skeleton; soft V7-fitted leather liner plus rigid steel plates; no animation edits'
    d['surface_winding'] = 'ue_native'
    write(R / 'M4_RightGauntletSample.json', d)
    write(R / 'parts.json', dict(stage=1, side='right', profile='M4', parts=manifest,
          liner_triangles=len(liner['triangles']), total_triangles=len(d['triangles']),
          material_slots=['LeatherLiner', 'ArticulatedSteel'], steel_material=MATERIAL,
          source=str(DONOR), new_animations=0, runtime_tested=False, production_equipment=False))


def main():
    R.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    d = right_liner(read(DONOR))
    anatomy = read(P / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']['r']
    liner, rig = make_liner(d)
    mat = steel_material()
    tree = BVHTree.FromPolygons([Vector(p) for p in d['positions']], d['triangles'], all_triangles=True)
    author_back(tree, anatomy, rig, mat)
    author_cuff(tree, anatomy, rig, mat)
    for digit in ('index', 'thumb'):
        author_digit(d, anatomy, digit, rig, mat)
    export_payload(d)
    rig['Stage'] = 'Stage 1 right-hand structural sample; remaining three fingers leather only'
    rig['RuntimeAttachment'] = 'Skeletal equipment follower using existing M4 Leader Pose; preserve native rest skeleton'
    rig.show_in_front = True
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene['Delivery'] = 'Authoring sample, no rendered preview or runtime acceptance'
    # Pack the already accepted liner textures into the editable source.
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    activate(liner)
    bpy.ops.wm.save_as_mainfile(filepath=str(R / 'M4_RightGauntletSample.blend'))
    # Convenience DCC interchange only. UE uses the native JSON binding route.
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(R / 'M4_RightGauntletSample.fbx'), use_selection=True,
        object_types={'MESH', 'ARMATURE'}, add_leaf_bones=False, bake_anim=False,
        use_armature_deform_only=False, mesh_smooth_type='FACE', path_mode='STRIP')
    print('METAL_GAUNTLET_SAMPLE_AUTHORED', str(R), flush=True)


if __name__ == '__main__':
    main()
