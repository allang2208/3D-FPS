import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ThrowRefineV3/ThunderHammer_ThrowRefineV3_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene=bpy.context.scene;rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
def framed(a,n):return Matrix((a,n,a.cross(n))).transposed().to_quaternion()
def project(v,a):return (v-a*v.dot(a)).normalized()
result=[]
for clip,times in [('A_ThunderHammer_ThrowCharge',[0,.3,.6,1.,1.3]),('A_ThunderHammer_ThrowRelease',[.06,.12,.18,.24])]:
    action=bpy.data.actions[clip];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    for t in times:
        f=t*240;scene.frame_set(int(f),subframe=f-int(f));wpn=rig.pose.bones['WPN_root'].matrix.copy()
        for s in ('l','r'):
            U,F,H=[n+'_'+s for n in ('upperarm','lowerarm','hand')];sgn=1 if s=='r' else -1
            shoulder=rig.pose.bones[U].matrix.translation;grip=wpn.inverted()@rig.pose.bones[H].matrix
            radial=Vector((grip.translation.x,grip.translation.y,0)).normalized(); flip=Quaternion(radial,math.pi)
            grip=Matrix.LocRotScale(grip.translation,flip@grip.to_quaternion(),Vector((1,1,1)))
            if s=='r':shoulder=Vector((.25,.11,-.18))
            a=(rest[F].translation-rest[U].translation).normalized();b=(rest[H].translation-rest[F].translation).normalized();rn=a.cross(b).normalized()
            l1=(rest[F].translation-rest[U].translation).length;l2=(rest[H].translation-rest[F].translation).length;best=None
            for roll in range(-180,180,5):
                hand=wpn@Quaternion((0,0,1),math.radians(roll)).to_matrix().to_4x4()@grip
                v=hand.translation-shoulder;axis=v.normalized();dist=v.length
                if dist>=(l1+l2)*.98:continue
                center=shoulder+axis*((l1*l1-l2*l2+dist*dist)/(2*dist));radius=math.sqrt(max(0.,l1*l1-(center-shoulder).length_squared));guide=project(Vector((sgn*.85,-.15,-.40)),axis)
                neutral=hand.to_quaternion()@rest[H].to_quaternion().inverted()@b
                for j in range(-180,180,5):
                    elbow=center+Quaternion(axis,math.radians(j))@guide*radius
                    ua=(elbow-shoulder).normalized();fa=(hand.translation-elbow).normalized();normal=ua.cross(fa).normalized()
                    df=framed(fa,normal)@framed(b,rn).inverted();full=neutral.rotation_difference(fa)@hand.to_quaternion()@rest[H].to_quaternion().inverted();dq=full@df.inverted()
                    twist=(2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(fa),dq.w)+math.pi)%(2*math.pi)-math.pi
                    bend=neutral.angle(fa)
                    cost=3*bend*bend+1.5*twist*twist+.025*math.radians(roll)**2
                    cost+=600*max(0.,.095-sgn*elbow.x)**2+280*max(0.,.15-elbow.length)**2
                    cost+=70*max(0.,elbow.z-hand.translation.z+.018)**2+25*max(0.,.075-elbow.y)**2
                    if best is None or cost<best['cost']:best={'cost':cost,'roll':roll,'pole':j,'bend':math.degrees(bend),'twist':math.degrees(twist),'elbow':list(elbow)}
            result.append({'clip':clip,'t':t,'side':s,**(best or {})})
(P/'contact-fit-supported.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
