import bpy
from pathlib import Path
O=Path(__file__).parent
for f in [O/'M4_Vertical_Fitted.blend']+list(O.glob('A_M4_Vertical_*.blend')):
 bpy.ops.wm.open_mainfile(filepath=str(f))
 with bpy.data.libraries.load(str(O/'VerticalForegrip_Refined.blend'),link=False) as (a,b):b.objects=['SM_VerticalForegrip']
 for ob in bpy.context.scene.objects:
  if ob.name.startswith('VG_'):ob.data=b.objects[0].data
 bpy.ops.wm.save_as_mainfile(filepath=str(f))
