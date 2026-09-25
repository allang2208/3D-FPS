"""Render thumb candidates for the AKM / A762 magazine grip: shipped, the fitted
swing-only opposition, and a near-rest reference."""
import bpy, bmesh, json, sys, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']


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


def left_only(arms):
    right = {g.index for g in arms.vertex_groups if g.name.endswith('_r')}
    bm = bmesh.new(); bm.from_mesh(arms.data)
    deform = bm.verts.layers.deform.active
    dead = [v for v in bm.verts if sum(w for g, w in v[deform].items() if g in right) > .5]
    bmesh.ops.delete(bm, geom=dead, context='VERTS')
    bm.to_mesh(arms.data); bm.free()


def draw(tag, path, action, f, quats):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action if action is None else bpy.data.actions[action]
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    left_only(arms)
    sc = bpy.context.scene
    sc.frame_set(f); bpy.context.view_layer.update()
    if quats:
        for n, q in quats.items():
            pb = r.pose.bones[n]
            loc, _, scale = pb.matrix_basis.decompose()
            pb.matrix_basis = Matrix.LocRotScale(loc, q, scale)
        bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pose = {b.name: b.matrix.copy() for b in r.pose.bones}
    restb = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
    D = r.matrix_world @ pose['WPN_SOCKET_Magazine'] @ restb.inverted() @ r.matrix_world.inverted()
    mags = [o for o in sc.objects if o.type == 'MESH'
            and any(g.name == 'WPN_SOCKET_Magazine' for g in o.vertex_groups)]
    if not mags:
        with bpy.data.libraries.load(str(A762_LIB), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n.startswith('A762_R02_Magazine_')]
        for o in dst.objects:
            if o is not None:
                sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
                mags.append(o)
    groups = [g.name for g in arms.vertex_groups]
    e = arms.evaluated_get(dg); me = e.to_mesh(); AM = e.matrix_world
    verts, polys, vmap = [], [], {}
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
    e.to_mesh_clear()
    am = bpy.data.meshes.new('A' + tag); am.from_pydata(verts, [], polys); am.update()
    ao = bpy.data.objects.new('A' + tag, am); sc.collection.objects.link(ao)
    mv, mp = [], []
    for m in mags:
        off = len(mv)
        mv.extend(D @ (m.matrix_world @ v.co) for v in m.data.vertices)
        mp.extend([[off + i for i in p.vertices] for p in m.data.polygons])
    mm = bpy.data.meshes.new('M' + tag); mm.from_pydata(mv, [], mp); mm.update()
    mo = bpy.data.objects.new('M' + tag, mm); sc.collection.objects.link(mo)
    ao.color = (.25, .45, .62, 1); mo.color = (.78, .52, .16, 1)
    for o in sc.objects:
        if o.type == 'MESH':
            vis = o in (ao, mo)
            o.hide_render = not vis
            if o.name in bpy.context.view_layer.objects:
                o.hide_set(not vis)
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
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = .30
    centre = r.matrix_world @ pose['hand_l'].translation
    fwd = (r.matrix_world @ pose['middle_01_l'].translation - centre).normalized()
    across = (r.matrix_world @ pose['index_01_l'].translation - r.matrix_world @ pose['pinky_01_l'].translation).normalized()
    normal = across.cross(fwd).normalized()
    for nm, u in [('back', -normal), ('palm', normal), ('edge', across), ('tip', fwd)]:
        cam.location = centre + u * .35
        cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = str(O / f'fit_{tag}_{nm}.png')
        bpy.ops.render.render(write_still=True)


def quats_for(params):
    a, b, c, d = params
    return {'thumb_01_l': swing_only(Matrix.Rotation(math.radians(a), 4, 'Z').to_quaternion() @
                                     Matrix.Rotation(math.radians(b), 4, 'X').to_quaternion()),
            'thumb_02_l': Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion(),
            'thumb_03_l': Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion()}


fit = json.loads((O / 'thumb_fit.json').read_text())
V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
if '--result' in sys.argv:
    for gun, rel in [('AKM', 'AKM/standard/base/A_AKM_reload.blend'), ('A762', 'A762/standard/base/A_A762_reload.blend')]:
        draw(gun + '_new', O / rel, None, 148, None)
        print('RENDERED', gun, 'authored', flush=True)
    print('RESULT_RENDER_OK', flush=True)
    sys.exit(0)
for gun, rel in [('AKM', 'AKM/standard/base/A_AKM_reload.blend'), ('A762', 'A762/standard/base/A_A762_reload.blend')]:
    params = [fit[gun]['params'][k] for k in ('a_z', 'b_x', 'c_02', 'd_03')]
    draw(gun + '_ship', V4 / rel, None, 148, None)
    draw(gun + '_fit', V4 / rel, None, 148, quats_for(params))
    draw(gun + '_rest', V4 / rel, None, 148, {'thumb_01_l': Quaternion(), 'thumb_02_l': Quaternion(),
                                              'thumb_03_l': Matrix.Rotation(math.radians(4), 4, 'Z').to_quaternion()})
    print('RENDERED', gun, params, flush=True)
print('FIT_RENDER_OK', flush=True)
