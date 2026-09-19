import bpy,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'AKM_Soviet_Editable.blend'))
code=Path('D:/FPS3D/FPSGAME/SourceAssets/AKMIntegration20260910/review_matched_motion.py').read_text();code=code[code.index("r=bpy.data.objects"):]
exec(compile(code,__file__,'exec'))
