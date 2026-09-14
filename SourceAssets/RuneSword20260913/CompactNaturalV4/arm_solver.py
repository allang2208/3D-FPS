"""Continuous two-hand grasp paths with a stateless, closed arm pose solution."""
import math
import numpy as np
from mathutils import Matrix,Vector,Quaternion

def frame(direction,normal):
    y=direction.normalized();x=normal-y*normal.dot(y);x.normalize();z=x.cross(y)
    return Matrix((x,y,z)).transposed().to_quaternion()

class ArmSolver:
    def __init__(self,rest,grasp,fingers):
        self.rest=rest;self.grasp=grasp;self.fingers=fingers;self.depth={'l':-.172,'r':-.072};self.ready={}
    def hand(self,side,sf,angle):
        return sf@Matrix.Translation((0,0,self.depth[side]))@Matrix.Rotation(angle,4,'Z')@self.grasp[side]
    def support(self,side,H):
        rest=self.rest;un,fn,hn=[p+'_'+side for p in ['upperarm','lowerarm','hand']]
        anchor=rest[un].translation;T=H.translation
        ru=rest[fn].translation-anchor;rf=rest[hn].translation-rest[fn].translation
        l1,l2=ru.length,rf.length;d=H.to_quaternion()@rest[hn].to_quaternion().inverted()@rf.normalized()
        preferred=anchor+Vector((-.025 if side=='l' else .025,.055,-.035))
        ideal=T-d*l2;near=ideal+(preferred-ideal).normalized()*l1;offset=near-anchor
        offset.x=max(-.13,min(.13,offset.x));offset.y=max(-.045,min(.12,offset.y));offset.z=max(-.10,min(-.01,offset.z))
        A=anchor+offset;axis=(T-A).normalized();dist=(T-A).length
        if dist>l1+l2-.018:A+=axis*(dist-(l1+l2-.018));dist=(T-A).length
        # Support the grip through the shoulder, while biasing the elbow down.
        # This avoids both a fully locked pole and an elbow entering the camera.
        down=Vector((-.45 if side=='l' else .45,-.15,-1));down-=axis*down.dot(axis)
        wanted=ideal-A;wanted-=axis*wanted.dot(axis)
        down.normalize();pole=(wanted/l2+down*.30).normalized()
        along=(l1*l1-l2*l2+dist*dist)/(2*dist);E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
        ud=(E-A).normalized();fd=(T-E).normalized();normal=ud.cross(fd).normalized();rnormal=ru.cross(rf).normalized()
        uq=frame(ud,normal)@frame(ru,rnormal).inverted()@rest[un].to_quaternion()
        fq=frame(fd,normal)@frame(rf,rnormal).inverted()@rest[fn].to_quaternion()
        neutral=fq@rest[fn].to_quaternion().inverted()@rest[hn].to_quaternion()
        delta=H.to_quaternion()@neutral.inverted()
        twist=(2*math.atan2(Vector((delta.x,delta.y,delta.z)).dot(fd),delta.w)+math.pi)%(2*math.pi)-math.pi
        bend=fd.angle(d)
        cost=bend*bend*.15+(A-preferred).length_squared*1.8
        cost+=max(0,E.z+.14)**2*40+max(0,E.y-.48)**2*2
        return cost,A,E,T,uq,fq,twist
    def ready_pose(self,sf):
        for side,seed in [('l',-29),('r',-126)]:
            seed=math.radians(seed)
            angles=[seed+math.radians(v) for v in range(-150,151)]
            # Retain the outward ready elbows and readable two-hand silhouette.
            self.ready[side]=min(angles,key=lambda a:self.support(side,self.hand(side,sf,a))[0]+(a-seed)**2*.006)
    def fit_path(self,frames,constant=False):
        result={};n=len(frames)
        for side in ['l','r']:
            if constant:result[side]=[self.ready[side]]*n;continue
            step=math.radians(2.5);count=433;center=count//2
            angles=self.ready[side]+(np.arange(count)-center)*step
            candidates=[]
            for sf in frames:
                row=[]
                for a in angles:
                    v=self.support(side,self.hand(side,sf,float(a)))
                    row.append([v[0],*v[1],*v[2]])
                candidates.append(row)
            candidates=np.array(candidates);costs=candidates[:,:,0]
            prev=np.full(count,np.inf);prev[center]=costs[0,center];back=np.zeros((n,count),dtype=np.int16)
            # Track complete revolutions, since +360 degrees is the same final
            # grasp. Forcing the scalar angle back to zero bends the wrist during
            # recovery even though the hand can close continuously at +360.
            for i in range(1,n):
                options=np.full((9,count),np.inf)
                for row,diff in enumerate(range(-4,5)):
                    start=max(0,diff);end=min(count,count+diff)
                    change=candidates[i,start:end,1:]-candidates[i-1,start-diff:end-diff,1:]
                    support_motion=np.sum(change*change*np.array([60,60,60,100,100,100]),axis=1)
                    options[row,start:end]=prev[start-diff:end-diff]+.35*(diff*step)**2+support_motion
                rows=np.argmin(options,axis=0);prev=costs[i]+options[rows,np.arange(count)]
                back[i]=np.arange(count)-(rows-4)
            indices=[center]*n;indices[-1]=min([center-144,center,center+144],key=lambda k:prev[k])
            for i in range(n-1,0,-1):indices[i-1]=int(back[i,indices[i]])
            path=angles[indices];final_angle=float(path[-1])
            # Smooth the discrete authoring grid before bone baking. Fixed end
            # angles give exactly the same hand and helper-bone pose on return.
            for _ in range(3):
                path=np.convolve(np.pad(path,(2,2),mode='edge'),np.array([1,4,6,4,1])/16,mode='valid')
                path[0]=self.ready[side];path[-1]=final_angle
            # Zero-velocity entry/exit over 20 ms, within the authored ready poses.
            for i in range(min(6,n)):
                u=i/5;w=u*u*(3-2*u)
                path[i]=self.ready[side]+(path[i]-self.ready[side])*w
                path[-1-i]=final_angle+(path[-1-i]-final_angle)*w
            result[side]=[float(a) for a in path]
        return result
    def fit_support(self,frames,grasps):
        result={};kernel=np.exp(-.5*(np.arange(-10,11)/3.5)**2);kernel/=kernel.sum()
        for side in ['l','r']:
            hands=[self.hand(side,sf,a) for sf,a in zip(frames,grasps[side])]
            raw=[self.support(side,H) for H in hands]
            values=[]
            for H,v in zip(hands,raw):
                A,E=v[1:3];axis=(H.translation-A).normalized()
                down=Vector((-.45 if side=='l' else .45,-.15,-1));down-=axis*down.dot(axis);down.normalize()
                lateral=axis.cross(down);pole=E-A;pole-=axis*pole.dot(axis)
                values.append([*A,math.atan2(pole.dot(lateral),pole.dot(down))])
            values=np.array(values);values[:,3]=np.unwrap(values[:,3])
            filtered=np.stack([np.convolve(np.pad(values[:,j],(10,10),mode='edge'),kernel,mode='valid') for j in range(4)],axis=1)
            filtered[0]=values[0];filtered[-1]=values[-1]
            un,fn,hn=[n+'_'+side for n in ['upperarm','lowerarm','hand']]
            l1=(self.rest[fn].translation-self.rest[un].translation).length
            l2=(self.rest[hn].translation-self.rest[fn].translation).length
            chain=[]
            for H,v in zip(hands,filtered):
                A=Vector(v[:3]);T=H.translation;axis=(T-A).normalized();dist=(T-A).length
                if dist>l1+l2-.018:A+=axis*(dist-(l1+l2-.018));dist=(T-A).length
                down=Vector((-.45 if side=='l' else .45,-.15,-1));down-=axis*down.dot(axis);down.normalize()
                pole=down*math.cos(v[3])+axis.cross(down)*math.sin(v[3])
                along=(l1*l1-l2*l2+dist*dist)/(2*dist)
                E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
                chain.append((A,E))
            result[side]=chain
        return result
    def apply_arm(self,p,side,H,chain=None):
        rest=self.rest;un,fn,hn=[a+'_'+side for a in ['upperarm','lowerarm','hand']]
        _,A,E,T,uq,fq,twist=self.support(side,H)
        if chain is not None:A,E=chain
        axis=(T-E).normalized()
        old_fore=(rest[hn].translation-rest[fn].translation).normalized()
        hand_deform=H.to_quaternion()@rest[hn].to_quaternion().inverted()
        aligned=hand_deform@old_fore
        fore_deform=aligned.rotation_difference(axis)@hand_deform
        fq=fore_deform@rest[fn].to_quaternion()
        old_upper=(rest[fn].translation-rest[un].translation).normalized()
        upper_axis=(E-A).normalized();normal=upper_axis.cross(axis).normalized()
        uq=frame(upper_axis,normal)@frame(old_upper,old_upper.cross(old_fore).normalized()).inverted()@rest[un].to_quaternion()
        p['clavicle_'+side].translation+=A-rest[un].translation
        p[un]=Matrix.LocRotScale(A,uq,Vector((1,1,1)))
        p[fn]=Matrix.LocRotScale(E,fq,Vector((1,1,1)))
        for prefix,parent in [('upperarm',un),('lowerarm',fn)]:
            for idx in ['01','02']:
                name=f'{prefix}_twist_{idx}_{side}'
                if name not in rest:continue
                # This rigid sword grasp pronates the complete supported arm.
                # Give helpers the same segment deformation; multiplying an
                # unwrapped +/- 180-degree scalar by 1/3 or 2/3 caused the V3
                # skin collapse and the 120-degree pose left at clip boundaries.
                p[name]=p[parent]@rest[parent].inverted()@rest[name]
        p[hn]=H
        for name,relative in self.fingers[side].items():p[name]=H@relative
