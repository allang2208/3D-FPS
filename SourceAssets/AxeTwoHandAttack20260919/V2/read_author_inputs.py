"""Read existing axe wrist geometry and upstream attack poses for V2 authoring."""
import bpy
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent / 'Axe_TwoHand_Attack_Editable.blend'))
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
scene = bpy.context.scene
action = bpy.data.actions['A_Harvest_Axe_Swing']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
rows = []
for t in [0, .18, .26, .30, .4, .48, .62, .82, 1.1]:
    s = t * .24 / .48 if t <= .48 else .24 + (t-.48)*.44/.62
    f = s * 150
    scene.frame_set(int(f), subframe=f-int(f))
    bpy.context.view_layer.update()
    row = {'t': t}
    for side in ['r', 'l']:
        u, l, h = ['%s_%s' % (x, side) for x in ['upperarm','lowerarm','hand']]
        pose = {n: rig.pose.bones[n].matrix.copy() for n in [u,l,h]}
        rest_axis = (rest[h].translation-rest[l].translation).normalized()
        ideal = (pose[h].to_quaternion() @ rest[h].to_quaternion().inverted()) @ rest_axis
        fore = (pose[h].translation-pose[l].translation).normalized()
        row[side] = {'wrist_bend_deg': math.degrees(ideal.angle(fore)),
                     'shoulder': list(pose[u].translation), 'elbow':list(pose[l].translation),
                     'wrist': list(pose[h].translation), 'neutral_fore_direction':list(ideal)}
    rows.append(row)
out = {'existing_axe': rows, 'reference': {}}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(HERE / 'Reference/Barbarian.glb'))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
scene = bpy.context.scene
print('REFERENCE_BONES', [b.name for b in rig.data.bones], flush=True)
for action in bpy.data.actions:
    if '2H_Melee_Attack' not in action.name:
        continue
    rig.animation_data_create()
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    start, end = action.frame_range
    fps = scene.render.fps / scene.render.fps_base
    samples = []
    for i in range(21):
        f = start + (end-start)*i/20
        scene.frame_set(int(f), subframe=f-int(f))
        bpy.context.view_layer.update()
        samples.append({'seconds':(f-start)/fps, 'pose':{
            b.name:[list(row) for row in (rig.matrix_world @ b.matrix)] for b in rig.pose.bones
            if any(x in b.name.lower() for x in ['hand','arm','weapon','wrist','chest'])}})
    out['reference'][action.name] = {'fps':fps,'frame_range':[start,end],
                                    'duration_s':(end-start)/fps,'samples':samples}
(HERE / 'author_inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('EXISTING_WRIST_GEOMETRY', json.dumps(rows), flush=True)
print('REFERENCE_CLIPS',json.dumps({n:{k:v for k,v in a.items() if k!='samples'} for n,a in out['reference'].items()}),flush=True)
