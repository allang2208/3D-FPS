"""把作者源 clip 从视模视点渲染成一条对位胶片（制作用，不作为验收）。

Blender --background --factory-startup --python render_preview.py -- Base

相机放在骨架头部原点（Infima 视模约定：head 在原点），朝 +Y 看，18 mm ≈ 90° 水平 FOV，
与参考视频的第一人称取景同量级，用于和 Reference/dense_frames 对位比较。
输出 Preview/<profile>_strip.png 与 Preview/<profile>_f_XX.png。
"""
import json
import math
import sys
from pathlib import Path

import bpy

O = Path(__file__).resolve().parent
profile = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'Base'
manifest = json.loads((O / 'animation.json').read_text(encoding='utf-8'))
contact = manifest['contact']
duration = manifest['duration']

blend = O / profile / ('M4_QuickCombat_%s_Editable.blend' % profile)
bpy.ops.wm.open_mainfile(filepath=str(blend))
rig = bpy.data.objects['SK_M4_Infima']
scene = bpy.context.scene

def bound_to_rig(ob):
    for mod in ob.modifiers:
        if mod.type == 'ARMATURE' and mod.object and mod.object.name == rig.name:
            return True
    return False


for ob in bpy.context.view_layer.objects:
    if ob.type in ('MESH', 'ARMATURE'):
        keep = ob.name == rig.name or (ob.type == 'MESH' and bound_to_rig(ob))
        ob.hide_render = not keep
        try:
            ob.hide_set(not keep)
        except RuntimeError:
            pass

# 游戏侧口径（FPSGAMECharacter.h）：BaseVerticalFieldOfView=75°（MaintainYFOV）、
# M4HipViewmodelLocation=(0,7,-7)cm（视模在相机右 7cm、下 7cm）→ 相机在骨架空间
# 为「左 7cm、上 7cm」。焦距按垂直 75°/16:9 反算：2·atan(10.125/f)=75° → f≈13.2mm。
cam_data = bpy.data.cameras.new('QC_Preview')
cam_data.lens = 13.2
cam_data.sensor_width = 36.0
cam = bpy.data.objects.new('QC_Preview', cam_data)
scene.collection.objects.link(cam)
cam.location = (-0.07, 0.0, 0.07)
cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
scene.camera = cam

scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.image_settings.file_format = 'PNG'

out = O / 'Preview'
out.mkdir(exist_ok=True)
action = bpy.data.actions['M4_QuickCombat_%s' % profile]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]

# 与作者源时间轴的关键帧对齐（0.06 起手 / 0.19 蓄势顶点 / 0.24 保持 / 接触 / 0.44 跟随 / 0.72 收势）
TIMES = [0.00, 0.06, 0.19, 0.24, 0.30, contact, 0.44, 0.58, duration]
for t in TIMES:
    scene.frame_set(int(round(t * 60.0)))
    bpy.context.view_layer.update()
    path = out / ('%s_t%05d.png' % (profile, round(t * 1000)))
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print('[PREVIEW] rendered t=%.2f %s' % (t, path.name), flush=True)
print('[PREVIEW] M4_QUICKCOMBAT_FRAMES %s %d' % (profile, len(TIMES)), flush=True)
