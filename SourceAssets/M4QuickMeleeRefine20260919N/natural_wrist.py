"""Contact-centred grip turn, followed by a connected, length-preserving arm."""
import math
from mathutils import Matrix, Quaternion, Vector

ARM_BONES=('upperarm_r','upperarm_twist_01_r','upperarm_twist_02_r',
           'lowerarm_r','lowerarm_twist_01_r','lowerarm_twist_02_r')
EDITED=ARM_BONES+('hand_r','ik_hand_r')

def smooth(t):
    t=max(0,min(1,t)); return t*t*t*(10+t*(-15+6*t))

def frame(axis,normal):
    normal=(normal-axis*normal.dot(axis)).normalized()
    return Matrix((axis,normal.cross(axis).normalized(),normal)).transposed().to_quaternion()

class NaturalWrist:
    def __init__(self,idle,rest,stations):
        self.idle,self.rest,self.stations=idle,rest,stations
        self.previous=0.; self.roll_previous=0.
        self.pivot=Vector((0,.025,-.045)); self.grip_axis=Vector((0,-.48,.877)).normalized()
        self.restfore=(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
        self.records=[]

    def target(self,pose,angle):
        weapon=pose['WPN_root']
        turn=Quaternion(self.grip_axis,angle).to_matrix().to_4x4()
        local=Matrix.Translation(self.pivot) @ turn @ Matrix.Translation(-self.pivot)
        return weapon @ local @ weapon.inverted() @ pose['hand_r']

    def apply(self,pose,seconds):
        weight=smooth(seconds/.10)*(1-smooth((seconds-.72)/.146666667))
        if weight<1e-7:
            return {n:pose[n].copy() for n in EDITED if n in pose}
        shoulder=pose['upperarm_r'].translation
        old_elbow=pose['lowerarm_r'].translation; old_wrist=pose['hand_r'].translation
        upper=(old_elbow-shoulder).length; lower=(old_wrist-old_elbow).length
        cap=math.radians(160)*weight

        def candidate(angle):
            hand=self.target(pose,angle); wrist=hand.translation
            desired=hand.to_quaternion() @ self.rest['hand_r'].to_quaternion().inverted() @ self.restfore
            axis=(wrist-shoulder).normalized(); d=(wrist-shoulder).length
            along=(upper*upper-lower*lower+d*d)/(2*d)
            radius=math.sqrt(max(0,upper*upper-along*along))
            center=shoulder+axis*along
            pole=-desired+axis*desired.dot(axis)
            if pole.length<1e-6: pole=old_elbow-center
            pole.normalize()
            elbow=center+pole*radius
            fore=(wrist-elbow).normalized()
            bend=desired.angle(fore)
            unreachable=max(0,d-upper-lower+.002)
            # Strongly prioritize a straight wrist over retaining an impossible
            # palm direction. Keep the smallest practical turn around the grip.
            cost=(150*max(0,bend-math.radians(18))**2+.12*bend*bend
                  +.20*angle*angle+.15*(angle-self.previous)**2
                  +1.0*(elbow-old_elbow).length_squared+10000*unreachable**2)
            return cost,hand,elbow,fore,bend

        angles=[-cap+2*cap*i/128 for i in range(129)]
        angle=min(angles,key=lambda a:candidate(a)[0]); step=cap/64
        for _ in range(5):
            angle=min((max(-cap,angle-step),angle,min(cap,angle+step)),key=lambda a:candidate(a)[0]); step*=.5
        _,hand,elbow,fore,bend=candidate(angle); self.previous=angle
        # At entry and exit bring the elbow off the source pole smoothly.
        wrist=hand.translation; axis=(wrist-shoulder).normalized(); d=(wrist-shoulder).length
        along=(upper*upper-lower*lower+d*d)/(2*d); radius=math.sqrt(max(0,upper*upper-along*along))
        center=shoulder+axis*along
        oldpole=(old_elbow-center); oldpole-=axis*oldpole.dot(axis); oldpole.normalize()
        newpole=(elbow-center).normalized()
        rotation=oldpole.rotation_difference(newpole)
        pole=Quaternion().slerp(rotation,weight) @ oldpole
        elbow=center+pole*radius; fore=(wrist-elbow).normalized()
        up=(elbow-shoulder).normalized(); normal=up.cross(fore).normalized()
        idle=self.idle
        iu=(idle['lowerarm_r'].translation-idle['upperarm_r'].translation).normalized()
        iff=(idle['hand_r'].translation-idle['lowerarm_r'].translation).normalized()
        inn=iu.cross(iff).normalized()
        uq=frame(up,normal) @ frame(iu,inn).inverted() @ idle['upperarm_r'].to_quaternion()
        fq=frame(fore,normal) @ frame(iff,inn).inverted() @ idle['lowerarm_r'].to_quaternion()
        hand_delta=hand.to_quaternion() @ self.rest['hand_r'].to_quaternion().inverted()
        desired=hand_delta @ self.restfore
        neutral_delta=desired.rotation_difference(fore) @ hand_delta
        desired_fq=neutral_delta @ self.rest['lowerarm_r'].to_quaternion()
        q=desired_fq @ fq.inverted()
        roll=2*math.atan2(Vector((q.x,q.y,q.z)).dot(fore),q.w)
        roll+=2*math.pi*round((self.roll_previous-roll)/(2*math.pi))
        self.roll_previous=roll
        result={}
        for main,origin,orientation,axis,residual in (
            ('upperarm_r',shoulder,uq,up,0),('lowerarm_r',elbow,fq,fore,roll)):
            result[main]=Matrix.LocRotScale(origin,orientation,pose[main].to_scale())
            delta=orientation @ self.rest[main].to_quaternion().inverted()
            for suffix in ('01','02'):
                name=main.replace('_r',f'_twist_{suffix}_r')
                twist=Quaternion(axis,residual*self.stations[name])
                pos=origin+twist @ delta @ (self.rest[name].translation-self.rest[main].translation)
                rot=twist @ delta @ self.rest[name].to_quaternion()
                # Transport K's skin frame with this whole segment, then fade
                # the new roll distribution in. This keeps entry/exit skin
                # continuous even while the arm triangle barely moves.
                transport=orientation @ pose[main].to_quaternion().inverted()
                oldpos=origin+transport @ (pose[name].translation-pose[main].translation)
                oldrot=transport @ pose[name].to_quaternion()
                pos=oldpos.lerp(pos,weight)
                rot=oldrot.slerp(rot,weight)
                result[name]=Matrix.LocRotScale(pos,rot,pose[name].to_scale())
        result['hand_r']=hand
        if 'ik_hand_r' in pose: result['ik_hand_r']=hand.copy()
        self.records.append({'time':seconds,'grip_turn_deg':math.degrees(angle),'wrist_bend_deg':math.degrees(desired.angle(fore)),
                             'forearm_roll_deg':math.degrees(roll),'elbow_delta_cm':100*(elbow-old_elbow).length})
        return result
