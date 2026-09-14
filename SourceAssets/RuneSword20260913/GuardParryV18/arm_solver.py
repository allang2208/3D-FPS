"""Continuous two-hand grasp paths with a stateless, closed arm pose solution."""
import math
import numpy as np
from mathutils import Matrix,Vector,Quaternion

def frame(direction,normal):
    y=direction.normalized();x=normal-y*normal.dot(y);x.normalize();z=x.cross(y)
    return Matrix((x,y,z)).transposed().to_quaternion()

def settle_hold(values,hold):
    if hold is None:return values
    first,last=hold;fixed=values[(first+last)//2].copy()
    values[first:last+1]=fixed
    # Smooth the shoulder/grasp solution into and out of the fixed load pose.
    for i in range(1,7):
        u=i/6;w=u*u*(3-2*u)
        if first-i>=0:values[first-i]=fixed+(values[first-i]-fixed)*w
        if last+i<len(values):values[last+i]=fixed+(values[last+i]-fixed)*w
    return values

def segment_gap(a,b,c,d):
    u=b-a;v=d-c;w=a-c
    aa=u.dot(u);bb=u.dot(v);cc=v.dot(v);dd=u.dot(w);ee=v.dot(w)
    denom=aa*cc-bb*bb
    s=max(0,min(1,(bb*ee-cc*dd)/denom)) if abs(denom)>1e-10 else 0
    t=(bb*s+ee)/cc
    if t<0:t=0;s=max(0,min(1,-dd/aa))
    elif t>1:t=1;s=max(0,min(1,(bb-dd)/aa))
    return (w+s*u-t*v).length

def forearms_cross_in_view(a,b,c,d):
    if min(a.y,b.y,c.y,d.y)<.09:return False
    a,b,c,d=[np.array((v.x/v.y,v.z/v.y)) for v in [a,b,c,d]]
    u=b-a;v=d-c;w=c-a;cross=lambda p,q:p[0]*q[1]-p[1]*q[0]
    determinant=cross(u,v)
    if abs(determinant)<1e-8:return False
    s=cross(w,v)/determinant;t=cross(w,u)/determinant
    point=a+s*u
    return .08<s<.92 and .08<t<.92 and abs(point[0])<1.34 and abs(point[1])<.77

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
    def fit_path(self,frames,constant=False,hold=None):
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
                    if hold and hold[0]<i<=hold[1] and diff!=0:continue
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
            result[side]=[float(a) for a in settle_hold(path,hold)]
        return result
    def fit_support(self,frames,grasps,hold=None):
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
            filtered=settle_hold(filtered,hold)
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
    def separate_arms(self,frames,grasps,chains,hold):
        """Jointly choose elbow planes while both fists stay on the hilt.

        Optimisation is part of authoring: capsule clearance and projected
        forearm overlap compete with wrist bend and continuous elbow motion.
        It changes elbow poles only; shoulders, wrists and bone lengths stay.
        """
        n=len(frames);offsets=np.radians(np.arange(-45,46,15));count=len(offsets)
        states=[(l,r) for l in range(count) for r in range(count)];center=len(states)//2
        state_ids=np.array(states);angles=offsets[state_ids]
        delta=state_ids[:,None,:]-state_ids[None,:,:]
        transition=np.sum((angles[:,None,:]-angles[None,:,:])**2,axis=2)*.5
        transition[np.max(np.abs(delta),axis=2)>1]=np.inf
        hands={side:[self.hand(side,sf,a) for sf,a in zip(frames,grasps[side])] for side in ['l','r']}
        options=[];costs=[];elbows=[]
        for f in range(n):
            candidates={};penalties={}
            # Fixed zero correction at the exact retained idle endpoints.
            w=min(1,f/12,(n-1-f)/12);w=w*w*(3-2*w)
            for side in ['l','r']:
                A,E=chains[side][f];H=hands[side][f];T=H.translation;axis=(T-A).normalized()
                pivot=A+axis*(E-A).dot(axis);pole=E-pivot
                rest=self.rest;old=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
                neutral=H.to_quaternion()@rest['hand_'+side].to_quaternion().inverted()@old
                candidates[side]=[];penalties[side]=[]
                for offset in offsets:
                    elbow=pivot+Quaternion(axis,float(offset*w))@pole
                    bend=(T-elbow).normalized().angle(neutral)
                    wrong_side=max(0,elbow.x+.025) if side=='l' else max(0,.025-elbow.x)
                    penalty=.55*bend*bend+8*max(0,bend-math.radians(50))**2+.05*offset*offset+6*wrong_side*wrong_side
                    candidates[side].append((A,elbow,T));penalties[side].append(penalty)
            row=[];ep=[]
            for li,ri in states:
                left=candidates['l'][li];right=candidates['r'][ri]
                cost=penalties['l'][li]+penalties['r'][ri]
                for a in range(2):
                    for b in range(2):
                        gap=segment_gap(left[a],left[a+1],right[b],right[b+1])
                        cost+=1800*max(0,.065-gap)**2
                if forearms_cross_in_view(left[1],left[2],right[1],right[2]):cost+=1.2
                row.append(cost);ep.append([*left[1],*right[1]])
            options.append(candidates);costs.append(row);elbows.append(ep)
        costs=np.array(costs);elbows=np.array(elbows)
        prev=np.full(len(states),np.inf);prev[center]=costs[0,center]
        back=np.zeros((n,len(states)),dtype=np.int16)
        for f in range(1,n):
            movement=np.sum((elbows[f-1,:,None,:]-elbows[f,None,:,:])**2,axis=2)*100
            links=transition
            if hold[0]<f<=hold[1]:links=np.where(np.eye(len(states),dtype=bool),0,np.inf)
            scores=prev[:,None]+links+movement
            back[f]=np.argmin(scores,axis=0);prev=costs[f]+scores[back[f],np.arange(len(states))]
        indices=[center]*n
        for f in range(n-1,0,-1):indices[f-1]=int(back[f,indices[f]])
        chosen=angles[indices]
        kernel=np.array([1,4,6,4,1])/16
        for side_index,side in enumerate(['l','r']):
            path=np.convolve(np.pad(chosen[:,side_index],(2,2),mode='edge'),kernel,mode='valid')
            path=settle_hold(path,hold)
            for f in range(n):
                A,E=chains[side][f];T=hands[side][f].translation;axis=(T-A).normalized()
                pivot=A+axis*(E-A).dot(axis);w=min(1,f/12,(n-1-f)/12);w=w*w*(3-2*w)
                chains[side][f]=(A,pivot+Quaternion(axis,float(path[f]*w))@(E-pivot))
        return chains

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
