"""Read the rejected gather and donor joint frames for the wrist repair."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;data={}
for label,path in [('rejected',P.parent/'UppercutRearHighV4/Warhammer_Uppercut_RearHigh_Editable.blend'),
                   ('donor',P.parent/'UppercutV1/Warhammer_Uppercut_Editable.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['SK_RusticPickaxe_Rig'];s=bpy.context.scene
    rest={b.name:b.matrix_local.copy() for b in r.data.bones};rows=[]
    for t in [0,.2,.4,.6,.8,1.,1.025,1.05]:
        f=t*240;s.frame_set(int(f),subframe=f-int(f));pose={b.name:b.matrix.copy() for b in r.pose.bones}
        row={'t':t,'arms':{},'weapon':[list(x) for x in pose['WPN_root']]}
        for side in ('l','r'):
            U,L,H=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
            fore=(pose[H].translation-pose[L].translation).normalized()
            native=(rest[H].translation-rest[L].translation).normalized()
            hand_axis=pose[H].to_quaternion()@rest[H].to_quaternion().inverted()@native
            deform={n:pose[n].to_quaternion()@rest[n].to_quaternion().inverted() for n in [L,H,'lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side]}
            edge=deform['lowerarm_twist_01_'+side].rotation_difference(deform[H]).angle
            row['arms'][side]={'wrist_bend_degrees':math.degrees(fore.angle(hand_axis)),
                'twist01_to_hand_degrees':math.degrees(min(edge,2*math.pi-edge)),
                'bones':{n:[list(x) for x in pose[n]] for n in [U,L,H,'clavicle_'+side,'lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side]},
                'hand_to_forearm':[list(x) for x in pose[L].inverted()@pose[H]]}
        rows.append(row)
        print(label,t,'left bend/edge',round(row['arms']['l']['wrist_bend_degrees'],2),round(row['arms']['l']['twist01_to_hand_degrees'],2),
              'left pos',list(pose['hand_l'].translation),'right bend',round(row['arms']['r']['wrist_bend_degrees'],2))
    data[label]=rows
(P/'joint_inputs.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
