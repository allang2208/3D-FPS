"""Render the A762 drum beside its AKM donor, and assembled in the receiver, so
the neck's shape can be judged directly."""
import bpy, sys
from pathlib import Path
from mathutils import Vector

O = Path(__file__).parent; S = O.parent
ACC = S / 'A762Meshy20260920/Accessories05'
DONOR = S / 'LargeDrumUpgrade20260920/Export/SM_AKM_LargeDrum_Upgrade.fbx'


def setup_scene(tag):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'OBJECT'
    sc.display.shading.show_cavity = True
    sc.display.shading.background_type = 'WORLD'
    if not sc.world:
        sc.world = bpy.data.worlds.new('W' + tag)
    sc.world.color = (.09, .09, .09)
    sc.render.resolution_x = 900; sc.render.resolution_y = 700; sc.render.resolution_percentage = 100
    sc.render.use_compositing = False; sc.render.use_sequencer = False
    cam = bpy.data.objects.new('C' + tag, bpy.data.cameras.new('C' + tag))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'
    return sc, cam


def shoot(sc, cam, path, centre, direction, up, scale):
    cam.data.ortho_scale = scale
    cam.location = centre + direction.normalized() * 1.2
    cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def colour(objs):
    for i, o in enumerate(objs):
        o.color = (.78, .52, .16, 1) if i == 0 else (.30, .52, .70, 1)


# 1) the drum alone, shipped vs donor, side by side in the same frame
for tag, path in (('a762', ACC / 'SM_A762_drum.blend'), ('donor', None),
                  ('rebuilt', O / 'SM_A762_drum.blend')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if path is not None:
        bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
        objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    else:
        bpy.ops.import_scene.fbx(filepath=str(DONOR))
        objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.hide_render = o not in objs
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    centre = sum(pts, Vector()) / len(pts)
    lo = Vector((min(p[i] for p in pts) for i in range(3)))
    hi = Vector((max(p[i] for p in pts) for i in range(3)))
    neck_lo = Vector((centre.x, centre.y, lo.z + (hi.z - lo.z) * 0.70))
    for o in objs:
        o.color = (.80, .55, .18, 1)
    sc, cam = setup_scene(tag)
    shoot(sc, cam, O / f'drum_{tag}_side.png', neck_lo, Vector((1, 0, 0)) * 1 + Vector((0, -0.25, 0.15)),
          Vector((0, 0, 1)), 0.24)
    shoot(sc, cam, O / f'drum_{tag}_front.png', neck_lo, Vector((0, -1, 0)) * 1 + Vector((0, 0, 0.2)),
          Vector((0, 0, 1)), 0.24)
    print('RENDERED', tag, flush=True)

# 2) assembled: receiver + drum
bpy.ops.wm.open_mainfile(filepath=str(ACC / 'A762_AccessoryReady_Editable.blend'), use_scripts=False)
r = bpy.data.objects['SK_M4_Infima']
sc = bpy.context.scene
recv = bpy.data.objects.get('A762_Receiver')
collar = bpy.data.objects.get('A762_R02_Receiver_MagwellCollar')
with bpy.data.libraries.load(str(ACC / 'SM_A762_drum.blend'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects]
drum = [o for o in dst.objects if o is not None and o.type == 'MESH']
for o in drum:
    sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
keep = [o for o in (recv, collar) if o] + drum
for o in sc.objects:
    if o.type == 'MESH':
        vis = o in keep
        o.hide_render = not vis
        if o.name in bpy.context.view_layer.objects:
            o.hide_set(not vis)
recv.color = (.55, .55, .58, 1)
if collar:
    collar.color = (.45, .45, .48, 1)
for o in drum:
    o.color = (.80, .55, .18, 1)
rest = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
# drum meshes are authored in the magazine-bone rest frame; bring them into the
# scene's rest world so they sit where the game puts them
drum_xf = r.matrix_world @ rest
for o in drum:
    o.matrix_world = drum_xf @ o.matrix_world
pts = [o.matrix_world @ v.co for o in drum for v in o.data.vertices]
centre = sum(pts, Vector()) / len(pts)
lo = Vector((min(p[i] for p in pts) for i in range(3)))
hi = Vector((max(p[i] for p in pts) for i in range(3)))
port = Vector((centre.x, centre.y, lo.z + (hi.z - lo.z) * 0.80))
sc2, cam2 = setup_scene('asm')
shoot(sc2, cam2, O / 'drum_assembled_side.png', port, Vector((1, 0, 0)) * 1 + Vector((0, -0.2, 0.1)),
      Vector((0, 0, 1)), 0.22)
shoot(sc2, cam2, O / 'drum_assembled_front.png', port, Vector((0, -1, 0)) * 1 + Vector((0.15, 0, 0.15)),
      Vector((0, 0, 1)), 0.22)
print('RENDERED assembled', flush=True)
print('DRUM_RENDER_OK', flush=True)
