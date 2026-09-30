"""Update the editable full FK source with the repaired static attachment."""
import bpy
from pathlib import Path
O=Path(__file__).parent;D=O.parent/'Drum46'
bpy.ops.wm.open_mainfile(filepath=str(D/'LMG201_Drum46_Animated.blend'),use_scripts=False);bpy.context.preferences.filepaths.save_version=0
old=bpy.data.objects['SM_LMG201_LargeDrum'];rig=old.parent
with bpy.data.libraries.load(str(O/'LMG201_DrumJoint47.blend'),link=False) as (src,dst):dst.objects=['SM_LMG201_LargeDrum']
new=dst.objects[0];new.data.transform(rig.data.bones['WPN_SOCKET_Magazine'].matrix_local);old.data=new.data
old.vertex_groups.clear();group=old.vertex_groups.new(name='WPN_SOCKET_Magazine');group.add(list(range(len(old.data.vertices))),1.,'REPLACE');bpy.data.objects.remove(new,do_unlink=True)
old['revision']='DrumJoint47 closed adapter; Drum46 native FK actions unchanged';bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_DrumJoint47_Animated.blend'),compress=True);print('D47_EDITABLE_SAVED',flush=True)
