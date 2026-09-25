"""Verify the rebuilt A762 drum: receiver clearance per height band, and renders
of the tower alone and seated in the receiver."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
ACC = S / 'A762Meshy20260920/Accessories05'
DONOR = S / 'LargeDrumUpgrade20260920/Export/SM_AKM_LargeDrum_Upgrade.fbx'
BANDS = [(0.030, 0.045), (0.045, 0.055), (0.055, 0.065), (0.065, 0.075), (0.075, 0.090)]
NEW = O / 'SM_A762_drum.blend'

bpy.ops.wm.open_mainfile(filepath=str(ACC / 'A762_AccessoryReady_Editable.blend'), use_scripts=False)
r = bpy.data.objects['SK_M4_Infima']
sc = bpy.context.scene
rest = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
xf = rest.inverted() @ r.matrix_world.inverted()
recv = bpy.data.objects['A762_Receiver']
tree = BVHTree.FromPolygons([xf @ (recv.matrix_world @ v.co) for v in recv.data.vertices],
                            [list(p.vertices) for p in recv.data.polygons], all_triangles=False)


def probe(label, points):
    rows = {}
    for lo, hi in BANDS:
        sel = [p for p in points if lo <= p.z < hi]
        if not sel:
            rows['%d-%d' % (lo * 1000, hi * 1000)] = None
            continue
        d = []
        for p in sel:
            loc, nor, _, dist = tree.find_nearest(p)
            if loc is None:
                continue
            d.append(-dist * 1000 if (p - loc).dot(nor) < 0 else dist * 1000)
        d.sort()
        rows['%d-%d' % (lo * 1000, hi * 1000)] = {'n': len(d), 'min': round(d[0], 2),
                                                  'med': round(d[len(d) // 2], 2),
                                                  'pen': sum(1 for x in d if x < -0.5)}
    print(label, json.dumps(rows), flush=True)
    return rows


with bpy.data.libraries.load(str(NEW), link=False) as (src, dst):
    dst.objects = [n for n in src.objects]
drum = [o for o in dst.objects if o is not None and o.type == 'MESH']
for o in drum:
    sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
pts_local = [o.matrix_world @ v.co for o in drum for v in o.data.vertices]
res = {'rebuilt': probe('rebuilt tower ', pts_local)}
pts = [r.matrix_world @ rest @ p for p in pts_local]
for o in drum:
    o.matrix_world = r.matrix_world @ rest @ o.matrix_world

# render: assembled side/front and the tower alone
for o in sc.objects:
    if o.type == 'MESH':
        keep = o in drum or o is recv or o.name == 'A762_R02_Receiver_MagwellCollar'
        o.hide_render = not keep
        if o.name in bpy.context.view_layer.objects:
            o.hide_set(not keep)
recv.color = (.55, .55, .58, 1)
for o in drum:
    o.color = (.80, .55, .18, 1)
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'OBJECT'; sc.display.shading.show_cavity = True
sc.display.shading.background_type = 'WORLD'
if not sc.world:
    sc.world = bpy.data.worlds.new('W')
sc.world.color = (.09, .09, .09)
sc.render.resolution_x = 900; sc.render.resolution_y = 700; sc.render.resolution_percentage = 100
sc.render.use_compositing = False; sc.render.use_sequencer = False
cam = bpy.data.objects.new('C', bpy.data.cameras.new('C')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.26
pts_local = [xf @ p for p in pts]
lo = Vector((min(p[i] for p in pts_local) for i in range(3)))
hi = Vector((max(p[i] for p in pts_local) for i in range(3)))
port = (lo + hi) / 2
port = Vector((port.x, port.y, lo.z + (hi.z - lo.z) * 0.85))
port_w = r.matrix_world @ rest @ port
for nm, d in (('side', Vector((1, 0, 0))), ('front', Vector((0, -1, 0)))):
    cam.location = port_w + (r.matrix_world.to_3x3() @ d).normalized() * 1.2 + Vector((0, 0, 0.05))
    cam.rotation_euler = (port_w - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = str(O / f'rebuilt_assembled_{nm}.png')
    bpy.ops.render.render(write_still=True)
print('VERIFY_DRUM_OK', flush=True)
