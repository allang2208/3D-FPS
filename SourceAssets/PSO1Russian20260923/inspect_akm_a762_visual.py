"""See whether AKM/A762 body feet and left jaws poke past the kept side clamp."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTAS = {'AKM': Vector((0.010, -0.035, 0.035)), 'A762': Vector((0.010, -0.015, 0.035))}
AXIS_Z = 0.1024


def src(host, ob, co):
    return (ob.matrix_world @ co) - DELTAS[host]


def run(host):
    bpy.ops.wm.open_mainfile(filepath=str(O / ('PSO1_%s_Editable.blend' % host)))
    body = bpy.data.objects['PSO_ScopeBody']
    mount = bpy.data.objects['PSO_ScopeMount']
    lens = bpy.data.objects['PSO_ScopeLens']
    glass = []
    for p in lens.data.polygons:
        name = lens.data.materials[p.material_index].name
        if 'Glass' not in name:
            continue
        c = sum((src(host, lens, lens.data.vertices[i].co) for i in p.vertices), Vector()) / len(p.vertices)
        glass.append({'y': round(c.y, 4), 'z': round(c.z, 4), 'x': round(c.x, 4), 'area': round(p.area, 6)})
    verts, faces = [], []
    for p in mount.data.polygons:
        n = len(verts)
        for i in p.vertices:
            verts.append(src(host, mount, mount.data.vertices[i].co))
        faces.append(tuple(range(n, n + len(p.vertices))))
    tree = BVHTree.FromPolygons(verts, faces)
    poke = []
    for v in body.data.vertices:
        p = src(host, body, v.co)
        radial = Vector((p.x, 0, p.z - AXIS_Z))
        r = radial.length
        if r < 0.023:
            continue
        direction = radial.normalized()
        origin = Vector((0, p.y, AXIS_Z))
        hit, normal, index, dist = tree.ray_cast(origin, direction, r + 0.05)
        # A hit closer than the vertex means the clamp stands outside this point.
        covered = hit is not None and dist >= r - 0.0004
        if not covered and r > 0.026:
            poke.append({'x': round(p.x, 4), 'y': round(p.y, 4), 'z': round(p.z, 4), 'r': round(r, 4),
                         'hit': None if hit is None else round(dist, 4)})
    # Spikes: a vertex much farther from the axis than every neighbour.
    bm = bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table()
    spikes = []
    for v in bm.verts:
        p = src(host, body, v.co)
        r = math.hypot(p.x, p.z - AXIS_Z)
        nbr = []
        for e in v.link_edges:
            q = src(host, body, e.other_vert(v).co)
            nbr.append(math.hypot(q.x, q.z - AXIS_Z))
        if nbr and r > max(nbr) + 0.004:
            spikes.append({'x': round(p.x, 4), 'y': round(p.y, 4), 'z': round(p.z, 4),
                           'r': round(r, 4), 'nbr_max': round(max(nbr), 4)})
    bm.free()
    # Sliver faces on the body: longest edge / shortest edge.
    slivers = 0
    for p in body.data.polygons:
        me = body.data
        pts = [src(host, body, me.vertices[i].co) for i in p.vertices]
        edges = [(pts[i] - pts[(i + 1) % len(pts)]).length for i in range(len(pts))]
        if min(edges) > 1e-8 and max(edges) / min(edges) > 25 and p.area < 1e-6:
            slivers += 1
    report = {
        'host': host,
        'glass_faces': glass,
        'uncovered_body_verts_beyond_26mm': len(poke),
        'poke_sample': sorted(poke, key=lambda d: -d['r'])[:20],
        'radial_spikes': len(spikes),
        'spike_sample': spikes[:20],
        'sliver_faces': slivers,
    }
    # Clay render, backface culling on, so a real opening reads as a hole.
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 900
    scene.render.film_transparent = False
    sh = scene.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'MATERIAL'
    sh.show_backface_culling = True
    sh.show_cavity = True
    sh.cavity_type = 'BOTH'
    for ob in scene.objects:
        if ob.type == 'MESH':
            ob.hide_render = False
    cam_data = bpy.data.cameras.new('InspectCam')
    cam = bpy.data.objects.new('InspectCam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam_data.lens = 70
    # Scope sits around the placed tube. Frame the clamp junction (source y ~ -0.04).
    delta = DELTAS[host]
    target = Vector((delta.x + 0.015, delta.y - 0.04, delta.z + 0.06))
    views = {
        'side': Vector((0.28, 0.0, 0.02)),
        'front': Vector((0.02, -0.32, 0.04)),
        'three_quarter': Vector((0.22, -0.22, 0.12)),
    }
    for name, offset in views.items():
        cam.location = target + offset
        direction = target - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(OUT / ('%s_%s.png' % (host, name)))
        bpy.ops.render.render(write_still=True)
    return report


reports = [run(h) for h in ('AKM', 'A762')]
(OUT / 'visual.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
print('PSO_VISUAL_DONE', flush=True)
