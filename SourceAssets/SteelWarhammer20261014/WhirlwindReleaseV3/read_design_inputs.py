"""Read existing authored key poses for the new swing and handoff design."""
import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
rows={}
for label,path,rig_name,fps in [
    ('hammer',P.parent/'WhirlwindGripV2/Warhammer_Whirlwind_IdleGrip_Editable.blend','SK_RusticPickaxe_Rig',300),
    ('sword',ROOT/'SourceAssets/Whirlwind20260920/RecoverV6/WhirlwindRecover_Manny_Editable.blend','SK_RuneSword_Rig',480)]:
    bpy.ops.wm.open_mainfile(filepath=str(path));scene=bpy.context.scene;rig=bpy.data.objects[rig_name]
    rows[label]={'keys':[],'action':rig.animation_data.action.name}
    for t in [0.,.14,.34,.5,.628,.892,1.028,1.18,1.3,1.48,1.64,1.82]:
        f=t*fps;scene.frame_set(int(f),subframe=f-int(f))
        w=rig.pose.bones['WPN_root'].matrix
        points={n:list(rig.pose.bones[n].matrix.translation) for n in ['upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r']}
        rows[label]['keys'].append({'t':t,'origin':list(w.translation),'axis':list(w.to_quaternion()@Vector((0,0,1))),
                                    'q':list(w.to_quaternion()),'points':points})
    scene.frame_set(0)
    rows[label]['left_finger_locals']={b.name:{'q':list(b.matrix_basis.to_quaternion()),'p':list(b.matrix_basis.translation)} for b in rig.pose.bones if b.name.endswith('_l') and b.name.startswith(('thumb','index','middle','ring','pinky'))}
(P/'design_inputs.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
for label,data in rows.items():
    print(label+' '+data['action'])
    for row in data['keys']:
        print(row['t'],'axis',[round(x,3) for x in row['axis']],'hands',[[round(x,3) for x in row['points']['hand_'+s]] for s in ('l','r')])
print('DESIGN_INPUTS_READ')
