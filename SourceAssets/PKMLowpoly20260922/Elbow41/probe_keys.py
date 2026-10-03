"""Did the Elbow41 keys actually get written into the edit blend?"""
from pathlib import Path

import bpy

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
PAIRS = (
    ('equip', ROOT / 'EquipCharge31' / 'PKM_base_EquipCharge_Editable.blend',
     ROOT / 'Elbow41' / 'Edit' / 'PKM_equip_Elbow41.blend', 'PKM31_base_equip'),
    ('sprint_loop', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
     ROOT / 'Elbow41' / 'Edit' / 'PKM_sprint_loop_Elbow41.blend', 'PKM17_base_sprint_loop'),
)
WATCH = ['lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l']

for label, src, edit, action_name in PAIRS:
    for tag, path in (('src', src), ('edit', edit)):
        bpy.ops.wm.open_mainfile(filepath=str(path))
        scene = bpy.context.scene
        rig = bpy.data.objects['PKM_Manny_Rig']
        names = [a.name for a in bpy.data.actions]
        act = bpy.data.actions.get(action_name)
        print('\n=== %s / %s ===' % (label, tag))
        print('  actions:', names, '| wanted:', action_name, '| found:', act is not None)
        if act is None:
            continue
        print('  slots:', [s.identifier for s in act.slots],
              '| layers:', len(act.layers))
        nkeys = 0
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for c in bag.fcurves:
                        if any('"%s"' % n in c.data_path for n in WATCH):
                            nkeys += len(c.keyframe_points)
        print('  watch fcurve keys total:', nkeys)
        rig.animation_data.action = act
        rig.animation_data.action_slot = act.slots[0]
        print('  active slot:', rig.animation_data.action_slot.identifier)
        scene.frame_set(0)
        bpy.context.view_layer.update()
        for n in WATCH:
            q = rig.pose.bones[n].rotation_quaternion
            print('  f0   %-22s %s' % (n, [round(v, 5) for v in q]))
        if act.frame_range[1] > 40:
            scene.frame_set(40)
            bpy.context.view_layer.update()
            for n in WATCH:
                q = rig.pose.bones[n].rotation_quaternion
                print('  f40  %-22s %s' % (n, [round(v, 5) for v in q]))
print('\nKEY_PROBE_DONE')