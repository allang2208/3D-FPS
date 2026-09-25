"""Render the shipped round-1 thumb against the final aimed-up target, with the
thumb as its own coloured object and the posed magazine proxy.

The 'side2' view looks along minus the tilt axis (the side the thumb is on), and
'game' looks along the weapon barrel from behind, i.e. roughly the player's view.
The visible thumb direction is reported from the skinned mesh the same way the
aim solved it, as a cross-check on the renders.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
FRAME = 148
CASES = {
    'AKM': S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend',
    'A762': S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend',
}
FIT = json.loads((O / 'thumb_fit.json').read_text())
TGT = json.loads((O / 'thumb_target2.json').read_text())


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


def load(gun, path):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    sc = bpy.context.scene
    sc.frame_set(FRAME); bpy.context.view_layer.update()
    W = r.matrix_world
    D = W @ r.pose.bones['WPN_SOCKET_Magazine'].matrix @ r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted() @ W.inverted()
    proxy = [o for o in sc.objects if o.type == 'MESH' and gun.upper() in o.name.upper() and 'MAG' in o.name.upper()]
    dg = bpy.context.evaluated_depsgraph_get()
    apply_d = False
    if not proxy:
        with bpy.data.libraries.load(str(A762_LIB), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n.startswith('A762_R02_Magazine_')]
        proxy = [o for o in dst.objects if o is not None]
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
    return r, sc, W, mv, mp, mag_arm, tilt_axis


def thumb_state(r, arms):
    dg = bpy.context.evaluated_depsgraph_get()
    e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    groups = [g.name for g in arms.vertex_groups]
    verts, polys, vmap = [], [], {}
    cent = {p: [] for p in PARTS}
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        if best and best.endswith('_l'):
            vmap[v.index] = len(verts); verts.append(M @ v.co)
            if best in PARTS:
                cent[best].append(M @ v.co)
    for p in me.polygons:
        idx = [vmap[i] for i in p.vertices if i in vmap]
        if len(idx) >= 3:
            polys.append(idx)
    e.to_mesh_clear()
    c = {p: sum(pts, Vector()) / len(pts) for p, pts in cent.items() if pts}
    return verts, polys, c


def set_thumb(r, root, c, d, keep):
    for n, q in (('thumb_01_l', root),
                 ('thumb_02_l', Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion()),
                 ('thumb_03_l', Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion())):
        loc, scale = keep[n]
        r.pose.bones[n].matrix_basis = Matrix.LocRotScale(loc, q, scale)
    bpy.context.view_layer.update()


rows = []
for gun, path in CASES.items():
    r, sc, W, mv, mp, mag_arm, tilt_axis = load(gun, path)
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    keep = {n: (lambda dd: (dd[0], dd[2]))(r.pose.bones[n].matrix_basis.decompose()) for n in PARTS}
    p1 = FIT[gun]['params']
    t = TGT[gun]
    variants = [('cur', (Matrix.Rotation(math.radians(p1['a_z']), 4, 'Z').to_quaternion() @
                          Matrix.Rotation(math.radians(p1['b_x']), 4, 'X').to_quaternion()), p1['c_02'], p1['d_03'],
                 'round-1 shipped', (.25, .85, .3, 1)),
                ('new', Quaternion(t['root_quat_wxyz']), t['c_02'], t['d_03'],
                 'aimed up tilt %.0f flex %.0f/%.0f' % (t['tilt'], t['c_02'], t['d_03']), (.85, .2, .75, 1))]
    for tag, root, c, d, note, col in variants:
        set_thumb(r, root, c, d, keep)
        verts, polys, cent = thumb_state(r, arms)
        vd = cent['thumb_03_l'] - cent['thumb_01_l']
        P = {b.name: b.matrix.copy() for b in r.pose.bones}
        centre = P['hand_l'].translation
        wpn = [b for b in P if b.startswith('WPN_')]
        barrel = (P['WPN_SOCKET_Muzzle'].translation - P['WPN_root'].translation).normalized()
        fwd = (P['middle_01_l'].translation - centre).normalized()
        across = (P['index_01_l'].translation - P['pinky_01_l'].translation).normalized()
        normal = across.cross(fwd).normalized()
        for o in list(sc.objects):
            if o.type == 'MESH':
                o.hide_render = True
        hm = bpy.data.meshes.new('hand' + tag)
        # hand and thumb split by colour: rebuild the hand mesh without the thumb
        hv, hp, vmap = [], [], {}
        dg = bpy.context.evaluated_depsgraph_get()
        e = arms.evaluated_get(dg); me = e.to_mesh(); AM = e.matrix_world
        groups = [g.name for g in arms.vertex_groups]
        kind = {}
        for v in me.vertices:
            best, w = None, 0.0
            for g in v.groups:
                if g.weight > w:
                    best, w = groups[g.group], g.weight
            kind[v.index] = best
        objs = []
        for nm, want in (('hand', False), ('thumb', True)):
            vmap, vv = {}, []
            for v in me.vertices:
                b = kind[v.index]
                if not (b and b.endswith('_l')):
                    continue
                if (b in PARTS) != want:
                    continue
                vmap[v.index] = len(vv); vv.append(AM @ v.co)
            pp = [[vmap[i] for i in p.vertices if i in vmap] for p in me.polygons]
            pp = [x for x in pp if len(x) >= 3]
            m = bpy.data.meshes.new(nm + tag + gun)
            m.from_pydata(vv, [], pp); m.update()
            o = bpy.data.objects.new(nm + tag + gun, m); sc.collection.objects.link(o)
            o.color = (.22, .42, .60, 1) if not want else col
            objs.append(o)
        e.to_mesh_clear()
        mm = bpy.data.meshes.new('mag' + tag + gun); mm.from_pydata(mv, [], mp); mm.update()
        mo = bpy.data.objects.new('mag' + tag + gun, mm); sc.collection.objects.link(mo)
        mo.color = (.80, .55, .18, 1)
        sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'
        sc.display.shading.color_type = 'OBJECT'; sc.display.shading.show_cavity = True
        sc.display.shading.background_type = 'WORLD'
        if not sc.world:
            sc.world = bpy.data.worlds.new('W' + tag + gun)
        sc.world.color = (.08, .08, .09)
        sc.render.resolution_x = 900; sc.render.resolution_y = 900; sc.render.resolution_percentage = 100
        sc.render.use_compositing = False; sc.render.use_sequencer = False
        cam = bpy.data.objects.new('cam' + tag + gun, bpy.data.cameras.new('cam' + tag + gun))
        sc.collection.objects.link(cam); sc.camera = cam
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = .34
        views = [('side', tilt_axis), ('side2', -tilt_axis), ('game', -barrel), ('back', -normal)]
        for vn, u in views:
            cam.location = centre + u * .45
            cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = str(O / ('thumb4_%s_%s_%s.png' % (gun.lower(), tag, vn)))
            bpy.ops.render.render(write_still=True)
        mo.hide_render = True
        for vn, u in (('side2', -tilt_axis), ('game', -barrel)):
            cam.location = centre + u * .45
            cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = str(O / ('thumb4_%s_%s_%s_nomag.png' % (gun.lower(), tag, vn)))
            bpy.ops.render.render(write_still=True)
        rows.append({'gun': gun, 'tag': tag, 'note': note,
                     'vis_len_mm': round(vd.length * 1000, 1),
                     'angle_to_mag_deg': round(math.degrees(math.acos(max(-1, min(1, vd.normalized().dot(mag_arm))))), 2),
                     'rise_mm': round(vd.z * 1000, 1)})
        for o in objs + [mo]:
            bpy.data.objects.remove(o)
        print('RENDERED', gun, tag, rows[-1], flush=True)
(O / 'render_thumb4.json').write_text(json.dumps(rows, indent=1))
print('RENDER4_OK', flush=True)
