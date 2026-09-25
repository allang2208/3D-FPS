"""Does the untouched donor tower poke out of the A762 receiver?
Renders the donor drum seated on the rifle, next to the shipped and rebuilt ones."""
import bpy, sys
from pathlib import Path
from mathutils import Vector

O = Path(__file__).parent; S = O.parent
ACC = S / 'A762Meshy20260920/Accessories05'
DONOR = S / 'LargeDrumUpgrade20260920/Export/SM_AKM_LargeDrum_Upgrade.fbx'


def assemble(tag, load):
    bpy.ops.wm.open_mainfile(filepath=str(ACC / 'A762_AccessoryReady_Editable.blend'), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    sc = bpy.context.scene
    rest = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
    recv = bpy.data.objects['A762_Receiver']
    load(r, sc)
    drum = [o for o in sc.objects if o.get('is_drum')]
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
        sc.world = bpy.data.worlds.new('W' + tag)
    sc.world.color = (.09, .09, .09)
    sc.render.resolution_x = 900; sc.render.resolution_y = 700; sc.render.resolution_percentage = 100
    sc.render.use_compositing = False; sc.render.use_sequencer = False
    cam = bpy.data.objects.new('C' + tag, bpy.data.cameras.new('C' + tag))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.30
    pts = [o.matrix_world @ v.co for o in drum for v in o.data.vertices]
    lo = Vector((min(p[i] for p in pts) for i in range(3)))
    hi = Vector((max(p[i] for p in pts) for i in range(3)))
    mid = (lo + hi) / 2
    port = Vector((mid.x, mid.y, lo.z + (hi.z - lo.z) * 0.90))
    for nm, d in (('side', Vector((1, 0, 0))), ('front', Vector((0, -1, 0)))):
        cam.location = port + d * 1.2 + Vector((0, 0, 0.04))
        cam.rotation_euler = (port - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = str(O / f'{tag}_assembled_{nm}.png')
        bpy.ops.render.render(write_still=True)
    print('RENDERED', tag, flush=True)


def load_blend(path):
    def f(r, sc):
        d = sc.frame_set
        with bpy.data.libraries.load(str(path), link=False) as (src, dst):
            dst.objects = [n for n in src.objects]
        for o in dst.objects:
            if o is None or o.type != 'MESH':
                continue
            sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
            o['is_drum'] = 1
            o.matrix_world = r.matrix_world @ r.data.bones['WPN_SOCKET_Magazine'].matrix_local @ o.matrix_world
    return f


def load_fbx(path):
    def f(r, sc):
        before = set(sc.objects)
        bpy.ops.import_scene.fbx(filepath=str(path))
        for o in [o for o in bpy.context.scene.objects if o.type == 'MESH' and o not in before]:
            o['is_drum'] = 1
            o.matrix_world = r.matrix_world @ r.data.bones['WPN_SOCKET_Magazine'].matrix_local @ o.matrix_world
    return f


assemble('donor', load_fbx(DONOR))
assemble('rebuilt', load_blend(O / 'SM_A762_drum.blend'))
print('ASSEMBLED_RENDER_OK', flush=True)
