import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
args=sys.argv[sys.argv.index('--')+1:];source=Path(args[0]);label=args[1]
bpy.ops.wm.open_mainfile(filepath=str(source));rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
def degrees(q):
    a=math.degrees(q.angle);return min(a,360-a)
report={};rows={}
for clip in ['A_ThunderHammer_CallCharge','A_ThunderHammer_CallRelease']:
    action=bpy.data.actions[clip];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    cliprows=[];prev={};summary={s:{} for s in ('l','r')}
    for frame in range(round(action.frame_range[1])+1):
        scene.frame_set(frame);pose={b.name:b.matrix.copy() for b in rig.pose.bones};row={'t':frame/240}
        for s in ('l','r'):
            U,F,H=[x+'_'+s for x in ('upperarm','lowerarm','hand')]
            ua=(pose[F].translation-pose[U].translation).normalized();fa=(pose[H].translation-pose[F].translation).normalized()
            rb=(rest[H].translation-rest[F].translation).normalized()
            palm=pose[H].to_quaternion()@rest[H].to_quaternion().inverted()@rb
            twistbone='lowerarm_twist_01_'+s
            dq=pose[twistbone].to_quaternion()@rest[twistbone].to_quaternion().inverted()@(pose[F].to_quaternion()@rest[F].to_quaternion().inverted()).inverted()
            twist=(2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(fa),dq.w)+math.pi)%(2*math.pi)-math.pi
            metrics={'wrist_bend':math.degrees(fa.angle(palm)),'forearm_twist':math.degrees(twist),'elbow_flex':math.degrees(ua.angle(fa))}
            for n in (U,F,H,twistbone):
                local=pose[rig.data.bones[n].parent.name].inverted()@pose[n]
                metrics[n+'_step']=degrees(local.to_quaternion().rotation_difference(prev[n])) if n in prev else 0.
                prev[n]=local.to_quaternion()
            for name,value in metrics.items():
                if abs(value)>abs(summary[s].get(name,{}).get('value',-1)):
                    summary[s][name]={'value':value,'time':frame/240}
            row[s]={**metrics,'shoulder':list(pose[U].translation),'elbow':list(pose[F].translation),'wrist':list(pose[H].translation)}
        cliprows.append(row)
    report[clip]=summary;rows[clip]=cliprows
(P/(label+'-metrics.json')).write_text(json.dumps({'source':str(source),'summary':report,'frames':rows},indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
