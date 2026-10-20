import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'SVCH_Replacement_Editable.blend'),load_ui=False)
for ob in bpy.context.scene.objects:
 if ob.type=='ARMATURE' or ob.name.startswith('SVCH_New') or ob.name=='RearClamp':
  print(ob.name,'world',list(map(list,ob.matrix_world)),'parent inverse',list(map(list,ob.matrix_parent_inverse)))
