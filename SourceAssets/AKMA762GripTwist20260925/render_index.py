"""Render candidate thumb lifts against the index finger.

Thumb is magenta, the index finger cyan, the other fingers blue-grey and the
magazine tan, so a crossing is visible.  'back' looks at the back of the hand
(where "thumb above the index" is read), 'thumb' along minus the hand's across
axis and 'game' along the barrel.

Each candidate is the v3 root (shipping root, distal 4/3) plus one extra swing
about a hand-frame axis, applied about an axis perpendicular to the visible thumb
direction so the accepted roll does not change.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
INDEX = ['index_01_l', 'index_02_l', 'index_03_l']
FRAME = 148
CASES = {
    'AKM': S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend',
    'A762': S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend',
}
TARGET = json.loads((O / 'thumb_target3.json').read_text())
CANDS = {'AKM': [('base', None), ('n_m8', ('normal', -8.0)), ('f_m8', ('fwd', -8.0)), ('f_p32', ('fwd', 32.0))],
         'A762': [('base', None), ('n_m20', ('normal', -20.0)), ('f_p20', ('fwd', 20.0)), ('f_m16', ('fwd', -16.0))]}


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


def open_clip(path):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    act = r.animation_data.action
    r.animation_data.action_slot = act.slots[0]
    sc = bpy.context.scene
    sc.frame_set(FRAME); bpy.context.view_layer.update()
    return r, sc


def set_thumb(r, root, c, d, keep):
    for n, q in (('thumb_01_l', root),
                 ('thumb_02_l', Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion()),
                 ('thumb_03_l', Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion())):
        r.pose.bones[n].matrix_basis = Matrix.LocRotScale(keep[n][0], q, keep[n][1])
    bpy.context.view_layer.update()


def centroids(arms):
    dg = bpy.context.evaluated_depsgraph_get()
    e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    names = [g.name for g in arms.vertex_groups]
    acc = {g: [] for g in PARTS + INDEX}
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = names[g.group], g.weight
        if best in acc:
            acc[best].append(M @ v.co)
    e.to_mesh_clear()
    return {k: (sum(v, Vector()) / len(v) if v else Vector()) for k, v in acc.items()}


rows = []
for gun, path in CASES.items():
    r, sc = open_clip(path)
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    W = r.matrix_world
    keep = {n: (lambda dd: (dd[0], dd[2]))(r.pose.bones[n].matrix_basis.decompose()) for n in PARTS}
    q3 = Quaternion(TARGET[gun]['root_quat_wxyz'])
    C, D = TARGET[gun]['c_02'], TARGET[gun]['d_03']
    dg = bpy.context.evaluated_depsgraph_get()
    Dm = W @ r.pose.bones['WPN_SOCKET_Magazine'].matrix @ r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted() @ W.inverted()
    proxy = [o for o in sc.objects if o.type == 'MESH' and gun.upper() in o.name.upper() and 'MAG' in o.name.upper()]
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
            mv.extend(Dm @ (o.matrix_world @ v.co) for v in o.data.vertices)
            mp.extend([[off + i for i in p.vertices] for p in o.data.polygons])
    P = {b.name: b.matrix.copy() for b in r.pose.bones}
    centre = W @ P['hand_l'].translation
    fwd = (W @ P['middle_01_l'].translation - centre).normalized()
    across = (W @ P['index_01_l'].translation - W @ P['pinky_01_l'].translation).normalized()
    normal = across.cross(fwd).normalized()
    axes = {'normal': normal, 'across': across, 'fwd': fwd}
    set_thumb(r, q3, C, D, keep)
    cen0 = centroids(arms)
    vis = (cen0['thumb_03_l'] - cen0['thumb_01_l']).normalized()
    M0 = {b.name: b.matrix.copy() for b in r.pose.bones}['thumb_01_l'].to_3x3()
    for tag, spec in CANDS[gun]:
        if spec is None:
            q = q3
        else:
            ax = axes[spec[0]]
            perp = ax - vis * ax.dot(vis)
            perp.normalize()
            R = Matrix.Rotation(math.radians(spec[1]), 3, perp)
            Mcur = {b.name: b.matrix.copy() for b in r.pose.bones}['thumb_01_l'].to_3x3()
            q = (M0.inverted() @ R @ M0 @ q3.to_matrix()).to_quaternion()
        set_thumb(r, q, C, D, keep)
        cen = centroids(arms)
        vd = cen['thumb_03_l'] - cen['thumb_01_l']
        side = (cen['thumb_02_l'] + cen['thumb_03_l'] - cen['index_01_l'] - cen['index_02_l']
                - cen['index_03_l']).dot(normal) * 1000 / 2
        dg = bpy.context.evaluated_depsgraph_get()
        e = arms.evaluated_get(dg); me = e.to_mesh(); AM = e.matrix_world
        names = [g.name for g in arms.vertex_groups]
        kind = {}
        for v in me.vertices:
            best, w = None, 0.0
            for g in v.groups:
                if g.weight > w:
                    best, w = names[g.group], g.weight
            kind[v.index] = best
        objs = []
        pal = {0: (.85, .2, .75, 1), 1: (.2, .8, .85, 1), 2: (.22, .42, .60, 1)}
        for which, gset in ((0, PARTS), (1, INDEX), (2, None)):
            vmap, pts = {}, []
            for v in me.vertices:
                b = kind[v.index]
                if not (b and b.endswith('_l')):
                    continue
                if which == 0 and b not in PARTS:
                    continue
                if which == 1 and b not in INDEX:
                    continue
                if which == 2 and (b in PARTS or b in INDEX):
                    continue
                vmap[v.index] = len(pts); pts.append(AM @ v.co)
            pp = [[vmap[i] for i in p.vertices if i in vmap] for p in me.polygons]
            pp = [x for x in pp if len(x) >= 3]
            m = bpy.data.meshes.new('p%d%s%s' % (which, tag, gun))
            m.from_pydata(pts, [], pp); m.update()
            o = bpy.data.objects.new('p%d%s%s' % (which, tag, gun), m)
            sc.collection.objects.link(o); o.color = pal[which]
            objs.append(o)
        e.to_mesh_clear()
        mm = bpy.data.meshes.new('mag%s%s' % (tag, gun)); mm.from_pydata(mv, [], mp); mm.update()
        mo = bpy.data.objects.new('mag%s%s' % (tag, gun), mm); sc.collection.objects.link(mo)
        mo.color = (.80, .55, .18, 1)
        for o in list(sc.objects):
            if o.type == 'MESH' and o not in objs and o is not mo:
                o.hide_render = True
        sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'
        sc.display.shading.color_type = 'OBJECT'; sc.display.shading.show_cavity = True
        sc.display.shading.background_type = 'WORLD'
        if not sc.world:
            sc.world = bpy.data.worlds.new('W' + tag + gun)
        sc.world.color = (.08, .08, .09)
        sc.render.resolution_x = 900; sc.render.resolution_y = 900; sc.render.resolution_percentage = 100
        sc.render.use_compositing = False; sc.render.use_sequencer = False
        cam = bpy.data.objects.new('cam%s%s' % (tag, gun), bpy.data.cameras.new('c'))
        sc.collection.objects.link(cam); sc.camera = cam
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = .26
        ctr = (cen['thumb_02_l'] + cen['index_01_l']) / 2
        for vn, u in (('back', -normal), ('thumb', -across), ('palm', normal)):
            cam.location = ctr + u * .45
            cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = str(O / ('thumb6_%s_%s_%s.png' % (gun.lower(), tag, vn)))
            bpy.ops.render.render(write_still=True)
        rows.append({'gun': gun, 'tag': tag, 'spec': spec,
                     'visible_len_mm': round(vd.length * 1000, 1),
                     'thumb_vs_index_side_mm': round(side, 2),
                     'root_wxyz': [round(x, 6) for x in q]})
        for o in objs + [mo]:
            bpy.data.objects.remove(o)
        print('RENDERED', gun, tag, rows[-1], flush=True)
(O / 'render_thumb6.json').write_text(json.dumps(rows, indent=1))
print('RENDER6_OK', flush=True)
