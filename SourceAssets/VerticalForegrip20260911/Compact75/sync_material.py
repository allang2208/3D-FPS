import bpy
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'))
with bpy.data.libraries.load(str(O/'VerticalForegrip_Refined.blend'),link=False) as (a,b):b.objects=['SM_VerticalForegrip']
mesh=b.objects[0].data
for o in bpy.context.scene.objects:
 if o.name.startswith('VG_'):o.data=mesh
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Vertical_Fitted.blend'))
