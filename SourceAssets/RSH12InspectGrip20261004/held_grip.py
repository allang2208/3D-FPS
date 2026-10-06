import json
import math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from grip_scene import pose,matrix
from grip_motion import correct,quat
O=Path(__file__).parent

class HeldGrip:
    def __init__(self,rig,D,profile,meta):
        self.rig,self.D,self.meta=rig,D,meta
        self.recipe=json.loads((O/'production_single_r_inspect.json').read_text())
        inspect=D['clips']['inspect']['samples'][72]
        p=pose(rig,D,profile,'inspect',inspect);correct(p,rig,meta,self.recipe)
        self.held={n:(p[rig.data.bones[n].parent.name].inverted()@p[n]) for n in p if n.endswith('_r') and n.startswith(('middle','ring','pinky'))}
        # The little finger wraps below the short grip. Lower its curl by rotating the MCP,
        # rather than translating a phalanx or cutting the grip silhouette.
        frame=p['WPN_root']@Matrix(meta['alignment'])
        n='pinky_01_r';par=rig.data.bones[n].parent.name
        axis=p[par].to_quaternion().inverted()@(frame.to_quaternion()@Vector((0,1,0)))
        t,q,s=self.held[n].decompose();self.held[n]=Matrix.LocRotScale(t,Quaternion(axis,.0523598776)@q,s)
        axis=p[par].to_quaternion().inverted()@(frame.to_quaternion()@Vector((0,0,1)))
        t,q,s=self.held[n].decompose();self.held[n]=Matrix.LocRotScale(t,Quaternion(axis,-.0698131701)@q,s)
        finish=O/'pinky_finish.json'
        if finish.exists():
            for n,v in json.loads(finish.read_text())['local_targets'].items():self.held[n]=matrix(v)
        self.inspect_local={n:p[rig.data.bones[n].parent.name].inverted()@p[n] for n in p if n.endswith('_r') and n.startswith(('index','thumb'))}
        self.ready_local={n:m.copy() for n,m in self.inspect_local.items()}
        ready=O/'ready_index_thumb.json'
        if ready.exists():
            for n,v in json.loads(ready.read_text())['local_delta'].items():
                t,q,s=self.ready_local[n].decompose();self.ready_local[n]=Matrix.LocRotScale(t,quat(v)@q,s)
        n='index_metacarpal_r';par=rig.data.bones[n].parent.name
        axis=p[par].to_quaternion().inverted()@(frame.to_quaternion()@Vector((0,0,1)))
        t,q,s=self.ready_local[n].decompose();self.ready_local[n]=Matrix.LocRotScale(t,Quaternion(axis,-.0261799388)@q,s)
        self.source_idle=pose(rig,D,profile,'idle',D['clips']['idle']['samples'][0])
        self.source_inspect=pose(rig,D,profile,'inspect',inspect)
    def apply(self,p):
        changed=correct(p,self.rig,self.meta,self.recipe)
        for n,lp in self.held.items():
            parent=self.rig.data.bones[n].parent.name
            p[n]=p[parent]@lp;changed.add(n)
        return changed

    def local_q(self,p,n):
        return (p[self.rig.data.bones[n].parent.name].inverted()@p[n]).to_quaternion()

    def authored(self,p,kind):
        from contact_motion import smooth,mix
        old={n:m.copy() for n,m in p.items()};frame=p['WPN_root']@Matrix(self.meta['alignment']);reference=self.source_idle
        def relative(source,side):return (source['WPN_root']@Matrix(self.meta['alignment'])).inverted()@source['hand_'+side]
        def gate(side,ref):
            a,b=relative(old,side),relative(ref,side)
            d=(a.translation-b.translation).length
            angle=a.to_quaternion().rotation_difference(b.to_quaternion()).angle
            angle=min(angle,6.283185307-angle)
            return (1-smooth((d-.008)/.018))*(1-smooth((angle-.12)/.3))
        w=gate('r',reference);changed=set()
        if w>1e-6:
            changed.update(self.apply(p))
            # Native inspection straightens the index. Retain its timing while fitting both endpoints.
            numerator=denominator=0.
            for n in ('index_01_r','index_02_r','index_03_r'):
                a=self.local_q(self.source_idle,n);b=self.local_q(self.source_inspect,n);c=self.local_q(old,n)
                def log(q):
                    if q.w<0:q.negate()
                    axis,angle=q.to_axis_angle();return axis*angle
                v=log(b@a.inverted());u=log(c@a.inverted());numerator+=u.dot(v);denominator+=v.dot(v)
            phase=max(0.,min(1.,numerator/max(denominator,1e-8)))
            for n,target in self.inspect_local.items():
                par=self.rig.data.bones[n].parent.name
                di=target.to_quaternion()@self.local_q(self.source_inspect,n).inverted()
                dr=self.ready_local[n].to_quaternion()@self.local_q(self.source_idle,n).inverted()
                lp=old[par].inverted()@old[n];t,q,s=lp.decompose()
                rotation=dr.slerp(di,phase)@q
                if n=='thumb_01_r':
                    axis=p[par].to_quaternion().inverted()@(frame.to_quaternion()@Vector((0,0,1)))
                    rotation=Quaternion(axis,.0698131701*math.sin(math.pi*phase))@rotation
                p[n]=p[par]@Matrix.LocRotScale(t,rotation,s);changed.add(n)
            if w<.999999:
                for n in changed:p[n]=mix(old[n],p[n],w)
        # Keep the original 715 support-hand contact with the gripping hand. Moving it
        # away from the weapon alone introduces a visible gap between the two hands.
        return changed
