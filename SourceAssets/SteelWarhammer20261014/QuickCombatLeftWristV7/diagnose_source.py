"""Read the reported wrist/forearm chain from the currently authored V6 source."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
p=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(p.parent/'QuickCombatReachV6/Warhammer_QuickCombat_ReachV6_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene=bpy.context.scene
rig.data.pose_position='POSE'
rows=[]
for t in (0,.03,.06,.09,.12,.15,.175,.20,.25,.33,.4,.5):
    f=t*300;scene.frame_set(int(f),subframe=f-int(f));row={'time':t}
    for side in ('l','r'):
        u,l,h=[rig.pose.bones[n+'_'+side].matrix.copy() for n in ('upperarm','lowerarm','hand')]
        ru,rl,rh=[rig.data.bones[n+'_'+side].matrix_local.copy() for n in ('upperarm','lowerarm','hand')]
        upper=l.translation-u.translation;fore=h.translation-l.translation
        hand_dir=(h.to_quaternion()@rh.to_quaternion().inverted())@(rh.translation-rl.translation)
        q=(h.to_quaternion()@rh.to_quaternion().inverted())@(l.to_quaternion()@rl.to_quaternion().inverted()).inverted()
        a=2*math.atan2(Vector((q.x,q.y,q.z)).dot(fore.normalized()),q.w)
        a=(a+math.pi)%(2*math.pi)-math.pi
        row[side]={'wrist_axis_bend_deg':math.degrees(fore.angle(hand_dir)),
                   'hand_forearm_twist_deg':math.degrees(a),
                   'elbow_flex_deg':math.degrees(upper.angle(fore)),
                   'reach_ratio':(h.translation-u.translation).length/(upper.length+fore.length),
                   'shoulder':list(u.translation),'elbow':list(l.translation),'wrist':list(h.translation)}
    rows.append(row)
(p/'source_chain_before.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
for row in rows:print('WRIST_SOURCE',row['time'],{s:{k:round(v,2) for k,v in row[s].items() if isinstance(v,float)} for s in ('l','r')})
