"""Keep the upgraded firing and speedloader actions with the single-load source."""
import bpy
from pathlib import Path
O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(O/'DanWesson715_SingleLoad_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
with bpy.data.libraries.load(str(O.parent/'DanWesson715Upgrade20260914/DanWesson715_Upgrade_Editable.blend'),link=False) as (src,dst):
    dst.actions=[name for name in src.actions if name.startswith('DW715V2_') and name not in bpy.data.actions]
for action in dst.actions:
    if action:action.use_fake_user=True
bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_SingleLoad_Editable.blend'))
print('DW715_SINGLE_COMBINED_SOURCE_SAVED',flush=True)
