"""Check the ASH-12 empty-reload action's real keyframe range and sample rate."""
import bpy, sys
from pathlib import Path

S = Path(r'D:\FPS3D\FPSGAME\SourceAssets')
BLEND = S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(BLEND), use_scripts=False)
scene = bpy.context.scene
rig = bpy.data.objects['SK_M4_Infima']
for name in ('ASH12_EmptyReload_RightEdgeReachPullReturn', 'ASH12_Reference_reload_empty', 'ASH12_idle'):
    act = bpy.data.actions.get(name)
    if not act:
        print('ACTION missing', name, flush=True)
        continue
    curves = {(c.data_path, c.array_index): c
              for layer in act.layers for strip in layer.strips
              for bag in strip.channelbags for c in bag.fcurves}
    keys = [(c.data_path, len(c.keyframe_points),
             round(c.keyframe_points[0].co[0], 2), round(c.keyframe_points[-1].co[0], 2))
            for c in curves.values()]
    frames = [k[1] for k in keys]
    print('ACTION', name, 'curves', len(curves), 'keys_per_curve', min(frames), max(frames),
          'range', act.frame_range[:], 'first/last', keys[0], flush=True)
print('SCENE fps', scene.render.fps, '/', scene.render.fps_base,
      'range', scene.frame_start, scene.frame_end, flush=True)
rig.animation_data.action = bpy.data.actions['ASH12_EmptyReload_RightEdgeReachPullReturn']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
for f in range(0, 800, 40):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    p = rig.pose.bones['hand_r'].matrix.translation
    print('SAMPLE_R', f, [round(v * 100, 1) for v in p], flush=True)
