"""Read the accepted motion's late poses to place the free-hand path."""
from pathlib import Path
import bpy,json
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'WhirlwindFlowV4/Warhammer_Whirlwind_Flow_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_RusticPickaxe_Rig'];s.frame_set(0)
g=r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_l'].matrix
rows=[]
for t in [0,1.04,1.10,1.16,1.24,1.32,1.4,1.48,1.56,1.64,1.7,1.76,1.82]:
    f=t*300;s.frame_set(int(f),subframe=f-int(f))
    w=r.pose.bones['WPN_root'].matrix
    row={'t':t,'grip':list((w@g).translation),'left':list(r.pose.bones['hand_l'].matrix.translation),
         'right':list(r.pose.bones['hand_r'].matrix.translation),'axis':list(w.to_quaternion()@Vector((0,0,1)))}
    rows.append(row)
    print(json.dumps({k:([round(v,3) for v in x] if isinstance(x,list) else x) for k,x in row.items()}))
(P/'motion_inputs.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
