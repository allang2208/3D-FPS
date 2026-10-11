"""Save the mechanical correction in the accepted R23 editable source."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Super90LoaderR23_20261010/Super90_Speedloader_R23.blend'))
patch=json.loads((O/'translation_patch.json').read_text())
data=json.loads((O/'blender_locations.json').read_text())
for clip in patch['clips']:
    action=bpy.data.actions[clip['name']]
    bag=action.layers[0].strips[0].channelbag(action.slots[0])
    for bone,values in data[clip['branch']].items():
        for axis in range(3):
            curve=next(c for c in bag.fcurves if c.data_path==f'pose.bones["{bone}"].location' and c.array_index==axis)
            for key in curve.keyframe_points:
                frame=round(key.co.x)
                if 0<=frame<len(values):key.co.y=values[frame][axis]
            curve.update()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_Speedloader_R24.blend'))
print('SUPER90_R24_EDITABLE_SAVED',flush=True)
