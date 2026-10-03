"""Apply body-only cylinder seal to A762+AKM editables; export FBX; verify. No UE import."""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
EXP = O / 'Exports'; EXP.mkdir(exist_ok=True)
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R_IN, R_PATCH, R_OUTER = 0.1024, 0.0200, 0.0202, 0.0265

def under_pierce(body):
    verts = [(body.matrix_world @ v.co) - DELTA for v in body.data.vertices]
    faces = [tuple(p.vertices) for p in body.data.polygons]
    tree = BVHTree.FromPolygons(verts, faces)
    target = Vector((0.0, -0.04, 0.10))
    cam_loc = target + Vector((0.12, -0.05, -0.22))
    direction = (target - cam_loc).normalized()
    z_axis = -direction
    x_axis = z_axis.cross(Vector((0, 0, 1))); x_axis.normalize()
    y_axis = z_axis.cross(x_axis).normalized()
    half_w, half_h, steps = 0.22, 0.14, 90
    pierce = 0
    for iy in range(steps):
        for ix in range(steps):
            u = (ix/(steps-1))*2-1; v = (iy/(steps-1))*2-1
            dir_w = (direction + x_axis*(u*half_w) + y_axis*(v*half_h)).normalized()
            if tree.ray_cast(cam_loc, dir_w, 0.9)[0] is not None:
                continue
            n_hit = 0
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    if dy == 0 and dx == 0: continue
                    if not (0 <= iy+dy < steps and 0 <= ix+dx < steps): continue
                    u2 = ((ix+dx)/(steps-1))*2-1; v2 = ((iy+dy)/(steps-1))*2-1
                    if tree.ray_cast(cam_loc, (direction + x_axis*(u2*half_w) + y_axis*(v2*half_h)).normalized(), 0.9)[0] is not None:
                        n_hit += 1
            if n_hit < 10: continue
            ox, oz = cam_loc.x, cam_loc.z - AXIS_Z
            dx, dz = dir_w.x, dir_w.z
            A = dx*dx + dz*dz; B = 2*(ox*dx + oz*dz); C = ox*ox + oz*oz - R_IN*R_IN
            disc = B*B - 4*A*C
            if A < 1e-12 or disc < 0: continue
            sd = math.sqrt(disc)
            ts = [t for t in [(-B-sd)/(2*A), (-B+sd)/(2*A)] if t > 0.01]
            if not ts: continue
            t = min(ts)
            if tree.ray_cast(cam_loc, dir_w, t - 1e-4)[0] is None:
                pierce += 1
    return pierce

def seal_body(body):
    mw = body.matrix_world.copy(); inv = mw.inverted()
    verts_w = [(mw @ v.co) - DELTA for v in body.data.vertices]
    faces_i = [tuple(p.vertices) for p in body.data.polygons]
    tree = BVHTree.FromPolygons(verts_w, faces_i)

    def gap_at(R, y, adeg, lo=0.75, hi=1.25):
        a = math.radians(adeg)
        ox, oz = math.cos(a), math.sin(a)
        start = Vector((1.7*R*ox, y, AXIS_Z + 1.7*R*oz))
        h = tree.ray_cast(start, Vector((-ox, 0, -oz)), 1.2*R)
        if h[0] is None:
            return True
        hit = h[0]; hx, hz = hit.x, hit.z - AXIS_Z
        hr = math.hypot(hx, hz)
        same = (hx*ox + hz*oz) > 0
        return (not same) or hr < R*lo or hr > R*hi

    bm = bmesh.new(); bm.from_mesh(body.data)
    for v in bm.verts:
        v.co = (mw @ v.co) - DELTA

    def add_cyl_patch(R, y0, y1, a0, a1, ystep=0.0025, astep=3):
        ys = []
        y = y0
        while y <= y1 + 1e-9:
            ys.append(round(y, 4)); y += ystep
        angs = list(range(a0, a1 + 1, astep))
        mask = {(y, ad) for y in ys for ad in angs if gap_at(R, y, ad)}
        dil = set(mask)
        for y, ad in list(mask):
            for dy in (-ystep, 0, ystep):
                for da in (-astep, 0, astep):
                    yy = round(y + dy, 4)
                    if ys[0] <= yy <= ys[-1] and angs[0] <= ad + da <= angs[-1]:
                        dil.add((yy, ad + da))
        vmap = {}
        def V(y, ad):
            key = (y, ad)
            if key in vmap: return vmap[key]
            a = math.radians(ad)
            vv = bm.verts.new(Vector((R*math.cos(a), y, AXIS_Z + R*math.sin(a))))
            vmap[key] = vv; return vv
        for y, ad in dil:
            V(y, ad)
        quads = 0
        for y, ad in list(dil):
            corners = [(y, ad), (y, ad+astep), (round(y+ystep, 4), ad+astep), (round(y+ystep, 4), ad)]
            if not all(c in dil for c in corners):
                continue
            try:
                f = bm.faces.new([V(*c) for c in corners]); f.smooth = True; quads += 1
            except ValueError:
                pass
        return len(mask), len(vmap), quads

    m1, v1, q1 = add_cyl_patch(R_PATCH, -0.095, 0.030, -155, 25)
    m2, v2, q2 = add_cyl_patch(R_OUTER, -0.090, 0.020, -130, 20, ystep=0.003, astep=4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    flipped = 0
    for f in bm.faces:
        c = f.calc_center_median()
        radial = Vector((c.x, 0, c.z - AXIS_Z))
        r = math.hypot(c.x, c.z - AXIS_Z)
        if radial.length > 1e-8 and (abs(r - R_PATCH) < 0.0012 or abs(r - R_OUTER) < 0.0015):
            if f.normal.dot(radial) < 0:
                f.normal_flip(); flipped += 1
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00035)
    for v in bm.verts:
        v.co = inv @ (v.co + DELTA)
    bm.to_mesh(body.data); bm.free(); body.data.update()
    for p in body.data.polygons:
        p.use_smooth = True
    return {'inner': {'mask': m1, 'verts': v1, 'quads': q1},
            'outer': {'mask': m2, 'verts': v2, 'quads': q2},
            'flipped': flipped}

