"""Read existing donor FBX takes for the user's staff animation search.

No project assets, runtime settings, previews or animations are modified.
"""
import bpy
import json
from pathlib import Path

root = Path('D:/FPS3D/FPSGAME')
source = root / 'SourceAssets/ThirdPersonSwordFree20261005/Kevin/Animations'
out = root / 'SourceAssets/ThirdPersonStaffAnimationSearch20261010'
out.mkdir(parents=True, exist_ok=True)
clips = [
    'Male/Combat/Polearm/HumanM@CombatIdlePolearm01.fbx',
    'Male/Combat/Polearm/HumanM@AttackPolearm01.fbx',
    'Masked Poses/HumanM@WeaponHoldPolearm01.fbx',
    'Male/Combat/1H/HumanM@CombatIdle1H01.fbx',
]
results = {}
for clip in clips:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source / clip), use_anim=True)
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    action = rig.animation_data.action
    start, end = action.frame_range
    names = [b.name for b in rig.pose.bones]
    samples = []
    for t in (0., .25, .5, .75, 1.):
        f = start + (end-start)*t
        bpy.context.scene.frame_set(int(f), subframe=f-int(f))
        bones = {}
        for b in rig.pose.bones:
            m = rig.matrix_world @ b.matrix
            bones[b.name] = {'position': list(m.translation), 'rotation_wxyz': list(m.to_quaternion())}
        samples.append({'phase': t, 'bones': bones})
    results[clip] = {'source': str(source / clip), 'action': action.name,
                    'frames': [start, end], 'fps': bpy.context.scene.render.fps,
                    'bone_names': names, 'samples': samples}
    print('STAFF_DONOR', clip, start, end, bpy.context.scene.render.fps)
    print('RIG_BONES', ','.join(names))
    print('FIRST_POSE', json.dumps({n:v for n,v in samples[0]['bones'].items()
                                 if any(k in n.lower() for k in ['hand', 'arm', 'weapon'])}))
(out / 'local-source-poses.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
