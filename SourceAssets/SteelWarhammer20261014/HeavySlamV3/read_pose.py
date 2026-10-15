import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'RhythmClearanceV2/Warhammer_Clearance_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];a=bpy.data.actions['A_Warhammer_Clearance_Slash1']
rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
out={}
for t in (0,28):
    bpy.context.scene.frame_set(t)
    out[str(t)]={n:list(rig.pose.bones[n].matrix.translation) for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l','clavicle_r','upperarm_r','lowerarm_r','hand_r','WPN_root')}
    wp=rig.pose.bones['WPN_root'].matrix
    out[str(t)]['axes']=[list(wp.to_quaternion()@v) for v in (Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))]
    out[str(t)]['grips']={s:list((wp.inverted()@rig.pose.bones['hand_'+s].matrix).translation) for s in ('l','r')}
(P/'source_pose.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
