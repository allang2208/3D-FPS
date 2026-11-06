"""Continuous upper/forearm frames for the native V7 weights. Component-space metres."""
import math
import numpy as np
from mathutils import Quaternion,Vector

def smooth_centres(centres):
    weights=(1,4,7,10,7,4,1)
    return [sum((centres[min(max(i+j-3,0),len(centres)-1)]*v for j,v in enumerate(weights)),Vector())/sum(weights)
            for i in range(len(centres))]

def balance_elbow_cap(A,poses,rest,side):
    # Adjacent vertices at the elbow are weighted to both shafts. Choose their
    # axial rotations jointly across the complete take, with the hand fixed.
    # A global path avoids a change of winding when the observed seam crosses 180°.
    name=lambda n:n+'_'+side
    u,l,h=map(name,('upperarm','lowerarm','hand'))
    grid=np.arange(-75.,76.,5.);zero=len(grid)//2
    step=.9*(grid[:,None]-grid[None,:])**2
    penalty=.12*(grid[:,None]**2+grid[None,:]**2)
    prev=np.full(penalty.shape,np.inf);prev[zero,zero]=0.
    parents=[];axes=[];previous_u=previous_f=None
    for p in poses:
        ua=(p[l].translation-p[u].translation).normalized()
        fa=(p[h].translation-p[l].translation).normalized()
        axes.append((ua,fa))
        ru=p[u].to_quaternion()@rest[u].to_quaternion().inverted()
        rf=p[l].to_quaternion()@rest[l].to_quaternion().inverted()
        qu=np.array([list(Quaternion(ua,math.radians(g))@ru) for g in grid])
        qf=np.array([list(Quaternion(fa,math.radians(g))@rf) for g in grid])
        angle=np.rad2deg(2*np.arccos(np.clip(np.abs(qu@qf.T),0.,1.)))
        def movement(old,new):
            if old is None:return step
            delta=np.rad2deg(2*np.arccos(np.clip(np.abs(old@new.T),0.,1.)))
            return step+3.*np.maximum(delta-12.,0.)**2
        upper=prev[:,:,None]+movement(previous_u,qu)[:,None,:]
        up_index=upper.argmin(axis=0).T;up_min=upper.min(axis=0).T
        fore=up_min[:,:,None]+movement(previous_f,qf)[None,:,:]
        parents.append((up_index,fore.argmin(axis=1)))
        prev=fore.min(axis=1)+penalty+3.5*np.maximum(angle-86.,0.)**2+18.*np.maximum(angle-108.,0.)**2
        previous_u,previous_f=qu,qf
    path=[];ui=fi=zero
    for up_index,fore_index in reversed(parents):
        path.append((grid[ui],grid[fi]))
        old_f=fore_index[ui,fi];ui,fi=up_index[ui,old_f],old_f
    path=np.asarray(path[::-1]);kernel=np.array([1.,6.,1.])/8.
    path=np.stack([np.convolve(path[:,k],kernel,mode='same') for k in range(2)],axis=1)
    for i in range(1,len(poses)-1):
        p=poses[i];ua,fa=axes[i];upper_roll,fore_roll=np.deg2rad(path[i])
        def apply(n,origin,axis,roll):
            turn=Quaternion(axis,roll);m=p[n]
            p[n]=A.mat(origin+turn@(m.translation-origin),turn@m.to_quaternion(),m.to_scale())
        for n in (name('clavicle'),name('upperarm_twist_01'),name('upperarm_twist_02'),u):
            apply(n,p[u].translation,ua,upper_roll)
        for n,share in ((l,1.),(name('lowerarm_twist_02'),.60),(name('lowerarm_twist_01'),.14)):
            apply(n,p[l].translation,fa,share*fore_roll)

