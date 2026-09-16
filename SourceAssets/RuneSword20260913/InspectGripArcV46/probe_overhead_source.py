"""What the accepted heavy attack actually contains, and where its poses sit."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
sys.path.insert(0, str(P))
import twirl_model as model

SOURCE = P.parent / 'ChargedErgoV43/AzureRunesword_ChargedHoldV45.blend'
WANTED = ('A_RuneSword_HeavyCharge', 'A_RuneSword_HeavyRelease', 'A_RuneSword_Idle')

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
mesh = bpy.data.objects['RuneSword_Blade']
fps = scene.render.fps / scene.render.fps_base
print('source %s' % SOURCE.name)
print('fps %.2f  objects %s' % (fps, [o.name for o in bpy.data.objects
                                      if o.name.startswith(('SK_', 'Rune'))]))
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
geometry = model.sword_geometry(rest['WPN_root'], mesh)
animated = set()
for action in bpy.data.actions:
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if curve.data_path.startswith('pose.bones["'):
                        animated.add(curve.data_path.split('"')[1])

report = {'source': str(SOURCE), 'fps': fps, 'animated_bones': sorted(animated),
          'actions': {}}
for action in bpy.data.actions:
    if not action.name.startswith('A_RuneSword'):
        continue
    start, end = action.frame_range
    report['actions'][action.name] = [round(start, 1), round(end, 1),
                                      round((end - start) / fps, 4)]
print('%d animated bones' % len(animated))
print('%-34s %8s %8s %8s' % ('action', 'first', 'last', 'seconds'))
for name, value in sorted(report['actions'].items()):
    print('%-34s %8.1f %8.1f %8.3f' % (name, value[0], value[1], value[2]))

for clip in WANTED:
    action = bpy.data.actions.get(clip)
    if not action:
        continue
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    start, end = map(int, action.frame_range)
    print('=== %s' % clip)
    print('%8s %9s %9s %9s %9s %9s' % ('sec', 'handY', 'pomY', 'tipY', 'tipZ', 'handZ'))
    for frame in list(range(start, min(start + 12, end) + 1, 2)) + [end]:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        hand = rig.pose.bones['hand_r'].matrix
        full = rig.pose.bones['WPN_root'].matrix @ rest['WPN_root'].inverted()
        tip = full @ geometry['high']
        pommel = full @ geometry['low']
        print('%8.3f %9.4f %9.4f %9.4f %9.4f %9.4f'
              % (frame / fps, hand.translation.y, pommel.y, tip.y, tip.z,
                 hand.translation.z))
(P / 'probe_overhead_source.json').write_text(json.dumps(report, indent=2),
                                              encoding='utf-8')
print('PROBE_OVERHEAD_SOURCE_DONE')
