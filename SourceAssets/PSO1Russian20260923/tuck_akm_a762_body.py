"""Tuck leftover PSO body feet and left jaws on AKM and A762.

Same rule as the PKM extraction: project the patch, including one ring of
neighbours, onto the tube cylinder. Do not delete faces and do not fill holes.
The side clamp, lens partition, adapter and aim sockets stay where they are.
"""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Matrix, Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTAS = {'AKM': Vector((0.010, -0.035, 0.035)), 'A762': Vector((0.010, -0.015, 0.035))}
AXIS_Z, R_TUBE_IN, FOOT_MAX_Z = 0.1024, 0.0200, 0.072


def render(host, tag):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 900
    sh = scene.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'MATERIAL'
    sh.show_backface_culling = True
    sh.show_cavity = True
    sh.cavity_type = 'BOTH'
    cam = bpy.data.objects.get('InspectCam')
    if cam is None:
        cam = bpy.data.objects.new('InspectCam', bpy.data.cameras.new('InspectCam'))
        scene.collection.objects.link(cam)
        cam.data.lens = 70
    scene.camera = cam
    delta = DELTAS[host]
    target = Vector((delta.x + 0.015, delta.y - 0.04, delta.z + 0.06))
    cam.location = target + Vector((0.22, -0.22, 0.12))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('%s_%s.png' % (host, tag)))
    bpy.ops.render.render(write_still=True)


def tuck(host):
    src = O / ('PSO1_%s_Editable.blend' % host)
    backup = OUT / ('PSO1_%s_Editable.before-tuck.blend' % host)
    if not backup.exists():
        shutil.copy2(src, backup)
    bpy.ops.wm.open_mainfile(filepath=str(src))
    body = bpy.data.objects['PSO_ScopeBody']
    before_bounds = len(body.data.vertices), len(body.data.polygons)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    boundary_before = sum(1 for e in bm.edges if e.is_boundary)
    mw = body.matrix_world.copy()
    inv = mw.inverted()
    delta = DELTAS[host]
    for v in bm.verts:
        v.co = (mw @ v.co) - delta
    foot = [v for v in bm.verts if v.co.z < FOOT_MAX_Z and -0.095 < v.co.y < 0.05]
    for v in foot:
        v.co.x *= 0.45
        v.co.z = min(v.co.z, 0.079)
    primary = [v for v in bm.verts if v.co.x > 0.0195 and -0.16 < v.co.y < 0.06 and v.co.z < 0.135]
    patch = set(primary)
    for v in primary:
        for e in v.link_edges:
            patch.add(e.other_vert(v))
    moved = 0
    for v in patch:
        dx, dz = v.co.x, v.co.z - AXIS_Z
        r = math.hypot(dx, dz)
        if r > R_TUBE_IN:
            k = R_TUBE_IN / r
            v.co.x = dx * k
            v.co.z = AXIS_Z + dz * k
            moved += 1
    for v in bm.verts:
        v.co = inv @ (v.co + delta)
    boundary_after = sum(1 for e in bm.edges if e.is_boundary)
    if boundary_after != boundary_before:
        raise RuntimeError('tuck opened or closed edges %s %s' % (boundary_before, boundary_after))
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    render(host, 'after_tuck')
    bpy.ops.wm.save_as_mainfile(filepath=str(src))
    return {'host': host, 'verts_faces': before_bounds, 'foot': len(foot), 'primary': len(primary),
            'patch': len(patch), 'projected': moved, 'boundary': boundary_after}


report = [tuck(h) for h in ('AKM', 'A762')]
(OUT / 'tuck_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PSO_TUCK_DONE', json.dumps(report), flush=True)
