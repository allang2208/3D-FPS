"""Assemble the editable material and contact authoring into one source file."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O/'QBZ191_Wear_Editable.blend'))
names=[x['action'] for x in json.loads((O/'build.json').read_text()).values()]
with bpy.data.libraries.load(str(O/'QBZ191_Contact_Editable.blend'),link=False) as (src,dst):dst.actions=names
for action in dst.actions:action.use_fake_user=True
r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['QBZ191_base_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
bpy.context.scene.frame_set(0);bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_ContactWear_Editable.blend'))
print('QBZ_CONTACT_WEAR_EDITABLE_SAVED',flush=True)
