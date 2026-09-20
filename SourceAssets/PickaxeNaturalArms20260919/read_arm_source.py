"""Read the reported elbow fault in the existing pickaxe source, without edits."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'D:\FPS3D\FPSGAME')
HERE=Path(__file__).resolve().parent
revised = '--revised' in sys.argv
source = HERE/'Pickaxe_NaturalArms_Editable.blend' if revised else ROOT/'SourceAssets/PickaxeOverhead20260919/Pickaxe_Overhead_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=bpy.data.objects['SK_RusticPickaxe_Rig']; scene=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
report={'rest':{},'phases':[]}
for s in ('l','r'):
    names=[n+'_'+s for n in ('clavicle','upperarm','upperarm_twist_01','upperarm_twist_02','lowerarm','lowerarm_twist_01','lowerarm_twist_02','hand')]
    report['rest'][s]={n:{'position':list(rest[n].translation),'q':list(rest[n].to_quaternion()),'parent':rig.data.bones[n].parent.name} for n in names}
for clip,times in (('Swing',[0,.12,.24,.36,.46,.52,.56,.60,.69,.85,1.0,1.16]),('HitRecover',[0,.085,.20,.36,.56])):
    a=bpy.data.actions['A_RusticPickaxe_'+clip];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    for time in times:
        sec=(.24*time/.60 if time<=.60 else .24+.44*(time-.60)/.56) if clip=='Swing' else .44*time/.56
        f=sec*300;scene.frame_set(math.floor(f),subframe=f-math.floor(f))
        row={'clip':clip,'time':time,'arms':{}}
        for s in ('l','r'):
            U,F,H=[n+'_'+s for n in ('upperarm','lowerarm','hand')]
            m={n:rig.pose.bones[n].matrix.copy() for n in (U,F,H)}
            a1=(rest[F].translation-rest[U].translation).normalized();a2=(rest[H].translation-rest[F].translation).normalized()
            up=(m[F].translation-m[U].translation).normalized();fore=(m[H].translation-m[F].translation).normalized()
            ud=m[U].to_quaternion()@rest[U].to_quaternion().inverted()
            fd=m[F].to_quaternion()@rest[F].to_quaternion().inverted()
            hd=m[H].to_quaternion()@rest[H].to_quaternion().inverted()
            neutral=hd@a2
            hinge=(ud@a2).rotation_difference(fore)@ud
            delta=fd@hinge.inverted()
            twist=(2*math.atan2(Vector(delta[1:]).dot(fore),delta.w)+math.pi)%(2*math.pi)-math.pi
            row['arms'][s]={'shoulder':list(m[U].translation),'elbow':list(m[F].translation),'wrist':list(m[H].translation),'wrist_bend_deg':math.degrees(neutral.angle(fore)),'elbow_twist_deg':math.degrees(twist),'upper_axis_error_deg':math.degrees((ud@a1).angle(up))}
        report['phases'].append(row)
(HERE/('revised_arm_diagnosis.json' if revised else 'source_diagnosis.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
for row in report['phases']:
    print(row['clip'],row['time'],{s:{'elbow_x':round(a['elbow'][0],3),'wrist_bend':round(a['wrist_bend_deg'],1),'elbow_twist':round(a['elbow_twist_deg'],1)} for s,a in row['arms'].items()},flush=True)
