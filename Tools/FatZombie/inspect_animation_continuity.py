"""Read delivered FBX motion without saving or changing the source assets."""
import bpy
import json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/FatZombieMeshy20260913')
OUT = Path('D:/FPS3D/FPSGAME/Saved/FatZombieContinuity')
OUT.mkdir(parents=True, exist_ok=True)
result = {}
for role in ('Idle', 'Walk', 'Attack', 'Death'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT / 'final' / f'A_FatZombie_{role}.fbx'))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    action = rig.animation_data.action
    start, end = (round(x) for x in action.frame_range)
    names = [b.name for b in rig.pose.bones]
    samples = []
    for frame in range(start, end + 1):
        bpy.context.scene.frame_set(frame)
        samples.append({n: rig.matrix_world @ rig.pose.bones[n].matrix for n in names})
    stats = {}
    for name in names:
        p = [s[name].translation for s in samples]
        steps = [(p[i] - p[i-1]).length * 100 for i in range(1, len(p))]
        angles = [samples[i-1][name].to_quaternion().rotation_difference(samples[i][name].to_quaternion()).angle * 57.29578 for i in range(1, len(p))]
        stats[name] = {
            'first_cm': list(p[0] * 100), 'last_cm': list(p[-1] * 100),
            'range_cm': [(max(v[a] for v in p) - min(v[a] for v in p)) * 100 for a in range(3)],
            'seam_cm': (p[-1] - p[0]).length * 100,
            'max_step_cm': max(steps), 'max_step_frame': start + 1 + steps.index(max(steps)),
            'max_step_degrees': max(angles),
        }
    result[role] = {'frames': [start, end], 'fps': bpy.context.scene.render.fps,
                    'rig_matrix': [list(row) for row in rig.matrix_world], 'bones': stats,
                    'positions_cm': [{n: list(s[n].translation * 100) for n in names} for s in samples]}
    print('FAT_CONTINUITY ' + json.dumps({'role': role, 'frames': [start, end],
        'bones': {n: stats[n] for n in ('Hips', 'Head', 'LeftFoot', 'RightFoot') if n in stats}}), flush=True)
(OUT / 'delivered_fbx_before.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