def render_verify(scene, prefix):
    for o in list(scene.objects):
        if o.type == 'CAMERA':
            bpy.data.objects.remove(o, do_unlink=True)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 70
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 1700; scene.render.resolution_y = 1100
    sh = scene.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
    sh.show_backface_culling = True; sh.show_cavity = True; sh.cavity_type = 'BOTH'
    for ob in scene.objects:
        if ob.type == 'MESH':
            keep = ob.name in ('PSO_ScopeBody', 'PSO_ScopeMount', 'PSO_ScopeLens')
            ob.hide_render = not keep; ob.hide_set(not keep)
    target = DELTA + Vector((0.01, -0.04, 0.09))
    for name, off, hide_m in [
        ('%s_under' % prefix, Vector((0.12, -0.05, -0.22)), False),
        ('%s_bodyonly_under' % prefix, Vector((0.12, -0.05, -0.22)), True),
        ('%s_side' % prefix, Vector((0.30, 0.0, 0.03)), False),
    ]:
        bpy.data.objects['PSO_ScopeMount'].hide_render = hide_m
        bpy.data.objects['PSO_ScopeLens'].hide_render = hide_m
        cam.location = target + off
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(OUT / ('A762_%s.png' % name))
        bpy.ops.render.render(write_still=True)

results = {}
for host in ('A762', 'AKM'):
    src = O / ('PSO1_%s_Editable.blend' % host)
    bak = OUT / ('PSO1_%s_Editable.before-bodyseal.blend' % host)
    shutil.copy2(src, bak)
    # confirm still matches before-tuck for A762
    bpy.ops.wm.open_mainfile(filepath=str(src))
    scene = bpy.context.scene
    body = bpy.data.objects['PSO_ScopeBody']
    pierce_before = under_pierce(body)
    v_before, f_before = len(body.data.vertices), len(body.data.polygons)
    mats_before = [m.name if m else None for m in body.data.materials]
    seal = seal_body(body)
    pierce_after = under_pierce(body)
    bpy.ops.wm.save_as_mainfile(filepath=str(src))

    # export optic only
    bpy.ops.object.select_all(action='DESELECT')
    optic = []
    for name in ('PSO_ScopeBody', 'PSO_ScopeLens', 'PSO_ScopeMount'):
        ob = bpy.data.objects.get(name)
        if ob:
            ob.hide_set(False); ob.select_set(True); optic.append(ob)
    bpy.context.view_layer.objects.active = optic[0]
    # export without rewriting world matrices of gun parts
    fbx = EXP / ('SM_PSO1_%s_BodySeal.fbx' % host)
    bpy.ops.export_scene.fbx(
        filepath=str(fbx), use_selection=True, object_types={'MESH'},
        axis_forward='-Y', axis_up='Z', bake_anim=False,
        mesh_smooth_type='FACE', use_tspace=True)

    if host == 'A762':
        render_verify(scene, 'finalseal')

    results[host] = {
        'backup': str(bak),
        'pierce_before': pierce_before,
        'pierce_after': pierce_after,
        'mesh_before': {'v': v_before, 'f': f_before},
        'mesh_after': {'v': len(body.data.vertices), 'f': len(body.data.polygons)},
        'materials': mats_before,
        'seal': seal,
        'fbx': str(fbx),
        'mount_kept': 'PSO_ScopeMount' in bpy.data.objects,
    }

results['ue_import'] = {
    'attempted': False,
    'blocked_reason': 'UnrealEditor process is running; do not kill; commandlet import deferred',
}
(OUT / 'a762_akm_bodyseal_applied.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print('APPLIED', json.dumps(results, indent=2), flush=True)
