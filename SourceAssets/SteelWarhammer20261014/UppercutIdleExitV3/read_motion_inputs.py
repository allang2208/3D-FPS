"""Read existing uppercut poses to place the new idle-grip exit and join."""
from pathlib import Path
import bpy,json
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'UppercutV1/Warhammer_Uppercut_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_RusticPickaxe_Rig'];rows=[]
for t in [0,.5,1,1.025,1.05,1.075,1.125,1.266667,1.5,2.05]:
    f=t*240;s.frame_set(int(f),subframe=f-int(f))
    w=r.pose.bones['WPN_root'].matrix
    row={'t':t,'weapon':list(w.translation),'q':list(w.to_quaternion()),
         'axis':list(w.to_quaternion()@Vector((0,0,1))),
         'head':list(w@Vector((0,0,.972475657))),
         'joints':{n:list(r.pose.bones[n].matrix.translation) for n in ['hand_l','hand_r','lowerarm_l','lowerarm_r','upperarm_l','upperarm_r']}}
    rows.append(row)
    print(json.dumps({'t':t,'weapon':[round(x,3) for x in row['weapon']],
        'axis':[round(x,3) for x in row['axis']],
        'hands':[[round(x,3) for x in row['joints']['hand_'+side]] for side in ('l','r')]}))
(P/'motion_inputs.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
