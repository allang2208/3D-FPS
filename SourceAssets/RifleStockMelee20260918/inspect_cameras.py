"""读源文件里预设的预览相机与头部位置，用于渲染对位图。"""
import bpy
from pathlib import Path

DIR = Path(__file__).resolve().parent
SRC = DIR.parent / 'M4ContactImpact20260910' / 'M4_Hand_MAT_Editable.blend'

bpy.ops.wm.open_mainfile(filepath=str(SRC))
rig = bpy.data.objects['SK_M4_Infima']
act = bpy.data.actions['M4_idle']
rig.animation_data_create()
rig.animation_data.action = act
rig.animation_data.action_slot = act.slots[0]
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()

for n in ('head', 'neck_01', 'spine_03', 'pelvis', 'root'):
    if n in rig.pose.bones:
        print('[CAM] bone %s = %s' % (n, tuple(round(v, 4) for v in rig.pose.bones[n].matrix.translation)), flush=True)

for ob in [o for o in bpy.data.objects if o.type == 'CAMERA']:
    print('[CAM] %s loc=%s rot=%s lens=%s sensor=%s' % (
        ob.name, tuple(round(v, 3) for v in ob.matrix_world.translation),
        tuple(round(v, 1) for v in ob.rotation_euler),
        ob.data.lens, ob.data.sensor_width), flush=True)

scene = bpy.context.scene
print('[CAM] scene camera=%s res=%dx%d engine=%s' % (
    scene.camera.name if scene.camera else None, scene.render.resolution_x, scene.render.resolution_y,
    scene.render.engine), flush=True)
