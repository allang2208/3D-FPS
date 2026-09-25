"""Render the shipped round-1 thumb against the aimed-up candidates with the
thumb as its own coloured object, from the plane in which the aim was solved.

Views: 'side' looks along the tilt axis, so the magazine axis is vertical and the
palm side is horizontal; 'back'/'palm' look along the hand normal.  Each variant
is rendered hand+magazine and hand-only.
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
AIM = json.loads((O / 'thumb_aim2.json').read_text())
CHOICES = {'AKM': [(-5.0, 4, 3), (0.0, 4, 3), (5.0, 4, 3)],
           'A762': [(-15.0, 4, 3), (0.0, 4, 3), (5.0, 4, 3), (20.0, 4, 3)]}


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


def pick(rows):
    ok = [x for x in rows if x['chord_mm'] >= 58.0 and abs(x['root_twist_deg']) < 0.5
          and (x['clear']['thumb_03_l']['hand_min'] or 99) >= 4.0]
    near = [x for x in ok if -2.0 <= x['clear']['thumb_03_l']['min'] <= 10.0]
    near.sort(key=lambda x: -x['rise_mm'])
    ok.sort(key=lambda x: -x['rise_mm'])
    best = near[0] if near else (ok[0] if ok else None)
    alt = next((x for x in ok if x is not best), None)
    return best, alt


def load(gun, path):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    sc = bpy.context.scene
    sc.frame_set(FRAME); bpy.context.view_layer.update()
    W = r.matrix_world
    pose = {b.name: b.matrix.copy() for b in r.pose.bones}
    D = W @ pose['WPN_SOCKET_Magazine'] @ r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted() @ W.inverted()
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
    mag_c = sum(mv, Vector()) / len(mv)
    mag_arm = (W.to_3x3().inverted() @ Vector(AIM[gun]['mag_axis_armature'])).normalized()
    v = r.pose.bones['hand_l'].matrix.translation - mag_c
    v_perp = v - v.project(mag_arm)
    v_perp.normalize()
    tilt_axis = mag_arm.cross(v_perp).normalized()
    return r, sc, W, mv, mp, tilt_axis, v_perp, mag_arm


def split(arms, sc, tag, thumb_color):
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
    for nm, keep_thumb in (('hand', False), ('thumb', True)):
        vmap, verts = {}, []
        for v in me.vertices:
            b = kind[v.index]
            if not (b and b.endswith('_l')):
                continue
            if (b in PARTS) != keep_thumb:
                continue
            vmap[v.index] = len(verts); verts.append(AM @ v.co)
        polys = [[vmap[i] for i in p.vertices if i in vmap] for p in me.polygons]
        polys = [p for p in polys if len(p) >= 3]
        m = bpy.data.meshes.new(nm + tag); m.from_pydata(verts, [], polys); m.update()
        o = bpy.data.objects.new(nm + tag, m); sc.collection.objects.link(o)
        o.color = (.22, .42, .60, 1) if not keep_thumb else thumb_color
        objs.append(o)
    e.to_mesh_clear()
    return objs


def make_mag(sc, tag, mv, mp):
    m = bpy.data.meshes.new('mag' + tag); m.from_pydata(mv, [], mp); m.update()
    o = bpy.data.objects.new('mag' + tag, m); sc.collection.objects.link(o)
    o.color = (.80, .55, .18, 1)
    return o


def render_variants(gun, path, out_rows):
    r, sc, W, mv, mp, tilt_axis, v_perp, mag_arm = load(gun, path)
    keep = {n: (lambda d: (d[0], d[2]))(r.pose.bones[n].matrix_basis.decompose()) for n in PARTS}
    p = FIT[gun]['params']
    cur = {'thumb_01_l': swing_only(Matrix.Rotation(math.radians(p['a_z']), 4, 'Z').to_quaternion() @
                                   Matrix.Rotation(math.radians(p['b_x']), 4, 'X').to_quaternion()),
           'thumb_02_l': Matrix.Rotation(math.radians(p['c_02']), 4, 'Z').to_quaternion(),
           'thumb_03_l': Matrix.Rotation(math.radians(p['d_03']), 4, 'Z').to_quaternion()}
    best, alt = None, None
    choices = CHOICES[gun]
    variants = [('cur', cur, 'round-1 installed', (.25, .8, .3, 1))]
    colors = [(.85, .2, .75, 1), (.95, .55, .1, 1), (.2, .75, .85, 1), (.9, .85, .2, 1)]
    for i, (tl, c, d) in enumerate(choices):
        row = next((x for x in AIM[gun]['candidates'] if abs(x['tilt'] - tl) < .01
                    and abs(x['c_02'] - c) < .01 and abs(x['d_03'] - d) < .01), None)
        if not row:
            print('   no candidate', gun, tl, c, d, flush=True)
            continue
        variants.append(('t%+d_c%d_d%d' % (tl, c, d),
                         {'thumb_01_l': Quaternion(row['root_quat_wxyz']),
                          'thumb_02_l': Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion(),
                          'thumb_03_l': Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion()},
                         'tilt %.0f flex %.0f/%.0f res %.1f angle %.1f rise %+.1f clear %s'
                         % (tl, c, d, row['aim_residual_deg'], row['angle_to_mag_deg'], row['rise_mm'],
                            [row['clear'][k]['min'] for k in PARTS]),
                         colors[i % len(colors)]))
    for nm, q, note, col in variants:
        for n, qq in q.items():
            pb = r.pose.bones[n]
            pb.matrix_basis = Matrix.LocRotScale(keep[n][0], qq, keep[n][1])
        bpy.context.view_layer.update()
        tag = '%s_%s' % (gun.lower(), nm)
        for o in list(sc.objects):
            if o.type == 'MESH':
                o.hide_render = True
        ho, to = split(bpy.data.objects['SK_Manny_Arms_Export'], sc, tag, col)
        mo = make_mag(sc, tag, mv, mp)
        sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'
        sc.display.shading.color_type = 'OBJECT'; sc.display.shading.show_cavity = True
        sc.display.shading.background_type = 'WORLD'
        if not sc.world:
            sc.world = bpy.data.worlds.new('W_' + tag)
        sc.world.color = (.08, .08, .09)
        sc.render.resolution_x = 900; sc.render.resolution_y = 900; sc.render.resolution_percentage = 100
        sc.render.use_compositing = False; sc.render.use_sequencer = False
        cam = bpy.data.objects.new('cam' + tag, bpy.data.cameras.new('cam' + tag))
        sc.collection.objects.link(cam); sc.camera = cam
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = .34
        P = {b.name: b.matrix.copy() for b in r.pose.bones}
        centre = P['hand_l'].translation
        fwd = (P['middle_01_l'].translation - centre).normalized()
        across = (P['index_01_l'].translation - P['pinky_01_l'].translation).normalized()
        normal = across.cross(fwd).normalized()
        views = [('side', tilt_axis), ('side2', -tilt_axis), ('back', -normal), ('palm', normal)]
        wpn = [b for b in P if b.startswith('WPN_')]
        muz = next((b for b in wpn if 'Muzzle' in b or 'MUZZLE' in b), None)
        root = 'WPN_root' if 'WPN_root' in P else (wpn[0] if wpn else None)
        barrel = None
        if root is not None:
            o = P[muz].translation if muz else r.data.bones[root].tail_local
            barrel = (o - P[root].translation).normalized()
            views.append(('game', -barrel))
            if nm == 'cur':
                print('   WPN bones %s muzzle %s barrel %s' % (wpn[:14], muz, [round(x, 3) for x in barrel]), flush=True)
        for vn, u in views:
            cam.location = centre + u * .45
            cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = str(O / ('thumb3_%s_%s.png' % (tag, vn)))
            bpy.ops.render.render(write_still=True)
        mo.hide_render = True
        for vn, u in (('side', tilt_axis), ('side2', -tilt_axis), ('back', -normal), ('game', -barrel)):
            cam.location = centre + u * .45
            cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = str(O / ('thumb3_%s_%s_nomag.png' % (tag, vn)))
            bpy.ops.render.render(write_still=True)
        head = P['thumb_01_l'].translation
        tip = P['thumb_03_l'] @ Vector((0, r.data.bones['thumb_03_l'].length, 0))
        ch = tip - head
        out_rows.append({'tag': tag, 'gun': gun, 'variant': nm, 'note': note,
                         'chord_mm': round(ch.length * 1000, 1),
                         'rise_mm': round(ch.z * 1000, 1),
                         'along_mag_mm': round(ch.dot(mag_arm) * 1000, 1),
                         'side_up_mm': round(ch.dot(v_perp) * 1000, 1),
                         'params': ({'tilt': best['tilt'], 'c': best['c_02'], 'd': best['d_03']} if nm == 'best'
                                    else ({'tilt': alt['tilt'], 'c': alt['c_02'], 'd': alt['d_03']} if nm == 'alt' else 'round1'))})
        for o in (ho, to, mo):
            bpy.data.objects.remove(o)
        print('RENDERED', tag, note, flush=True)


rows = []
for gun, path in CASES.items():
    render_variants(gun, path, rows)
(O / 'render_thumb3.json').write_text(json.dumps(rows, indent=1))
print('RENDER3_OK', flush=True)
