import bpy
from pathlib import Path
O=Path(__file__).parent
for name in ['Compact_Baseline.blend','M4_Vertical_Fitted.blend']:
 bpy.ops.wm.open_mainfile(filepath=str(O/name));o=next(x for x in bpy.context.scene.objects if x.name.startswith('VG_'));world=o.matrix_world.copy();o.parent=None;o.matrix_world=world;bpy.ops.wm.save_as_mainfile(filepath=str(O/name))
