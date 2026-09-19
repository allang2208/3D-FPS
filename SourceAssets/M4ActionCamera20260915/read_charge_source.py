"""Read the active M4 equip source's charging-handle travel for camera timing."""
import bpy, json
from pathlib import Path
O = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent / 'M4WrapGrip20260910/M4_Hand_MAT_Editable.blend'))
rig = bpy.data.objects['SK_M4_Infima']
action = bpy.data.actions['M4_MAT_equip_charge']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
rows = []
for frame in range(39):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    local = rig.pose.bones['WPN_root'].matrix.inverted() @ rig.pose.bones['WPN_ChargingHandle'].matrix
    rows.append({'frame': frame, 'source_seconds': frame / 60., 'handle_local': list(local.translation)})
(O / 'charge-source.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('CHARGE_SOURCE', json.dumps(rows[8:27]), flush=True)
