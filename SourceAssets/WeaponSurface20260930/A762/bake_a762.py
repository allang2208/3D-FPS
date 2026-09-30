"""Blender (background): A762 unique UV1 layout and weapon-surface mask bake.

blender -b --factory-startup -P bake_a762.py

Reads the exact runtime LOD0 geometry dumped by ../dump_mesh_geometry.py. The main
gun's UV0 mostly tiles (rebuilt parts use world-scale box UVs), so masks are baked
into a new non-overlapping UV1; the two folding-sight static meshes already have a
unique UV0 and are baked there. Mask channels: R convex edge, G cavity, B AO,
A exposure (1 - cavity), all linear.

Outputs (Bake/): T_A762_WS_Mask.png (4096, UV1), T_A762_RearSight_WS_Mask.png and
T_A762_FrontSight_WS_Mask.png (1024, UV0), A762_uv1.bin (per-corner UV1, UE V-down
convention, same triangle order as the dump), bake_report.json, A762_SurfaceBake.blend.
"""
import json
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).parent
GEO = HERE.parent / 'inspect' / 'geometry'
OUT = HERE / 'Bake'
OUT.mkdir(exist_ok=True)
EDGE_RADIUS = 0.08   # cm: machined-edge detection radius (~0.8 mm)
CAVITY_AO = 0.5      # cm: hits closer than this count as cavity
BROAD_AO = 3.0       # cm: ambient occlusion reach
RAY_OFFSET = 0.05    # cm: ray start above the surface, skips coincident duplicate shells
RAYS = 40
VERTEX_ATTR = 'WS_Vertex'
MAIN_RES, SIGHT_RES = 4096, 1024
ARM_MARKERS = ('Manny', 'BarePalm', 'BareNative', 'BareFamily')
report = {'inputs': {}, 'objects': {}, 'tested': False}


def read_geometry(path):
    with open(path, 'rb') as f:
        header = json.loads(f.readline().decode('utf-8'))
        V, T = header['vertices'], header['triangles']
        pos = np.fromfile(f, np.float32, V * 3).reshape(V, 3)
        tri = np.fromfile(f, np.int32, T * 3).reshape(T, 3)
        mat = np.fromfile(f, np.int32, T)
        uv = np.fromfile(f, np.float32, T * 6).reshape(T, 3, 2)
        nrm = np.fromfile(f, np.float32, T * 9).reshape(T, 3, 3)
    return header, pos, tri, mat, uv, nrm


def build_object(key, offset):
    header, pos, tri, mat, uv, nrm = read_geometry(GEO / (key + '.bin'))
    report['inputs'][key] = {'path': header['path'], 'vertices': header['vertices'], 'triangles': header['triangles'],
                             'position_checksum': float(np.abs(pos).sum())}
    P = pos.astype(np.float64) * np.array([1, -1, 1])  # UE left-handed -> Blender right-handed
    N = nrm.astype(np.float64) * np.array([1, -1, 1])
    T = len(tri)
    # Mirroring reverses winding; keep Blender's geometric normals agreeing with UE's split normals.
    a, b, c = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
    face = np.cross(b - a, c - a)
    agree = float(np.mean(np.einsum('ij,ij->i', face, N.mean(1)) > 0))
    order = [0, 1, 2] if agree >= 0.5 else [0, 2, 1]
    tri_b, uv_b, nrm_b = tri[:, order], uv[:, order], N[:, order]
    me = bpy.data.meshes.new(key)
    me.vertices.add(len(P))
    me.vertices.foreach_set('co', (P + offset).astype(np.float32).ravel())
    me.loops.add(T * 3)
    me.loops.foreach_set('vertex_index', tri_b.ravel())
    me.polygons.add(T)
    me.polygons.foreach_set('loop_start', np.arange(0, T * 3, 3, dtype=np.int32))
    me.polygons.foreach_set('material_index', mat)
    me.update(calc_edges=True)
    layer = me.uv_layers.new(name='UV0')
    uvb = uv_b.reshape(-1, 2).astype(np.float64)
    layer.data.foreach_set('uv', np.stack([uvb[:, 0], 1.0 - uvb[:, 1]], 1).astype(np.float32).ravel())
    me.shade_smooth()
    me.normals_split_custom_set(nrm_b.reshape(-1, 3).tolist())
    for name in header['slots']:
        m = bpy.data.materials.get('BAKE_' + name) or bpy.data.materials.new('BAKE_' + name)
        me.materials.append(m)
    ob = bpy.data.objects.new(key, me)
    bpy.context.scene.collection.objects.link(ob)
    report['objects'][key] = {'winding_agreement': agree, 'flipped_winding': order != [0, 1, 2],
                              'slots': header['slots'], 'order': order}
    return ob, header, order


