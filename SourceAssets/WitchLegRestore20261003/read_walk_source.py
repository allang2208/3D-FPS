"""Read original walking leg positions and original garment dimensions."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

root = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchLegRestore20261003')
source = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Authoring/WitchRebuilt_Walk.blend')
bpy.ops.wm.open_mainfile(filepath=str(source))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
robe = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and 'OriginalRobe_Render' in o.name)
rest = {b.name: (rig.matrix_world @ b.matrix_local).translation.copy() for b in rig.data.bones}
down = ((rest['foot_l'] + rest['foot_r'])*.5 - rest['pelvis']).normalized()
across = (rest['thigh_r'] - rest['thigh_l']).normalized()
forward = ((rest['ball_l'] + rest['ball_r']) - (rest['foot_l'] + rest['foot_r'])).normalized()
forward = (forward - down*forward.dot(down) - across*forward.dot(across)).normalized()
rest_hip_rotation = (rig.matrix_world @ rig.data.bones['pelvis'].matrix_local).to_quaternion()
axes = [rest_hip_rotation.inverted() @ axis for axis in (down, across, forward)]
points = [robe.matrix_world @ v.co - rest['pelvis'] for v in robe.data.vertices]
report = {'source': str(source), 'robe_pelvis_relative_cm': {
    'min': [min(p.dot(axis)*100 for p in points) for axis in (down, across, forward)],
    'max': [max(p.dot(axis)*100 for p in points) for axis in (down, across, forward)]}, 'poses': []}
report['rest_leg_length_cm'] = (((rest['thigh_l']+rest['thigh_r'])*.5)-((rest['foot_l']+rest['foot_r'])*.5)).length*100
report['rest_pelvis_to_ankle_cm'] = (((rest['foot_l']+rest['foot_r'])*.5)-rest['pelvis']).dot(down)*100
scene = bpy.context.scene
for fraction in (0., .125, .25, .375, .5, .625, .75, .875):
    frame = scene.frame_start + (scene.frame_end-scene.frame_start)*fraction
    scene.frame_set(int(frame), subframe=frame-int(frame))
    hip = rig.matrix_world @ rig.pose.bones['pelvis'].matrix
    q = hip.to_quaternion()
    report['poses'].append({'fraction': fraction, 'frame': frame, 'feet_pelvis_relative_cm': {
        bone: [(p.dot(q @ axis)*100) for axis in axes]
        for bone in ('calf_l','calf_r','foot_l','foot_r','ball_l','ball_r')
        for p in [(rig.matrix_world @ rig.pose.bones[bone].matrix).translation-hip.translation]}})
(root / 'Receipts/walk-source.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('WITCH_WALK_SOURCE ' + json.dumps(report))
