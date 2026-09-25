"""Render the reload from the game viewmodel camera anchor used by the accepted
reviews: (0, -0.10, 0.05) m, -Y forward, 75 deg vertical FOV, 2.39:1 frame."""
import bpy, math
from pathlib import Path

O = Path(__file__).parent; S = O.parent

JOBS = [
    ('m4', S / 'ExtMagContact20260919/A_M4_ExtContact_reload.blend', None, [43, 54, 61, 68, 76, 88, 95, 103]),
    ('m4e', S / 'ExtMagContact20260919/A_M4_ExtContact_reload_empty.blend', None, [35, 43, 54, 70, 80, 100, 111, 130]),
    ('m16', S / 'M16RemovalMelee20260920/Animations/base/A_M16_reload.blend', None, [43, 54, 61, 68, 76, 88, 95, 103]),
    ('m16e', S / 'M16RemovalMelee20260920/Animations/base/A_M16_reload_empty.blend', None, [35, 43, 54, 70, 80, 100, 111, 143]),
]

for label, path, action, frames in JOBS:
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = bpy.data.actions[action] if action else r.animation_data.action
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    sc = bpy.context.scene
    for o in sc.objects:
        if o.type == 'MESH':
            o.hide_render = False
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.show_shadows = True
    sc.display.shading.show_cavity = True
    sc.display.shading.show_backface_culling = False
    sc.display.shading.background_type = 'WORLD'
    sc.world.color = (.06, .07, .09)
    sc.render.resolution_x = 1240; sc.render.resolution_y = 520
    sc.render.resolution_percentage = 100
    sc.render.use_compositing = False; sc.render.use_sequencer = False
    cam = bpy.data.objects.new('VM_' + label, bpy.data.cameras.new('VM_' + label))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (0.0, -0.10, 0.05)
    cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
    cam.data.clip_start = .005
    cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24
    cam.data.lens = 24 / (2 * math.tan(math.radians(75 / 2)))
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = str(O / f'game_{label}_{int(f):03d}.png')
        bpy.ops.render.render(write_still=True)
print('GAME_OK', flush=True)