def select_only(ob):
    bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode != 'OBJECT' else None
    for o in bpy.context.scene.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def arm_slots(header):
    return {i for i, m in enumerate(header['materials']) if m and any(k in m for k in ARM_MARKERS)}


def make_uv1(ob, header):
    me = ob.data
    uv1 = me.uv_layers.new(name='UV1')
    me.uv_layers.active = uv1
    arms = arm_slots(header)
    mats = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('material_index', mats)
    select_only(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    me.polygons.foreach_set('select', ~np.isin(mats, list(arms)))
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0015, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return uv1


def bake_material(mat, handling_exposure=True):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    n, l = nt.nodes, nt.links
    out = n.new('ShaderNodeOutputMaterial')
    emit = n.new('ShaderNodeEmission')
    geo = n.new('ShaderNodeNewGeometry')
    bevel = n.new('ShaderNodeBevel')
    bevel.samples = 8
    bevel.inputs['Radius'].default_value = EDGE_RADIUS
    dot = n.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    l.new(bevel.outputs['Normal'], dot.inputs[0])
    l.new(geo.outputs['Normal'], dot.inputs[1])

    def math_node(op, a, b=None, clamp=False):
        x = n.new('ShaderNodeMath')
        x.operation = op
        x.use_clamp = clamp
        for i, v in enumerate([a, b]):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                x.inputs[i].default_value = v
            else:
                l.new(v, x.inputs[i])
        return x.outputs[0]

    deviation = math_node('SUBTRACT', 1.0, dot.outputs['Value'])
    edge = math_node('MULTIPLY', math_node('SUBTRACT', math_node('MULTIPLY', deviation, 5.0), 0.05), 1.0, True)
    # Occlusion and the convex gate come from the per-vertex pass (vertex_masks): Cycles
    # AO counts coincident duplicate shells (e.g. the reload magazine pair) as occluders.
    attr = n.new('ShaderNodeAttribute')
    attr.attribute_type = 'GEOMETRY'
    attr.attribute_name = VERTEX_ATTR
    split = n.new('ShaderNodeSeparateColor')
    l.new(attr.outputs['Color'], split.inputs[0])
    convex = math_node('MULTIPLY', edge, split.outputs[0], True)
    rgb = n.new('ShaderNodeCombineColor')
    l.new(convex, rgb.inputs[0])
    l.new(split.outputs[1], rgb.inputs[1])
    l.new(split.outputs[2], rgb.inputs[2])
    l.new(rgb.outputs[0], emit.inputs['Color'])
    l.new(emit.outputs[0], out.inputs['Surface'])
    target = n.new('ShaderNodeTexImage')
    n.active = target
    return target, None


def hemisphere(count, rng):
    """Cosine-weighted unit directions around +Z."""
    u1, u2 = rng.random(count), rng.random(count)
    r, phi = np.sqrt(u1), 2 * np.pi * u2
    return np.stack([r * np.cos(phi), r * np.sin(phi), np.sqrt(1 - u1)], 1)


def vertex_masks(ob):
    """Per-vertex (convex gate, cavity, AO) stored as a POINT colour attribute.

    Rays start RAY_OFFSET outside the surface, so exactly coincident or nearly
    coincident duplicate shells do not occlude; convexity comes from mesh dihedrals.
    """
    me = ob.data
    me.update()
    # Buffers match Blender's native element types (float32/int32) so foreach_get takes
    # the raw path; face data is derived here instead of reading computed RNA getters.
    V = len(me.vertices)
    co32 = np.empty(V * 3, np.float32)
    me.vertices.foreach_get('co', co32)
    co = co32.reshape(V, 3).astype(np.float64)
    P = len(me.polygons)
    corner = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', corner)
    corner = corner.reshape(P, 3)
    tri = co[corner]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    fa_area = np.linalg.norm(fn, axis=1)
    fn /= np.maximum(fa_area, 1e-12)[:, None]
    fc = tri.mean(1)
    vn = np.zeros((V, 3))
    for k in range(3):
        np.add.at(vn, corner[:, k], fn * fa_area[:, None])
    vn /= np.maximum(np.linalg.norm(vn, axis=1), 1e-12)[:, None]
    print('A762_SURFACE_STAGE vertex arrays', V, P, flush=True)
    # Dihedral sign per manifold edge: convex when the neighbour lies below this face.
    loop_edge = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('edge_index', loop_edge)
    loop_face = np.repeat(np.arange(P), 3)
    order = np.argsort(loop_edge, kind='stable')
    e_sorted, f_sorted = loop_edge[order], loop_face[order]
    pair = np.nonzero(e_sorted[1:] == e_sorted[:-1])[0]
    e_id, fa, fb = e_sorted[pair], f_sorted[pair], f_sorted[pair + 1]
    angle = np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i', fn[fa], fn[fb]), -1, 1)))
    convex = np.einsum('ij,ij->i', fn[fa], fc[fb] - fc[fa]) < 0
    # Rounded 2-segment bevels turn a 90 deg edge into ~30 deg steps; they still count as
    # convex edges, while densified flat/curved faces (< 10 deg) do not.
    strength = np.clip((angle - 10.0) / 20.0, 0, 1)
    ev = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get('vertices', ev)
    ev = ev.reshape(-1, 2)
    gate = np.zeros(V)
    for side in (0, 1):
        np.maximum.at(gate, ev[e_id, side], np.where(convex, strength, 0.0))
    tree = BVHTree.FromPolygons([tuple(map(float, p)) for p in co], corner.tolist(), all_triangles=True)
    print('A762_SURFACE_STAGE bvh', flush=True)
    rng = np.random.default_rng(1930)
    local = hemisphere(RAYS, rng)
    ao = np.ones(V)
    cav = np.zeros(V)
    up = np.array([0.0, 0.0, 1.0])
    for i in range(V):
        n = vn[i]
        t = np.cross(up if abs(n[2]) < 0.9 else np.array([1.0, 0, 0]), n)
        t /= np.linalg.norm(t)
        b = np.cross(n, t)
        dirs = local[:, :1] * t + local[:, 1:2] * b + local[:, 2:3] * n
        origin = Vector((co[i] + n * RAY_OFFSET).tolist())
        far = near = 0
        for d in dirs:
            hit, _, _, dist = tree.ray_cast(origin, Vector(d.tolist()), BROAD_AO)
            if hit is not None:
                far += 1
                near += dist < CAVITY_AO
        ao[i] = 1 - far / RAYS
        cav[i] = near / RAYS
    cav = np.clip(cav * 1.6, 0, 1) ** 1.2
    attr = me.color_attributes.get(VERTEX_ATTR) or me.color_attributes.new(VERTEX_ATTR, 'FLOAT_COLOR', 'POINT')
    attr.data.foreach_set('color', np.stack([gate, cav, ao, np.ones(V)], 1).astype(np.float32).ravel())
    return {'vertices': V, 'manifold_edges': int(len(e_id)), 'convex_vertex_share': round(float((gate > 0.5).mean()), 4),
            'ao_mean': round(float(ao.mean()), 3), 'cavity_mean': round(float(cav.mean()), 3)}


def bake(ob, image, uv_name):
    me = ob.data
    me.uv_layers.active = me.uv_layers[uv_name]
    for m in me.materials:
        target, _ = bake_material(m)
        target.image = image
        m.node_tree.nodes.active = target
    select_only(ob)
    bpy.ops.object.bake(type='EMIT', margin=8, margin_type='EXTEND', use_clear=True)


def finish(image, path, neutral_uv=None):
    """neutral_uv: UE-convention UV whose 32x32 texel block is forced to edge 0 / cavity 0 /
    AO 1; rebuilt parts without their own mask island point there."""
    w, h = image.size
    px = np.empty(w * h * 4, np.float32)
    image.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    rgb = px[..., :3]
    # 3x3 box filter on the Monte Carlo AO noise; edges keep a narrow footprint.
    pad = np.pad(rgb, ((1, 1), (1, 1), (0, 0)), mode='edge')
    smooth = sum(pad[y:y + h, x:x + w] for y in range(3) for x in range(3)) / 9.0
    rgb = np.concatenate([np.maximum(rgb[..., :1] * 0.6 + smooth[..., :1] * 0.4, 0), smooth[..., 1:]], -1)
    if neutral_uv is not None:
        # Blender image rows run bottom-up; UE V runs top-down.
        cx, cy = int(neutral_uv[0] * w), int((1.0 - neutral_uv[1]) * h)
        rgb[cy - 16:cy + 16, cx - 16:cx + 16] = (0.0, 0.0, 1.0)
    alpha = np.clip(1.0 - rgb[..., 1:2], 0.2, 1.0)
    result = np.clip(np.concatenate([rgb, alpha], -1), 0, 1)
    save = bpy.data.images.new(path.stem, w, h, alpha=True, float_buffer=False)
    save.colorspace_settings.name = 'Non-Color'
    save.alpha_mode = 'STRAIGHT'
    save.pixels.foreach_set(result.ravel())
    save.filepath_raw = str(path)
    save.file_format = 'PNG'
    save.save()
    covered = float((result[..., 2] > 0.0).mean())
    return {'file': path.name, 'size': [w, h], 'mean': [round(float(result[..., i].mean()), 4) for i in range(4)],
            'edge_p99': round(float(np.percentile(result[..., 0], 99)), 4), 'covered': round(covered, 4)}


def setup_cycles():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.render.bake.use_selected_to_active = False
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == 'OPTIX'
        if any(d.use for d in prefs.devices):
            scene.cycles.device = 'GPU'
    except Exception as exc:
        report['device_error'] = str(exc)
    report['device'] = scene.cycles.device
    return scene


def seat_bake_copy(ob, key='A762_AfterSurface'):
    """Moves the arm-free bake copy into the seated idle pose (seated.py) so occlusion is
    computed where the parts really sit; the magazine, bolt and trigger are displaced in
    bind pose. Vertices are matched to the dump by their bind position."""
    import sys
    from mathutils.kdtree import KDTree
    sys.path.insert(0, str(HERE))
    import seated
    _, pos, st, _, _, _, _ = seated.load(key)
    me = ob.data
    V = len(me.vertices)
    co = np.empty(V * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(V, 3).astype(np.float64)
    flip = np.array([1.0, -1.0, 1.0])
    kd = KDTree(len(pos))
    for i, p in enumerate(pos.astype(np.float64) * flip):
        kd.insert(p, i)
    kd.balance()
    new = np.empty_like(co)
    source = np.empty(V, np.int64)
    worst = 0.0
    for i, c in enumerate(co):
        _, j, dist = kd.find(c)
        worst = max(worst, dist)
        new[i] = st[j] * flip
        source[i] = j
    if worst > 1e-3:
        raise RuntimeError('bake copy does not match the dump (%.4f cm)' % worst)
    me.vertices.foreach_set('co', new.astype(np.float32).ravel())
    me.update()
    stats = {'vertices': V, 'moved': int((np.linalg.norm(new - co, axis=1) > 1e-4).sum()), 'match_error_cm': worst}
    return stats, source


NEUTRAL_UV1 = (0.7002, 0.1494)
# Geometry state the full bake reads (dump_mesh_geometry.py / dump_bone_binding.py key).
MAIN_KEY = 'A762_Geometry'
SAMPLE_EDGE = 0.2    # cm: longest edge of the bake copy for the per-vertex occlusion pass


def densify(ob, max_edge=SAMPLE_EDGE, rounds=6):
    """Splits long edges of the bake copy (UVs interpolate linearly, the layout is unchanged)
    so the per-vertex cavity/AO is sampled every ~2 mm on the low-poly rebuilt parts too."""
    import bmesh
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    for _ in range(rounds):
        long_edges = [e for e in bm.edges if e.calc_length() > max_edge]
        if not long_edges:
            break
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(me)
    bm.free()
    me.update()
    return {'faces': len(me.polygons), 'vertices': len(me.vertices)}


if __name__ == '__main__':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = setup_cycles()

    main, main_header, main_order = build_object(MAIN_KEY, np.zeros(3))
    rear, rear_header, _ = build_object('A762_RearSight', np.array([0.0, 2000.0, 0.0]))
    front, front_header, _ = build_object('A762_FrontSight', np.array([0.0, 4000.0, 0.0]))

    print('A762_SURFACE_STAGE objects built', flush=True)
    make_uv1(main, main_header)
    print('A762_SURFACE_STAGE uv1', flush=True)
    # Re-fetch the layer: RNA references taken before an edit/object mode switch are stale
    # (reading them returned garbage and intermittently crashed foreach_get).
    loops = np.empty(len(main.data.loops) * 2, np.float32)
    main.data.uv_layers['UV1'].data.foreach_get('uv', loops)
    loops = loops.astype(np.float64).reshape(-1, 3, 2)[:, np.argsort(main_order)]  # back to the dump's corner order
    ue = np.stack([loops[..., 0], 1.0 - loops[..., 1]], -1).astype(np.float32)
    with open(OUT / 'A762_uv1.bin', 'wb') as f:
        # One buffered stream: ndarray.tofile() on a Python file bypasses its buffer.
        f.write((json.dumps({'triangles': int(ue.shape[0]),
                             'position_checksum': report['inputs'][MAIN_KEY]['position_checksum']}) + '\n').encode('utf-8'))
        f.write(ue.tobytes())

    # Bake copy of the main gun without the arms, so hands neither receive nor cast occlusion.
    bake_main = main.copy()
    bake_main.data = main.data.copy()
    bake_main.name = 'A762_BAKE'
    scene.collection.objects.link(bake_main)
    main.hide_render = True
    main.hide_set(True)
    select_only(bake_main)
    arms = arm_slots(main_header)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    mats = np.empty(len(bake_main.data.polygons), np.int32)
    bake_main.data.polygons.foreach_get('material_index', mats)
    bake_main.data.polygons.foreach_set('select', np.isin(mats, list(arms)))
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete(type='FACE')
    bpy.ops.object.mode_set(mode='OBJECT')

    print('A762_SURFACE_STAGE bake copy', flush=True)
    area = sum(p.area for p in bake_main.data.polygons)
    uvd = np.empty(len(bake_main.data.loops) * 2, np.float32)
    bake_main.data.uv_layers['UV1'].data.foreach_get('uv', uvd)
    uvd = uvd.astype(np.float64).reshape(-1, 3, 2)
    e1, e2 = uvd[:, 1] - uvd[:, 0], uvd[:, 2] - uvd[:, 0]
    uv_area = float(0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]).sum())
    report['uv1'] = {'gun_area_cm2': round(area, 1), 'uv_area': round(uv_area, 4),
                     'uv_per_cm': round(math.sqrt(uv_area / area), 6),
                     'texels_per_cm_at_4096': round(math.sqrt(uv_area / area) * MAIN_RES, 2)}

    for ob, res, name, uv_name in [(bake_main, MAIN_RES, 'T_A762_WS_Mask', 'UV1'),
                                   (rear, SIGHT_RES, 'T_A762_RearSight_WS_Mask', 'UV0'),
                                   (front, SIGHT_RES, 'T_A762_FrontSight_WS_Mask', 'UV0')]:
        for other in [bake_main, rear, front]:
            other.hide_render = other is not ob
        key = MAIN_KEY if ob is bake_main else ob.name
        if ob is bake_main:
            report['objects'][key]['seated'] = seat_bake_copy(ob, MAIN_KEY)[0]
            report['objects'][key]['densified'] = densify(ob)
        report['objects'][key]['vertex_pass'] = vertex_masks(ob)
        print('A762_SURFACE_VERTEX', name, report['objects'][key]['vertex_pass'], flush=True)
        image = bpy.data.images.new(name + '_bake', res, res, alpha=True, float_buffer=True)
        image.colorspace_settings.name = 'Non-Color'
        bake(ob, image, uv_name)
        report['objects'][key]['mask'] = finish(image, OUT / (name + '.png'))
        print('A762_SURFACE_BAKED', name, report['objects'][key]['mask'], flush=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'A762_SurfaceBake.blend'), compress=True)
    (OUT / 'bake_report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
    print('A762_SURFACE_BAKE_DONE', json.dumps(report['uv1']), flush=True)
