"""Native gestures plus a shared, object-relative two-hand grip."""
import json,sys,math
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
O=Path(__file__).parent
sys.path.insert(0,str(O.parent/'RSH12InspectGrip20261004'))
from grip_scene import pose
sys.path.insert(0,str(O.parent/'RSH12Speedloader20261003'))
from contact_motion import carry_arm,smooth,mix

def quat(v):return Quaternion((v[3],*v[:3]))
def rotation(p,rig,n):return (p[rig.data.bones[n].parent.name].inverted()@p[n]).to_quaternion()

class UnifiedGrip:
    def __init__(self,rig,data,profile,meta):
        self.rig,self.meta=rig,meta
        self.idle=pose(rig,data,profile,'idle',data['clips']['idle']['samples'][0])
        self.inspect=pose(rig,data,profile,'inspect',min(data['clips']['inspect']['samples'],key=lambda s:abs(s['time']-1.2)))
        self.recipes={side:json.loads((O/f'grasp_{side}.json').read_text()) for side in ('r','l')}
        self.deltas={}
        for side,recipe in self.recipes.items():
            source=self.frame(self.idle).inverted()@self.idle['hand_'+side]
            self.deltas[side]=Matrix(recipe['hand_in_grip'])@source.inverted()

    def frame(self,p):return p['WPN_root']@Matrix(self.meta['alignment'])

    def authored(self,p,kind):
        old={n:m.copy() for n,m in p.items()}
        frame=self.frame(old);inv=frame.inverted();changed=set()
        # Native index extension is the phase signal; the inspect endpoint has
        # exactly its source local rotations, including its metacarpal.
        numerator=denominator=0.
        for n in ('index_01_r','index_02_r','index_03_r'):
            a=rotation(self.idle,self.rig,n);b=rotation(self.inspect,self.rig,n);c=rotation(old,self.rig,n)
            def log(q):
                if q.w<0:q.negate()
                axis,angle=q.to_axis_angle();return axis*angle
            v=log(b@a.inverted());u=log(c@a.inverted())
            numerator+=u.dot(v);denominator+=v.dot(v)
        extension=max(0.,min(1.,numerator/max(denominator,1e-8)))
        for side,recipe in self.recipes.items():
            hand='hand_'+side
            source=self.frame(self.idle).inverted()@self.idle[hand]
            actual=inv@old[hand]
            angle=source.to_quaternion().rotation_difference(actual.to_quaternion()).angle
            angle=min(angle,2*math.pi-angle)
            weight=(1-smooth(((source.translation-actual.translation).length-.010)/.025))*(1-smooth((angle-.12)/.3))
            if weight<1e-6:continue
            target=frame@self.deltas[side]@inv@old[hand]
            moved=carry_arm(p,old,list(p),side,mix(old[hand],target,weight))
            for n,qv in recipe['local_grasp_rotations'].items():
                parent=self.rig.data.bones[n].parent.name
                lp=old[parent].inverted()@old[n];t,q,s=lp.decompose()
                if 'metacarpal' in n:
                    target_q=q # Retain the original palm/knuckle arrangement.
                elif side=='r' and n.startswith(('index','thumb')):
                    delta=quat(qv)@rotation(self.idle,self.rig,n).inverted()
                    if n.startswith('index'):delta=delta.slerp(Quaternion(),extension)
                    target_q=delta@q
                else:target_q=quat(qv)
                p[n]=p[parent]@Matrix.LocRotScale(t,q.slerp(target_q,weight),s)
                moved.add(n)
            changed.update(moved)
        return changed
