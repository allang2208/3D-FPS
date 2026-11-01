import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'JiLeiSeatV1/JiLeiMotionV1_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];sc=bpy.context.scene
a=bpy.data.actions['A_ThunderHammer_CallCharge'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
out={}
for frame in [0,192,480]:
 sc.frame_set(frame);p={b.name:b.matrix.copy() for b in rig.pose.bones};w=p['WPN_root'];row={n:list(p[n].translation) for n in ['WPN_root','hand_r','lowerarm_r','upperarm_r','hand_l']}
 row['shaft']=list(w.to_quaternion()@Vector((0,0,1)));row['head']=list(w@Vector((0,0,.916)))
 out[frame]=row
out['rest']={s:{n:list(rig.data.bones[n+'_'+s].matrix_local.translation) for n in ['upperarm','lowerarm','hand']} for s in ['r','l']}
(P/'source-keyposes.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out),flush=True)
