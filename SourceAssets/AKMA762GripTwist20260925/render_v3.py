"""Render the shipping round-1 thumb against the proposed natural extension.

  cur  - what ships now: the round-1 root (read from the round-1 blend) with the
         round-1 distal flexion 30/25 (AKM) and 33.5/34.8 (A762)
  v3   - the same root untouched, distal flexion 4/3 (the SVD rule)

Thumb is its own coloured object; the magazine proxy is posed with the magazine
track.  'side2' looks along minus the tilt axis (the side the thumb is on) and
'game' looks along the barrel from behind, roughly the player's view.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
WEB = ['thumb_01_l', 'index_01_l']
FRAME = 148
CASES = {
    'AKM': (S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend',
            O / 'AKM/standard/base/A_AKM_reload.blend'),
    'A762': (S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend',
             O / 'A762/standard/base/A_A762_reload.blend'),
}
FIT = json.loads((O / 'thumb_fit.json').read_text())


def swing_only(q):
    q = q.copy(); q.normalize()
    a = Vector((0.0, 1.0, 0.0))
    p = a * Vector((q.x, q.y, q.z)).dot(a)
    if p.length < 1e-12:
        return q
    tw = 2.0 * math.atan2(p.length, q.w)
    if p.dot(a) < 0:
        tw = -tw
    return q @ Quaternion(a, tw).inverted()


def principal(points):
    c = sum(points, Vector()) / len(points)
    xx = xy = xz = yy = yz = zz = 0.0
    for p in points:
        d = p - c
        xx += d.x * d.x; xy += d.x * d.y; xz += d.x * d.z
        yy += d.y * d.y; yz += d.y * d.z; zz += d.z * d.z
    M = Matrix(((xx, xy, xz), (xy, yy, yz), (xz, yz, zz)))
    v = Vector((M[0][0], M[1][0], M[2][0]))
    for i in (1, 2):
        w = Vector((M[0][i], M[1][i], M[2][i]))
        if w.length > v.length:
            v = w
    return c, v.normalized()


rows = []
for gun, (src, shipped) in CASES.items():
    bpy.ops.wm.open_mainfile(filepath=str(shipped), use_scripts=False)
    r0 = bpy.data.objects['SK_M4_Infima']
    a0 = r0.animation_data.action
    r0.animation_data.action = a0; r0.animation_data.action_slot = a0.slots[0]
    bpy.context.scene.frame_set(FRAME); bpy.context.view_layer.update()
    q_inst = r0.pose.bones['thumb_01_l'].matrix_basis.to_quaternion().copy()

    bpy.ops.wm.open_mainfile(filepath=str(src), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    sc = bpy.context.scene
    sc.frame_set(FRAME); bpy.context.view_layer.update()
    W = r.matrix_world
    D = W @ r.pose.bones['WPN_SOCKET_Magazine'].matrix @ r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted() @ W.inverted()
    proxy = [o for o in sc.objects if o.type == 'MESH' and gun.upper() in o.name.upper() and 'MAG' in o.name.upper()]
    dg = bpy.context.evaluated_depsgraph_get()
    apply_d = False
    if not proxy:
        with bpy.data.libraries.load(str(A762_LIB), link=False) as (lib_src, lib_dst):
            lib_dst.objects = [n for n in lib_src.objects if n.startswith('A762_R02_Magazine_')]
        proxy = [o for o in lib_dst.objects if o is not None]
        for o in proxy:
            sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
        apply_d = True
    mv, mp = [], []
    for o in proxy:
        if not apply_d and any(m.type == 'ARMATURE' for m in o.modifiers):
            e = o.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
            off = len(mv); mv.extend(M @ v.co for v in me.vertices)
            mp.extend([[off + i for i in p.vertices] for p in me.polygons]); e.to_mesh_clear()
        else:
            off = len(mv)
            mv.extend(D @ (o.matrix_world @ v.co) for v in o.data.vertices)
            mp.extend([[off + i for i in p.vertices] for p in o.data.polygons])
    mag_c_p, axis = principal(mv)
    if (r.pose.bones['WPN_root'].head - mag_c_p).dot(axis) < 0:
        axis = -axis
    Wr = W.to_3x3()
    mag_arm = (Wr.inverted() @ axis).normalized()
    v = r.pose.bones['hand_l'].matrix.translation - (Wr.inverted() @ mag_c_p)
    v_perp = (v - v.project(mag_arm)).normalized()
    tilt_axis = mag_arm.cross(v_perp).normalized()
    keep = {n: (lambda dd: (dd[0], dd[2]))(r.pose.bones[n].matrix_basis.decompose()) for n in PARTS}
    p1 = FIT[gun]['params']

    def sample():
        dg = bpy.context.evaluated_depsgraph_get()
        e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
        groups = [g.name for g in arms.vertex_groups]
        cent = {p: [] for p in PARTS + WEB}
        for vv in me.vertices:
            best, w = None, 0.0
            for g in vv.groups:
                if g.weight > w:
                    best, w = groups[g.group], g.weight
            if best in cent:
                cent[best].append(M @ vv.co)
        e.to_mesh_clear()
        return {k: sum(vv, Vector()) / len(vv) for k, vv in cent.items() if vv}

    def split(thumbcol, tag):
        dg = bpy.context.evaluated_depsgraph_get()
        e = arms.evaluated_get(dg); me = e.to_mesh(); AM = e.matrix_world
        groups = [g.name for g in arms.vertex_groups]
        kind = {}
        for vv in me.vertices:
            best, w = None, 0.0
            for g in vv.groups:
                if g.weight > w:
                    best, w = groups[g.group], g.weight
            kind[vv.index] = best
        objs = []
        for nm, want in (('hand', False), ('thumb', True)):
            vmap, pts = {}, []
            for vv in me.vertices:
                b = kind[vv.index]
                if not (b and b.endswith('_l')):
                    continue
                if (b in PARTS) != want:
                    continue
                vmap[vv.index] = len(pts); pts.append(AM @ vv.co)
            pp = [[vmap[i] for i in p.vertices if i in vmap] for p in me.polygons]
            pp = [x for x in pp if len(x) >= 3]
            m = bpy.data.meshes.new(nm + tag); m.from_pydata(pts, [], pp); m.update()
            o = bpy.data.objects.new(nm + tag, m); sc.collection.objects.link(o)
            o.color = (.22, .42, .60, 1) if not want else thumbcol
            objs.append(o)
        e.to_mesh_clear()
        return objs

    variants = [('cur', q_inst, p1['c_02'], p1['d_03'], (.25, .85, .3, 1)),
                ('v3', q_inst, 4.0, 3.0, (.85, .2, .75, 1))]
    for tag, root, c, d, col in variants:
        for n, q in (('thumb_01_l', root),
                     ('thumb_02_l', Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion()),
                     ('thumb_03_l', Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion())):
            r.pose.bones[n].matrix_basis = Matrix.LocRotScale(keep[n][0], q, keep[n][1])
        bpy.context.view_layer.update()
        cent = sample()
        vis = cent['thumb_03_l'] - cent['thumb_01_l']
        gap = (cent['thumb_01_l'] - cent['index_01_l']).length
        P = {b.name: b.matrix.copy() for b in r.pose.bones}
        centre = P['hand_l'].translation
        barrel = (P['WPN_SOCKET_Muzzle'].translation - P['WPN_root'].translation).normalized()
        fwd = (P['middle_01_l'].translation - centre).normalized()
        across = (P['index_01_l'].translation - P['pinky_01_l'].translation).normalized()
        normal = across.cross(fwd).normalized()
        for o in list(sc.objects):
            if o.type == 'MESH':
                o.hide_render = True
        name = '%s_%s' % (gun.lower(), tag)
        objs = split(col, name)
        mm = bpy.data.meshes.new('mag' + name); mm.from_pydata(mv, [], mp); mm.update()
        mo = bpy.data.objects.new('mag' + name, mm); sc.collection.objects.link(mo)
        mo.color = (.80, .55, .18, 1)
        sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'
        sc.display.shading.color_type = 'OBJECT'; sc.display.shading.show_cavity = True
        sc.display.shading.background_type = 'WORLD'
        if not sc.world:
            sc.world = bpy.data.worlds.new('W' + name)
        sc.world.color = (.08, .08, .09)
        sc.render.resolution_x = 900; sc.render.resolution_y = 900; sc.render.resolution_percentage = 100
        sc.render.use_compositing = False; sc.render.use_sequencer = False
        cam = bpy.data.objects.new('cam' + name, bpy.data.cameras.new('cam' + name))
        sc.collection.objects.link(cam); sc.camera = cam
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = .34
        views = [('side', tilt_axis), ('side2', -tilt_axis), ('game', -barrel), ('back', -normal)]
        for vn, u in views:
            cam.location = centre + u * .45
            cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = str(O / ('thumb5_%s_%s.png' % (name, vn)))
            bpy.ops.render.render(write_still=True)
        mo.hide_render = True
        for vn, u in (('side2', -tilt_axis), ('game', -barrel)):
            cam.location = centre + u * .45
            cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = str(O / ('thumb5_%s_%s_nomag.png' % (name, vn)))
            bpy.ops.render.render(write_still=True)
        rows.append({'gun': gun, 'tag': tag, 'c_02': c, 'd_03': d,
                     'visible_len_mm': round(vis.length * 1000, 1),
                     'angle_to_mag_deg': round(math.degrees(math.acos(max(-1, min(1, vis.normalized().dot(mag_arm))))), 1),
                     'rise_mm': round(vis.z * 1000, 1),
                     'web_gap_mm': round(gap * 1000, 2),
                     'root_wxyz': [round(x, 6) for x in root]})
        for o in objs + [mo]:
            bpy.data.objects.remove(o)
        print('RENDERED', name, rows[-1], flush=True)
(O / 'render_thumb5.json').write_text(json.dumps(rows, indent=1))
print('RENDER5_OK', flush=True)
