"""Read existing idle contacts and rig coordinates for the sprint authoring inputs."""
import bpy, json
from pathlib import Path
O = Path(__file__).resolve().parent
specs = json.loads((O / 'sources.json').read_text(encoding='utf-8'))
record = {}
for weapon, spec in specs.items():
    for profile, (source, action_name) in spec['profiles'].items():
        bpy.ops.wm.open_mainfile(filepath=str(O.parent / source))
        rig = bpy.data.objects['SK_M4_Infima']
        action = bpy.data.actions[action_name] if action_name else rig.animation_data.action
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        bpy.context.scene.frame_set(0)
        bpy.context.view_layer.update()
        item = {'source': source, 'action': action.name, 'frames': list(action.frame_range),
                'fps': bpy.context.scene.render.fps,
                'rig_scale': list(rig.scale), 'bones': {n: list(rig.pose.bones[n].matrix.translation)
                    for n in ('hand_r', 'hand_l', 'upperarm_r', 'lowerarm_r', 'WPN_root', 'WPN_SOCKET_Muzzle')}}
        record[weapon + ':' + profile] = item
        print('RIFLE_SOURCE', weapon, profile, json.dumps(item), flush=True)
(O / 'source-poses.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