def redistribute(A,poses,idle,side,rest,support_elbow):
    name=lambda n:n+'_'+side
    c,u,l,h=map(name,('clavicle','upperarm','lowerarm','hand'))
    s0,e0,w0=[idle[k].translation for k in (u,l,h)]
    up0,low0=e0-s0,w0-e0
    hint_e=smooth_centres([p[l].translation for p in poses])
    hint_s=smooth_centres([p[u].translation for p in poses])
    prior=0.;last_lower=last_pole=None;seam_state={}
    last_reach=last_swivel=None
    bottom=Vector((0.,-math.sin(math.radians(41.)),-math.cos(math.radians(41.))))
    bind_fore=rest[h].translation-rest[l].translation
    station=(rest[name('lowerarm_twist_02')].translation-rest[l].translation).dot(bind_fore)/bind_fore.length_squared
    stations={side:{name('lowerarm_twist_02'):station}}
    source_turns={bone:[p[bone].to_quaternion()@idle[bone].to_quaternion().inverted() for p in poses] for bone in (u,l)}
    def supported_turn(bone,neutral_axis,axis,i):
        # Transport neighbouring source rotations onto the same shaft before
        # averaging. A transient flip of the elbow plane gets low influence.
        kernels=(1,2,3,4,5,6,5,4,3,2,1)
        qs=[]
        for j in range(-5,6):
            rotation=source_turns[bone][min(max(0,i+j),len(poses)-1)]
            qs.append((rotation@neutral_axis).rotation_difference(axis)@rotation)
        centre=max(qs,key=lambda q:sum(w*abs(q.dot(r)) for w,r in zip(kernels,qs)))
        total=Vector((0,0,0,0))
        for w,q in zip(kernels,qs):
            dot=q.dot(centre)
            total+=Vector(q)*(w*(1. if dot>=0 else -1.)*max(.12,abs(dot)))
        return Quaternion(total).normalized()
    for i,p in enumerate(poses):
        if i==0 or i==len(poses)-1:continue
        hand=p[h].translation
        low_limit,high_limit=math.radians(30.),math.radians(125. if side=='r' else 140.)
        if side=='r':
            lower=(hand-hint_e[i]).normalized()
            elbow=hand-lower*low0.length
            upper=(elbow-hint_s[i]).normalized()
            # Leave room for the game's final two-bone grip correction. A nearly
            # straight chain can otherwise flip its elbow plane from frame to frame.
            bend=upper.angle(lower)
            pole=upper-lower*upper.dot(lower)
            if last_pole is not None:
                carried=last_lower.rotation_difference(lower)@last_pole
                turn=math.atan2(lower.dot(carried.cross(pole)),carried.dot(pole))
                # An almost straight elbow gives noisy pole observations. Transport
                # the last supported side instead of crossing the arm in one key.
                limit=math.radians(14.) if bend<math.radians(48) else math.radians(30.)
                pole=Quaternion(lower,max(-limit,min(turn,limit)))@carried
            elif pole.length<.04:
                natural=low0.normalized().rotation_difference(lower)@up0.normalized()
                pole=natural-lower*natural.dot(lower)
            last_lower,last_pole=lower.copy(),pole.normalized()
            bend=max(low_limit,min(bend,high_limit))
            upper=lower*math.cos(bend)+last_pole*math.sin(bend)
            shoulder=elbow-upper*up0.length
        else:
            # Anchor the proximal opening as well as the wrist. Moving the
            # shoulder around a fixed elbow exposes the cut end of this V7 mesh.
            # Project the shoulder onto the intersection of the reachable sphere
            # and the half-space below the wide camera's lower edge.
            shoulder=hint_s[i].copy()
            clearance=.113
            shoulder+=bottom*max(0.,clearance-bottom.dot(shoulder))
            reach=hand-shoulder
            a,b=up0.length,low0.length
            maximum=math.sqrt(a*a+b*b+2*a*b*math.cos(low_limit))
            minimum=math.sqrt(a*a+b*b+2*a*b*math.cos(high_limit))
            shoulder=hand-reach.normalized()*min(maximum,max(minimum,reach.length))
            if bottom.dot(shoulder)<clearance:
                signed=clearance-bottom.dot(hand)
                centre=hand+signed*bottom
                tangent=shoulder-centre;tangent-=bottom*tangent.dot(bottom)
                radius=math.sqrt(max(0.,maximum*maximum-signed*signed))
                shoulder=centre+tangent.normalized()*min(tangent.length,radius)
            reach=hand-shoulder;axis=reach.normalized()
            along=(a*a-b*b+reach.length_squared)/(2*reach.length)
            centre=shoulder+axis*along
            swivel=hint_e[i]-centre;swivel-=axis*swivel.dot(axis)
            if last_reach is not None:
                carried=last_reach.rotation_difference(axis)@last_swivel
                turn=math.atan2(axis.dot(carried.cross(swivel)),carried.dot(swivel))
                swivel=Quaternion(axis,max(-.24,min(.24,turn)))@carried
            last_reach,last_swivel=axis.copy(),swivel.normalized()
            elbow=centre+last_swivel*math.sqrt(max(0.,a*a-along*along))
            upper=(elbow-shoulder).normalized();lower=(hand-elbow).normalized()
        # Start at the shoulder with the shortest swing, independent of the
        # elbow-plane normal. That normal changes sign near full extension.
        su=up0.normalized().rotation_difference(upper)
        def set_bone(n,origin,neutral,rot):
            m=idle[n];p[n]=A.mat(origin+rot@(m.translation-neutral),rot@m.to_quaternion(),m.to_scale())
        if side=='r':
            # The leading hand already has a sound bind-space roll. Preserve
            # its natural winding and suppress only the short pole transients.
            ru=supported_turn(u,up0.normalized(),upper,i)
            rf=supported_turn(l,low0.normalized(),lower,i)
            palm=p[h].to_quaternion()@idle[h].to_quaternion().inverted()
            wrist=(palm@low0.normalized()).rotation_difference(lower)@palm
            twist=A.axis_angle(wrist@rf.inverted(),lower)
            for n in (c,u,name('upperarm_twist_01'),name('upperarm_twist_02')):
                set_bone(n,shoulder,s0,ru)
            for n,share in ((l,0.),(name('lowerarm_twist_02'),.40),(name('lowerarm_twist_01'),.86)):
                set_bone(n,elbow,e0,Quaternion(lower,twist*share)@rf)
            continue
        transported=lambda rot:(rot@low0.normalized()).rotation_difference(lower)@rot
        hand_delta=p[h].to_quaternion()@idle[h].to_quaternion().inverted()
        wrist=transported(hand_delta)
        phi=A.near_angle(A.axis_angle(wrist@transported(su).inverted(),lower),prior)
        prior=phi
        upper_roll=.40*phi
        end_upper=Quaternion(upper,upper_roll)@su
        start_fore=transported(end_upper)
        remaining=A.axis_angle(wrist@start_fore.inverted(),lower)
        # Clavicle and the proximal helper carry the same rigid shoulder ring.
        # Distal upper-arm and proximal forearm weights meet at the elbow.
        for n,share in ((c,0.),(name('upperarm_twist_01'),0.),(name('upperarm_twist_02'),.55),(u,1.)):
            set_bone(n,shoulder,s0,Quaternion(upper,upper_roll*share)@su)
        for n,share in ((l,0.),(name('lowerarm_twist_02'),.40),(name('lowerarm_twist_01'),.86)):
            set_bone(n,elbow,e0,Quaternion(lower,remaining*share)@start_fore)
        # The accepted two-hand idle already contains asymmetric humeral roll.
        # Account for the mesh's actual bind frame before skinning the elbow cap.
        uf=p[u].to_quaternion()@rest[u].to_quaternion().inverted()
        ff=p[l].to_quaternion()@rest[l].to_quaternion().inverted()
        hinge=(uf@bind_fore.normalized()).rotation_difference(lower)@uf
        offset=abs(A.axis_angle(ff@hinge.inverted(),lower))
        weight=A.smooth((math.degrees(offset)-32.)/40.)*A.smooth(i/14.)*A.smooth((len(poses)-1-i)/20.)
        p.update(support_elbow(p,rest,stations,side,seam_state,weight))
    if side=='r':balance_elbow_cap(A,poses,rest,side)
