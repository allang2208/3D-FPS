"""Render the shipped (IndexClearanceV4) AKM / A762 grip next to the accepted SVD
and M4 grips, in the magazine's own rest frame.  Left arm + magazine only."""
import bpy, bmesh, sys
from pathlib import Path
from mathutils import Vector

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'


def pca(points):
    c = sum(points, Vector()) / len(points)
    cov = [[0.0] * 3 for _ in range(3)]
    for p in points:
        d = p - c
        for i in range(3):
            for j in range(3):
                cov[i][j] += d[i] * d[j]
    A = [row[:] for row in cov]; vecs = []
    for _ in range(3):
        v = Vector((1.0, 0.31, 0.67))
        for _ in range(500):
            w = Vector((sum(A[i][j] * v[j] for j in range(3)) for i in range(3)))
            if w.length < 1e-14:
                break
            v = w.normalized()
        lam = sum(v[i] * sum(A[i][j] * v[j] for j in range(3)) for i in range(3))
        vecs.append((lam, v))
        for i in range(3):
            for j in range(3):
                A[i][j] -= lam * v[i] * v[j]
    vecs.sort(key=lambda x: -x[0])
    return c, [v for _, v in vecs]


def left_only(arms):
    right = {g.index for g in arms.vertex_groups if g.name.endswith('_r')}
    bm = bmesh.new(); bm.from_mesh(arms.data)
    deform = bm.verts.layers.deform.active
    dead = [v for v in bm.verts if sum(w for g, w in v[deform].items() if g in right) > .5]
    bmesh.ops.delete(bm, geom=dead, context='VERTS')
    bm.to_mesh(arms.data); bm.free()


def draw(tag, path, action, f):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action if action is None else bpy.data.actions[action]
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    left_only(arms)
    sc = bpy.context.scene
    sc.frame_set(f); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pose = {b.name: b.matrix.copy() for b in r.pose.bones}
    restb = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
    D = r.matrix_world @ pose['WPN_SOCKET_Magazine'] @ restb.inverted() @ r.matrix_world.inverted()
    Di = D.inverted()

    mags = [o for o in sc.objects if o.type == 'MESH' and o.parent == r
            and any(g.name == 'WPN_SOCKET_Magazine' for g in o.vertex_groups)]
    if not mags:
        with bpy.data.libraries.load(str(A762_LIB), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n.startswith('A762_R02_Magazine_')]
        for o in dst.objects:
            if o is None:
                continue
            sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
            o.matrix_world = D @ o.matrix_world
            mags.append(o)
    rest, polys = [], []
    for m in mags:
        off = len(rest)
        rest.extend(m.matrix_world @ v.co for v in m.data.vertices)
        polys.extend([[off + i for i in p.vertices] for p in m.data.polygons])
    if not rest:
        raise RuntimeError('no magazine geometry')
    c, ax = pca(rest)

    def to_frame(points):
        return [Vector((p.dot(ax[0]) - c.dot(ax[0]), p.dot(ax[1]) - c.dot(ax[1]), p.dot(ax[2]) - c.dot(ax[2])))
                for p in points]

    groups = [g.name for g in arms.vertex_groups]
    e = arms.evaluated_get(dg); me = e.to_mesh(); AM = e.matrix_world
    vmap, verts = {}, []
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        if not (best and best.endswith('_l')):
            continue
        vmap[v.index] = len(verts)
        verts.append(AM @ v.co)
    arm_polys = [[vmap[i] for i in p.vertices if i in vmap] for p in me.polygons]
    arm_polys = [p for p in arm_polys if len(p) >= 3]
    e.to_mesh_clear()
    am = bpy.data.meshes.new('Arm' + tag)
    am.from_pydata(to_frame([Di @ p for p in verts]), [], arm_polys); am.update()
    ao = bpy.data.objects.new('Arm' + tag, am); sc.collection.objects.link(ao)
    mm = bpy.data.meshes.new('Mag' + tag)
    mm.from_pydata(to_frame([Di @ p for p in rest]), [], polys); mm.update()
    mo = bpy.data.objects.new('Mag' + tag, mm); sc.collection.objects.link(mo)
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
        sc.world = bpy.data.worlds.new('GripWorld' + tag)
    sc.world.color = (.09, .09, .09)
    sc.render.resolution_x = 720; sc.render.resolution_y = 720; sc.render.resolution_percentage = 100
    sc.render.use_compositing = False; sc.render.use_sequencer = False
    cam = bpy.data.objects.new('C' + tag, bpy.data.cameras.new('C' + tag))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = .40
    for nm, u in [('Tp', ax[2]), ('Tn', -ax[2]), ('Wp', ax[1]), ('Wn', -ax[1]), ('L', ax[0])]:
        cam.location = u * .5
        cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = str(O / f'v4_{tag}_{nm}.png')
        bpy.ops.render.render(write_still=True)


V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
CASES = [
    ('AKM', V4 / 'AKM/standard/base/A_AKM_reload.blend', None, 148),
    ('A762', V4 / 'A762/standard/base/A_A762_reload.blend', None, 148),
    ('SVD', S / 'SVDThumbUp20260923/SVD_base_Editable.blend', 'A_SVD_reload', 148),
    ('M4', S / 'ExtMagContact20260919/A_M4_ExtContact_reload.blend', None, 76),
]
for tag, path, act, f in CASES:
    if not path.exists():
        print('MISSING', tag, flush=True); continue
    draw(tag, path, act, f)
    print('RENDERED', tag, flush=True)
print('V4_RENDER_OK', flush=True)
