"""Render an ASH-12 source clip from the recorded ASH-12 camera frame.

Camera basis comes from ASH12RightEdgeCharge20260919/authoring.json, so the framing
is the one the accepted right-edge-charge round authored against.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ASH12Fix20260925')
S = HERE.parent
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CLIP = ARGS[0]
FRAMES = [int(v) for v in ARGS[1:] if v.lstrip('-').isdigit()]
TAG = next((a for a in ARGS[1:] if not a.lstrip('-').isdigit()), CLIP)
OUT = HERE / 'Review'
OUT.mkdir(parents=True, exist_ok=True)

CLIPS = {
    'reload_empty': (S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
                     'ASH12_EmptyReload_RightEdgeReachPullReturn'),
    'quick_melee': (S / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
                    'ASH12_QuickCombat_N_Base'),
    'idle': (S / 'ASH1220260917/ASH12_Editable.blend', 'ASH12_idle'),
}
CAM = dict(eye=Vector((-0.07281457632780075, -0.19707617163658142, 0.12465998530387878)),
           right=Vector((0.9999997615814209, -0.0007808567606844008, 0.0)),
           forward=Vector((0.000780856644269079, 0.9999996423721313, -9.368201426696032e-05)),
           up=Vector((7.315222205761529e-08, 9.368197788717225e-05, 1.0)))

blend, action_name = CLIPS[CLIP]
EXTRA = [a for a in ARGS[1:] if not a.lstrip('-').isdigit() and a != 'gamecam']
if len(EXTRA) >= 2:
    blend, action_name = Path(EXTRA[0]), EXTRA[1]
TAG = EXTRA[2] if len(EXTRA) > 2 else CLIP
if 'gamecam' in ARGS:  # true runtime viewmodel eye instead of the recorded authoring anchor
    CAM = dict(eye=Vector((0.0, -0.10, 0.05)), right=Vector((1.0, 0.0, 0.0)),
               forward=Vector((0.0, 1.0, 0.0)), up=Vector((0.0, 0.0, 1.0)))
bpy.ops.wm.open_mainfile(filepath=str(blend), use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
act = bpy.data.actions[action_name]
scene = bpy.context.scene

basis = Matrix((CAM['right'], CAM['up'], -CAM['forward'])).transposed().to_4x4()
basis.translation = CAM['eye']
cam = bpy.data.objects.new('Ash12Cam', bpy.data.cameras.new('Ash12Cam'))
scene.collection.objects.link(cam)
cam.matrix_world = basis
cam.data.clip_start = 0.005
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 24
cam.data.lens = 24 / (2 * math.tan(math.radians(75 / 2)))
scene.camera = cam
for ob in scene.objects:
    if ob.type == 'MESH':
        ob.hide_render = not any(m.type == 'ARMATURE' and m.object == rig for m in ob.modifiers)
        ob.color = (.55, .63, .70, 1) if ob == arms else (.20, .23, .27, 1)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'OBJECT'
scene.display.shading.show_backface_culling = False
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.view_settings.view_transform = 'Standard'
if not scene.world:
    scene.world = bpy.data.worlds.new('Ash12World')
scene.world.color = (.055, .065, .08)
scene.render.resolution_x = 1187
scene.render.resolution_y = 539
scene.render.image_settings.file_format = 'PNG'
bpy.context.view_layer.update()

for f in FRAMES:
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(f)
    bpy.context.view_layer.update()
    scene.render.filepath = str(OUT / f'{TAG}_{f:03d}.png')
    bpy.ops.render.render(write_still=True)
    print('ASH12_RENDER', TAG, f, flush=True)
