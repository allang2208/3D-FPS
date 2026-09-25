"""Sweep candidate thumb poses for the AKM magazine grip and render each one from
two fixed views, so the "extends freely upwards" target can be picked by eye.
Root rotation is a local Z (flexion/abduction) and X pair with no twist; the last
two segments stay nearly straight.
"""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

O = Path(__file__).parent; S = O.parent
ACC = S / 'A762Meshy20260920/Accessories05'
V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
BONES = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
CANDIDATES = [
    ('cur', None),                       # shipped (first fix)
    ('z0x0', (0, 0, 6, 5)),
    ('zp20', (20, 0, 6, 5)),
    ('zn20', (-20, 0, 6, 5)),
    ('xp20', (0, 20, 6, 5)),
    ('xn20', (0, -20, 6, 5)),
    ('zp_xp', (20, 20, 6, 5)),
    ('zn_xp', (-20, 20, 6, 5)),
    ('zp_xn', (20, -20, 6, 5)),
]


def quats(par):
    a, b, c, d = par
    return {'thumb_01_l': Matrix.Rotation(math.radians(a), 4, 'Z').to_quaternion() @
                          Matrix.Rotation(math.radians(b), 4, 'X').to_quaternion(),
            'thumb_02_l': Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion(),
            'thumb_03_l': Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion()}


def left_only(arms):
    right = {g.index for g in arms.vertex_groups if g.name.endswith('_r')}
    bm = bmesh.new(); bm.from_mesh(arms.data)
    deform = bm.verts.layers.deform.active
    dead = [v for v in bm.verts if sum(w for g, w in v[deform].items() if g in right) > .5]
    bmesh.ops.delete(bm, geom=dead, context='VERTS')
    bm.to_mesh(arms.data); bm.free()


def shoot(tag, par):
    bpy.ops.wm.open_mainfile(filepath=str(V4 / 'AKM/standard/base/A_AKM_reload.blend'), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action; r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    left_only(arms)
    sc = bpy.context.scene
    sc.frame_set(148); bpy.context.view_layer.update()
    # bake the sampled pose into matrix_basis and detach the action, otherwise the
    # render re-evaluates the animation and discards the candidate
    base = {b.name: b.matrix_basis.copy() for b in r.pose.bones}
    r.animation_data_clear()
    for n, m in base.items():
        r.pose.bones[n].matrix_basis = m
    bpy.context.view_layer.update()
    if par is not None:
        for n, q in quats(par).items():
            pb = r.pose.bones[n]
            loc, _, scale = pb.matrix_basis.decompose()
            pb.matrix_basis = Matrix.LocRotScale(loc, q, scale)
        bpy.context.view_layer.update()
    tip = r.matrix_world @ r.pose.bones['thumb_03_l'].matrix @ Vector((0, r.data.bones['thumb_03_l'].length, 0))
    print('   tip mm', [round(x * 1000, 1) for x in tip], flush=True)
    mags = [o for o in sc.objects if o.type == 'MESH' and 'Magazine' in o.name]
    keep = [arms] + mags
    for o in sc.objects:
        if o.type == 'MESH':
            vis = o in keep
            o.hide_render = not vis
            if o.name in bpy.context.view_layer.objects:
                o.hide_set(not vis)
    arms.color = (.25, .45, .62, 1)
    for o in mags:
        o.color = (.78, .52, .16, 1)
    sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'OBJECT'; sc.display.shading.show_cavity = True
    sc.display.shading.background_type = 'WORLD'
    if not sc.world:
        sc.world = bpy.data.worlds.new('W')
    sc.world.color = (.09, .09, .09)
    sc.render.resolution_x = 700; sc.render.resolution_y = 560; sc.render.resolution_percentage = 100
    sc.render.use_compositing = False; sc.render.use_sequencer = False
    cam = bpy.data.objects.new('C', bpy.data.cameras.new('C')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.26
    pose = {b.name: b.matrix.copy() for b in r.pose.bones}
    centre = r.matrix_world @ pose['hand_l'].translation
    fwd = (r.matrix_world @ pose['middle_01_l'].translation - centre).normalized()
    across = (r.matrix_world @ pose['index_01_l'].translation - r.matrix_world @ pose['pinky_01_l'].translation).normalized()
    normal = across.cross(fwd).normalized()
    for nm, u in (('back', -normal), ('thumb', -across)):
        cam.location = centre + u * 0.4
        cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = str(O / f'sweep_{tag}_{nm}.png')
        bpy.ops.render.render(write_still=True)
    print('SWEEP_RENDERED', tag, flush=True)


for tag, par in CANDIDATES:
    shoot(tag, par)
print('SWEEP_OK', flush=True)
