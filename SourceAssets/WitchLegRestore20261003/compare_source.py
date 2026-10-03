"""Read the original Witch model/death action and the changed corpse source."""
import bpy
import json
from collections import defaultdict
from pathlib import Path

root = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchLegRestore20261003')
source = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Authoring')
report = {'runtime_tested': False, 'source_inspection': True}
for role, path in (
    ('original_model', source / 'WitchRebuilt_Master.blend'),
    ('changed_corpse', Path('D:/FPS3D/FPSGAME/SourceAssets/WitchCorpseFollow20261002/WitchRebuilt_CorpseFollow.blend')),
    ('original_death_action', source / 'WitchRebuilt_DeathBackward.blend'),
):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    data = {'source': str(path), 'bones': len(rig.data.bones), 'parts': []}
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or 'SimulationProxy' in obj.name:
            continue
        part = {'name': obj.name, 'vertices': len(obj.data.vertices)}
        if 'OriginalRobe_Render' in obj.name or 'LowerRobe' in obj.name:
            totals = defaultdict(float)
            for vertex in obj.data.vertices:
                for influence in vertex.groups:
                    totals[obj.vertex_groups[influence.group].name] += influence.weight
            part['average_bone_weights'] = {
                name: value / max(1, len(obj.data.vertices))
                for name, value in sorted(totals.items()) if value > 0.001
            }
        data['parts'].append(part)
    if role == 'original_death_action':
        scene = bpy.context.scene
        action = rig.animation_data.action if rig.animation_data else None
        data['action'] = action.name if action else None
        data['fps'] = scene.render.fps
        data['frame_range'] = [scene.frame_start, scene.frame_end]
        data['poses'] = []
        for ratio in (0.0, 0.6, 1.0):
            frame = scene.frame_start + (scene.frame_end - scene.frame_start) * ratio
            scene.frame_set(int(frame), subframe=frame-int(frame))
            data['poses'].append({'fraction': ratio, 'frame': frame, 'bones': {
                name: {'position_cm': list((rig.matrix_world @ rig.pose.bones[name].matrix).translation * 100),
                       'local_rotation': list(rig.pose.bones[name].matrix_basis.to_quaternion())}
                for name in ('pelvis','thigh_l','thigh_r','calf_l','calf_r','foot_l','foot_r')
            }})
    report[role] = data
(root / 'Receipts/source-comparison.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('WITCH_SOURCE_COMPARISON ' + json.dumps({
    role: {'parts': len(report[role]['parts']), 'bones': report[role]['bones']}
    for role in ('original_model','changed_corpse','original_death_action')}))
