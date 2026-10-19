import json
from pathlib import Path
import bpy
from mathutils import Vector
p=Path('D:/FPS3D/FPSGAME/SourceAssets/Zhanmadao20261018')
e={'__file__':str(p/'ChixiaoDoubleHeavyV1/author_motion.py')}
exec(compile((p/'ChixiaoDoubleHeavyV1/author_motion.py').read_text('utf-8').split('receipt=')[0],'helpers','exec'),e)
a=e['A']
for v in ('Standard','LongGrip'):
 bpy.ops.wm.open_mainfile(filepath=str(p/'ChixiaoGripV2'/v/'Chixiao_GripV2_Editable.blend'))
 rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
 mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.vertex_groups)
 clip=json.loads((p/'ChixiaoGripV2'/v/'editable_keys.json').read_text())
 w=e['pose_at'](clip,.30)
 bpy.context.scene.frame_set(72)
 print('COORD',v,'rig',list(map(list,rig.matrix_world)),'mesh',list(map(list,mesh.matrix_world)),'hand_key',list(w['hand_r'].translation),'hand_blend',list((rig.matrix_world@rig.pose.bones['hand_r'].matrix).translation),'upper_key',list(w['upperarm_r'].translation),flush=True)