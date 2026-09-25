"""Render the shipped round-1 thumb against the aimed-up candidates, hand and
posed magazine only, so the extension can be judged.

Tags per gun: cur = round-1 installed target, best = candidate with the pad
resting on the magazine, alt = the highest-rise candidate.
"""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

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
    arms = bpy.data.objects['SK_Manny_Arms_Export']
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
    return r, arms, sc, W, mv, mp, pose


def build(tag, r, arms, sc, mv, mp, quats, keep, centre_basis):
    dg = bpy.context.evaluated_depsgraph_get()
    for n, q in quats.items():
        pb = r.pose.bones[n]
        loc, scale = keep[n]
        pb.matrix_basis = Matrix.LocRotScale(loc, q, scale)
    bpy.context.view_layer.update()
    e = arms.evaluated_get(dg); me = e.to_mesh(); AM = e.matrix_world
    groups = [g.name for g in arms.vertex_groups]
    vmap, verts = {}, []
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        if not (best and best.endswith('_l')):
            continue
        vmap[v.index] = len(verts); verts.append(AM @ v.co)
    polys = [[vmap[i] for i in p.vertices if i in vmap] for p in me.polygons]
    polys = [p for p in polys if len(p) >= 3]
    thumb = []
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        if best in PARTS and v.index in vmap:
            thumb.append(vmap[v.index])
    e.to_mesh_clear()
    for o in list(sc.objects):
        if o.type == 'MESH' and not o.name.startswith(('A' + tag, 'M' + tag, 'T' + tag)):
            o.hide_render = True
    am = bpy.data.meshes.new('A' + tag); am.from_pydata(verts, [], polys); am.update()
    ao = bpy.data.objects.new('A' + tag, am); sc.collection.objects.link(ao)
    mm = bpy.data.meshes.new('M' + tag); mm.from_pydata(mv, [], mp); mm.update()
    mo = bpy.data.objects.new('M' + tag, mm); sc.collection.objects.link(mo)
    tv, tp = [], []
    for i in thumb:
        pass
    ao.color = (.25, .45, .62, 1); mo.color = (.78, .52, .16, 1)
    sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'OBJECT'; sc.display.shading.show_cavity = True
    sc.display.shading.background_type = 'WORLD'
    if not sc.world:
        sc.world = bpy.data.worlds.new('W' + tag)
    sc.world.color = (.09, .09, .09)
    sc.render.resolution_x = 720; sc.render.resolution_y = 720; sc.render.resolution_percentage = 100
    sc.render.use_compositing = False; sc.render.use_sequencer = False
    cam = bpy.data.objects.new('C' + tag, bpy.data.cameras.new('C' + tag))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = .28
    P = {b.name: b.matrix.copy() for b in r.pose.bones}
    centre = r.matrix_world @ (centre_basis or P['hand_l']).translation
    fwd = (r.matrix_world @ P['middle_01_l'].translation - centre).normalized()
    across = (r.matrix_world @ P['index_01_l'].translation - r.matrix_world @ P['pinky_01_l'].translation).normalized()
    normal = across.cross(fwd).normalized()
    views = [('back', -normal), ('thumb', -across), ('edge', across), ('palm', normal)]
    for nm, u in views:
        cam.location = centre + u * .35
        cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = str(O / ('aim_%s_%s.png' % (tag, nm)))
        bpy.ops.render.render(write_still=True)
    # hand only (magazine hidden) from the thumb side and the edge
    mo.hide_render = True
    for nm, u in (('thumb', -across), ('edge', across)):
        cam.location = centre + u * .35
        cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = str(O / ('aim_%s_%s_nomag.png' % (tag, nm)))
        bpy.ops.render.render(write_still=True)
    mo.hide_render = False
    return ao, mo


report = {}
for gun, path in CASES.items():
    r, arms, sc, W, mv, mp, pose = load(gun, path)
    keep = {n: (lambda d: (d[0], d[2]))(r.pose.bones[n].matrix_basis.decompose()) for n in PARTS}
    p = FIT[gun]['params']
    cur = {'thumb_01_l': swing_only(Matrix.Rotation(math.radians(p['a_z']), 4, 'Z').to_quaternion() @
                                   Matrix.Rotation(math.radians(p['b_x']), 4, 'X').to_quaternion()),
           'thumb_02_l': Matrix.Rotation(math.radians(p['c_02']), 4, 'Z').to_quaternion(),
           'thumb_03_l': Matrix.Rotation(math.radians(p['d_03']), 4, 'Z').to_quaternion()}
    best, alt = pick(AIM[gun]['candidates'])
    tags = [('cur', cur, 'round-1 installed')]
    for nm, row in (('best', best), ('alt', alt)):
        if row:
            tags.append((nm, {'thumb_01_l': Quaternion(row['root_quat_wxyz']),
                              'thumb_02_l': Matrix.Rotation(math.radians(row['c_02']), 4, 'Z').to_quaternion(),
                              'thumb_03_l': Matrix.Rotation(math.radians(row['d_03']), 4, 'Z').to_quaternion()},
                         'tilt %.0f flex %.0f/%.0f' % (row['tilt'], row['c_02'], row['d_03'])))
    for nm, q, note in tags:
        tag = gun.lower() + '_' + nm
        build(tag, r, arms, sc, mv, mp, q, keep, pose['hand_l'])
        report[tag] = {'gun': gun, 'variant': nm, 'note': note,
                       'candidate': None if nm == 'cur' else {k: v for k, v in (best if nm == 'best' else alt).items() if k != 'clear'}}
        print('RENDERED', tag, note, flush=True)
(O / 'render_aim.json').write_text(json.dumps(report, indent=1))
print('RENDER_AIM_OK', flush=True)
