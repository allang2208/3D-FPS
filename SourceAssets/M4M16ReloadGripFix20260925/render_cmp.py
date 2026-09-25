"""Normalised before/after/AKM comparison in the magazine's own rest frame.

All geometry is drawn in the magazine shell frame (PCA, origin = shell box
centre), so the accepted AKM wrap, the previous M4 clip and the refined M4 clip
can be compared with the magazine in an identical position.
"""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector, Matrix

O = Path(__file__).parent; S = O.parent
sys.path.insert(0, str(O))
import grip_lib as G


def to_frame(points, c, ax):
    return [Vector((p.dot(ax[0]) - c.dot(ax[0]), p.dot(ax[1]) - c.dot(ax[1]), p.dot(ax[2]) - c.dot(ax[2])))
            for p in points]


def draw(tag, path, action, mag_name, f):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = bpy.data.actions[action]
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    mag = bpy.data.objects[mag_name]
    sc = bpy.context.scene
    sc.frame_set(f); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    rest = [mag.matrix_world @ v.co for v in mag.data.vertices]
    c, ax = G.pca(rest)
    pose = {b.name: b.matrix.copy() for b in r.pose.bones}
    D = G.deform(rig=r, pose=pose)
    Di = D.inverted()
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
    polys = [[vmap[i] for i in p.vertices if i in vmap] for p in me.polygons]
    polys = [p for p in polys if len(p) >= 3]
    e.to_mesh_clear()
    arm = bpy.data.meshes.new('Arm' + tag)
    arm.from_pydata(to_frame([Di @ p for p in verts], c, ax), [], polys); arm.update()
    ao = bpy.data.objects.new('Arm' + tag, arm); sc.collection.objects.link(ao)
    mm = bpy.data.meshes.new('Mag' + tag)
    mm.from_pydata(to_frame(rest, c, ax), [], [list(p.vertices) for p in mag.data.polygons]); mm.update()
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
    sc.display.shading.background_type = 'WORLD'; sc.world.color = (.09, .09, .09)
    sc.render.resolution_x = 720; sc.render.resolution_y = 720; sc.render.resolution_percentage = 100
    sc.render.use_compositing = False; sc.render.use_sequencer = False
    cam = bpy.data.objects.new('C' + tag, bpy.data.cameras.new('C' + tag))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = .34
    for nm, i, sgn in [('T', 2, -1), ('T', 2, 1), ('W', 1, -1), ('W', 1, 1)]:
        u = ax[i] * sgn
        cam.location = u * .4
        cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = str(O / f'cmp_{tag}_{nm}{"p" if sgn > 0 else "n"}.png')
        bpy.ops.render.render(write_still=True)


draw('after', O / 'M4Animations/A_M4_ExtContact_reload.blend', 'A_M4_ExtContact_reload_GripPrecise',
     'M4_Magazine Light.003_Export', 76)
draw('before', S / 'ExtMagContact20260919/A_M4_ExtContact_reload.blend', 'A_M4_ExtContact_reload',
     'M4_Magazine Light.003_Export', 76)
draw('akm', S / 'AKMReloadPolish20260911/base/A_AKM_reload.blend', 'A_AKM_reload_Polished',
     'AKM_FactoryMagazine_Preview', 148)
print('CMP_OK', flush=True)
