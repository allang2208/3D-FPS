"""Read the actual M1911 author poses as production inputs, without rendering."""
from pathlib import Path
import json, math
import bpy
from mathutils import Vector

job = Path(__file__).parent
sources = job.parent
rows = {}
for side in ('single', 'r', 'l'):
    path = (sources / 'M1911ReloadTiming20260913/M1911_ReloadReady_Editable.blend' if side == 'single'
            else sources / f'PistolDualWield20260914/NaturalAimV3/M1911/{side}/M1911_{side}_Dual_Editable.blend')
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects['SK_M1911_Manny']
    scene = bpy.context.scene
    prefix = 'M1911_Contact_' if side == 'single' else f'Dual_M1911_{side}_'
    clips = ('fire', 'aim_fire', 'fire_last', 'aim_fire_last') if side == 'single' else ('fire', 'fire_last')
    actions = {name: bpy.data.actions.get(prefix + name) for name in clips}
    entries = {}
    for name, action in actions.items():
        rig.animation_data_create()
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        duration = float(action.frame_range[1]) / 60
        samples = []
        base = None
        for time in (0, .008333, .016667, .025, .033333, .05, .075, .10, .15, .22, .30, duration):
            frame = min(time, duration) * 60
            scene.frame_set(int(frame), subframe=frame % 1)
            bpy.context.view_layer.update()
            gun = rig.pose.bones['WPN_root'].matrix.copy()
            if base is None:
                base = gun.copy()
            delta = base.inverted() @ gun
            samples.append(dict(time=min(time, duration), translation_m=list(delta.translation),
                                euler_deg=[math.degrees(v) for v in delta.to_euler()],
                                hand_positions_m={s: list(rig.pose.bones['hand_' + s].matrix.translation)
                                                  for s in ('r', 'l')}))
        entries[name] = dict(source_action=action.name, source_duration=duration, samples=samples)
    rows[side] = dict(source=str(path), clips=entries)
(job / 'reference_poses.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
for side, data in rows.items():
    for name, entry in data['clips'].items():
        print('M1911_FIRE_SOURCE', side, name, entry['source_duration'],
              'sampled_root_rotation_deg', [round(max(abs(s['euler_deg'][i]) for s in entry['samples']), 3)
                                             for i in range(3)], flush=True)
