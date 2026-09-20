"""Fit a rigid two-hand pickaxe frame to lateral elbow support for authoring."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
ROOT=Path(r'D:\FPS3D\FPSGAME');HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/RusticPickaxe20260919/RusticPickaxe_TwoHand_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];a=bpy.data.actions['A_RusticPickaxe_Idle'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};idle={b.name:b.matrix.copy() for b in rig.pose.bones}
ready=idle['WPN_root'];grips={s:ready.inverted()@idle['hand_'+s] for s in ('l','r')}
pivot=Vector((0,0,.19))
def frame(center,pitch,roll):
    p=math.radians(pitch);z=Vector((0,math.sin(p),math.cos(p)));x=Vector((0,math.cos(p),-math.sin(p)))
    q=Quaternion(z,math.radians(roll))@Matrix((x,z.cross(x),z)).transposed().to_quaternion()
    return Matrix.LocRotScale(Vector(center)-q@pivot,q,Vector((1,1,1)))
report={'ready':{'q':list(ready.to_quaternion()),'shaft':list(ready.to_quaternion()@Vector((0,0,1))),'point':list(ready.to_quaternion()@Vector((1,0,0)))},'neutral':{s:list(grips[s].to_quaternion()@rest['hand_'+s].to_quaternion().inverted()@(rest['hand_'+s].translation-rest['lowerarm_'+s].translation).normalized()) for s in ('l','r')},'keys':{}}
for label,center,pitch,lift,forward in [('top',(-.015,.29,.24),-20,.13,.04),('impact',(-.015,.365,-.32),65,.005,.04),('follow',(-.015,.38,-.38),78,0,.04)]:
    candidates=[]
    for roll in range(-15,16,5):
        W=frame(center,pitch,roll);rows={};cost=0
        for s,sign in [('l',-1),('r',1)]:
            U,F,H=[n+'_'+s for n in ('upperarm','lowerarm','hand')]
            options=[]
            for griproll in (range(-175,1,5) if s=='l' else range(-25,26,5)):
              grip=Matrix.Rotation(math.radians(griproll),4,'Z')@grips[s];hand=W@grip
              l1=(rest[F].translation-rest[U].translation).length;l2=(rest[H].translation-rest[F].translation).length
              shoulder=idle[U].translation+Vector((sign*.012,forward,lift));target=hand.translation;d=target-shoulder;direction=d.normalized();dist=d.length
              along=(l1*l1-l2*l2+dist*dist)/(2*dist);rad=math.sqrt(max(0,l1*l1-along*along))
              pole=Vector((sign*.8,-.45,-.2 if label=='top' else .1));pole=(pole-direction*pole.dot(direction)).normalized()
              elbow=shoulder+direction*along+pole*rad;f=(target-elbow).normalized()
              neutral=hand.to_quaternion()@rest[H].to_quaternion().inverted()@(rest[H].translation-rest[F].translation).normalized()
              angle=neutral.angle(f)
              c=angle**2+(1000 if dist>l1+l2-.01 else 0)
              options.append((c,griproll,elbow,target,math.degrees(angle)))
            chosen=min(options,key=lambda c:c[0]);cost+=chosen[0]
            rows[s]={'griproll':chosen[1],'elbow':list(chosen[2]),'wrist':list(chosen[3]),'bend':chosen[4]}
        candidates.append({'roll':roll,'cost':cost,'arms':rows})
    best=sorted(candidates,key=lambda c:c['cost'])[:3];report['keys'][label]=best
(HERE/'pose_fit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
