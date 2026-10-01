"""Read the existing, licensed Khaimera arm donors for this authoring recipe."""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parents[1] / 'Mutant3Khaimera20260923/claw_reference_20260923/Mutant3_OpenClaw_Animated.blend'
OUT.mkdir(parents=True, exist_ok=True)
keys = ['Hips', 'LeftArm', 'RightArm', 'RightForeArm', 'RightHand']
result = {}
for label in ['A', 'C']:
    filename = SOURCE
    bpy.ops.wm.open_mainfile(filepath=str(filename))
    rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
    lookup = {b.name.rsplit(':', 1)[-1]: b.name for b in rig.data.bones}
    missing = set(keys) - lookup.keys()
    if missing:
        raise RuntimeError('Required donor joints missing: ' + str(missing) + '; actual bones: ' + str(sorted(lookup)))
    action = next(a for a in bpy.data.actions if a.name == 'A_Mutant3_Claw' + label)
    rig.animation_data.action = action
    if action.slots: rig.animation_data.action_slot = action.slots[0]
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    start = float(action.frame_range[0])
    frames = []
    for index in range(31):
        frame = start + index / 60.0 * fps
        scene.frame_set(math.floor(frame), subframe=frame % 1.0)
        frames.append({name: [list(row) for row in rig.matrix_world @ rig.pose.bones[lookup[name]].matrix] for name in keys})
    result[label] = {
        'file': str(filename), 'action': action.name, 'seconds': 0.5, 'fps': 60,
        'rest': {name: [list(row) for row in rig.matrix_world @ rig.data.bones[lookup[name]].matrix_local] for name in keys},
        'frames': frames,
    }
    samples = {str(i): {name: [round(x, 4) for x in Matrix(frames[i][name]).translation]
                       for name in ['RightArm', 'RightForeArm', 'RightHand']} for i in [0, 11, 20, 30]}
    print('CLAW_DONOR_' + label + ' ' + json.dumps(samples), flush=True)
(OUT / 'donor_motion.json').write_text(json.dumps(result), encoding='utf-8')
print('CLAW_DONORS_SAMPLED', flush=True)
