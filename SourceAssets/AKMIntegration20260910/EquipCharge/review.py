import bpy,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'AKM_EquipCharge_Editable.blend'))
code=(O.parent/'review_matched_motion.py').read_text()
code=code[code.index("r=bpy.data.objects"):]
code=code.replace("cases=[('idle',0)] if '--idle-only' in sys.argv else [('idle',0),('reload',70),('reload',145),('reload_empty',260),('reload_empty',355)]","cases=[('charge',0),('charge',66),('charge',96),('charge',204)]")
code=code.replace("bpy.data.actions['AKM_Native_'+clip]","bpy.data.actions['AKM_EquipCharge']")
exec(compile(code,__file__,'exec'))
