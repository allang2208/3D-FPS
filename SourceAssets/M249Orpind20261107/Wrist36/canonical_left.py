"""Unify held grip anatomy across idle, box reload support and recovery."""
from rig import *
from scipy.ndimage import gaussian_filter1d
scope={'__file__':str(ROOT/'fit_left.py')}
exec(compile((ROOT/'fit_left.py').read_text().split('fits={};poses={};report={}')[0],str(ROOT/'fit_left.py'),'exec'),scope)
boxmargin=scope['boxmargin'];margin=scope['margin'];camera=scope['camera']
current=pickle.load(open(ROOT/'current_poses.pkl','rb'));fits=pickle.load(open(ROOT/'left_fits.pkl','rb'))
grips=json.loads((ROOT.parent/'Wrist34/fit.json').read_text());gun=ix['WPN_root'];cl,ua,la,ha,arm,hand=indices('l');owned=[cl]+arm+[ha]
poses={};report={}
def regrip(w,target,arm_weight,hand_weight):
    """Blend the contact in world space, then solve fixed-length joints.

    Interpolating local arm rotations alone lets the closed fist arc away from
    the grip while the source clavicle is still returning to its held position.
    """
    q0=R.from_matrix(rot(w[cl]));delta=(R.from_matrix(rot(target[cl]))*q0.inv()).as_rotvec()*arm_weight
    h=(1-hand_weight)*w[ha,:3,3]+hand_weight*target[ha,:3,3]
    turn=(R.from_matrix(rot(target[ha]))*R.from_matrix(rot(w[ha])).inv()).as_rotvec()*hand_weight
    c=w[cl,:3,3];a0,e0,h0=[w[i,:3,3] for i in [ua,la,ha]];lu=np.linalg.norm(e0-a0);ll=np.linalg.norm(h0-e0)
    def shoulder(x):return c+R.from_rotvec(x).as_matrix()@(a0-c)
    if np.linalg.norm(h-shoulder(delta))>.985*(lu+ll):
        fit=minimize(lambda x:np.linalg.norm(x-delta)**2,delta,method='SLSQP',constraints=[dict(type='ineq',fun=lambda x:.985*(lu+ll)-np.linalg.norm(h-shoulder(x)))],options=dict(maxiter=50,ftol=1e-9))
        delta=fit.x
    a=shoulder(delta);direction=unit(h-a);distance=np.linalg.norm(h-a);along=(lu*lu-ll*ll+distance*distance)/(2*distance);center=a+direction*along
    desired=(1-arm_weight)*e0+arm_weight*target[la,:3,3]
    oldpole=unit(e0-center-direction*((e0-center)@direction));pole=unit(desired-center-direction*((desired-center)@direction));angle=np.arctan2(direction@np.cross(oldpole,pole),oldpole@pole)
    return solve(w,np.r_[delta,angle],shift=h-h0,hand_rotation=R.from_rotvec(turn).as_matrix())
for family,clips in current.items():
    if family=='bipod':continue  # Separate deployed-bipod pose, not a foregrip variant.
    ip=next(p for p in clips if p.endswith('_idle'));rp=next(p for p in clips if p.endswith('_reload'));home=clips[ip]['world'][0]
    normal=clips[rp];midk=np.argmin(abs(normal['times']-3.));mid=normal['world'][midk];xf=mid[gun]@np.linalg.inv(home[gun]);cam=camera(family,rp,np.array([3.]))[0]
    cfg=grips['base' if family=='bipod' else family];pivot=np.array(cfg['pivot']);axis=np.array(cfg['axis'])
    if family=='angled':
        # The angled grip's long axis is diagonal, not the vertical-grip axis.
        pivot=np.array([5.15,-28.45,-16.48]);axis=unit(np.array([.05976,-.71679,.69472]))
    def held(x):
        turn=R.from_rotvec(axis*x[4]).as_matrix();h=home[ha,:3,3]
        return solve(home,x[:4],shift=pivot+turn@(h-pivot)-h,hand_rotation=turn)
    def cost(x):
        q=held(x);return max(0,bend(q)-3)**2*30+.03*np.linalg.norm(q[ua,:3,3]-home[ua,:3,3])**2+.01*np.linalg.norm(q[la,:3,3]-home[la,:3,3])**2+.005*np.degrees(x[:4]).dot(np.degrees(x[:4]))+.08*np.degrees(x[4])**2
    def constraints(x):
        q=held(x);length=np.linalg.norm(home[la,:3,3]-home[ua,:3,3])+np.linalg.norm(home[ha,:3,3]-home[la,:3,3])
        return np.array([boxmargin(q)-.2,margin(xf@q,cam)-.3,length*.97-np.linalg.norm(q[ha,:3,3]-q[ua,:3,3])])
    canonical_parameters=None
    if (ROOT/'held_reference.pkl').exists():
        # Freeze the exact held poses inspected from the engine's actual skin.
        canonical=pickle.load(open(ROOT/'held_reference.pkl','rb'))[family]
    else:
        best=None
        for seed in [np.zeros(5),np.array([0,.2,0,.3,.15]),np.array([0,.4,0,.7,-.1])]:
            fit=minimize(cost,seed,method='SLSQP',bounds=[(-1.2,1.2)]*4+[(-.35,.35)],constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=150,ftol=1e-6,eps=1e-5))
            rank=fit.fun+1e6*max(0,-constraints(fit.x).min())
            if best is None or rank<best[0]:best=rank,fit
        fit=best[1];canonical=held(fit.x);canonical=preserve_local(home[None],canonical[None],owned)[0];canonical_parameters=fit.x.tolist()
        if constraints(fit.x).min()<-.025:raise RuntimeError('Held constraints failed '+family+' '+str(constraints(fit.x)))
    canonlocal=encode(canonical[None],parents)[0];homelocal=encode(home[None],parents)[0]
    print('CANONICAL',family,'bend',bend(canonical),flush=True)
    for path,a in clips.items():
        t=a['times'];old=a['world'];local=encode(old,parents);new=old.copy()
        if path==ip:
            # Idle is static in source; no sequential fitter drift inside its loop.
            for b in owned:local[:,b,3:7]=canonlocal[b,3:7]
            new=compose(local,parents)
        else:
            empty=path.endswith('_empty');shift=.9 if empty else 0.
            data=fits[(family,path)];from scipy.interpolate import PchipInterpolator
            params=PchipInterpolator(data['times'],data['parameters'],axis=0)(t)
            params=gaussian_filter1d(params,4.,axis=0,mode='nearest')
            release_index=np.argmin(abs(t-(2.10-shift)))
            for k in range(len(t)):
                # Keep the measured contact poses, only improve the free arm.
                # Continue the same arm correction through the entire regrip
                # blend; cutting it off mid-blend caused a one-frame elbow step.
                if t[k]<2.8-shift:new[k]=solve(old[k],params[min(k,release_index)])
            # Source hand is free between cover release and approaching the belt.
            for k in range(len(t)):
                w=new[k];weight=ease((t[k]-.70)/.12)*(1-ease((t[k]-(1.22 if not empty else .93))/.12))
                if weight<=0:continue
                desired=unit(w[ha,:3,3]-w[la,:3,3]);rest=unit(B[ha,:3,3]-B[la,:3,3]);axis0=rot(w[ha])@rot(B[ha]).T@rest
                angle=max(0,np.radians(bend(w)-12))*weight;turn=R.from_rotvec(unit(np.cross(axis0,desired))*angle).as_matrix()
                new[k]=solve(w,np.zeros(4),hand_rotation=turn)
            mod=encode(new,parents)
            start_weight=1-ease((t-.10)/.25)
            hold_weight=ease((t-(2.10-shift))/.70)
            contact_weight=ease((t-(2.10-shift))/.50)
            for k,w in enumerate(old):
                target_world=w[gun]@np.linalg.inv(home[gun])@canonical
                # Once the left hand regrips, keep exactly the idle anatomy.
                for b in owned:
                    if start_weight[k]>0:
                        delta=(R.from_quat(canonlocal[b,3:7])*R.from_quat(homelocal[b,3:7]).inv()).as_rotvec()
                        startq=(R.from_rotvec(delta*start_weight[k])*R.from_quat(local[k,b,3:7])).as_quat()
                        q0=R.from_quat(mod[k,b,3:7]);turn=(R.from_quat(startq)*q0.inv()).as_rotvec();mod[k,b,3:7]=(R.from_rotvec(turn*start_weight[k])*q0).as_quat()
                if hold_weight[k]>0:
                    contact=regrip(new[k],target_world,hold_weight[k],contact_weight[k]);contact_local=encode(contact[None],parents)[0]
                    mod[k,owned,3:7]=contact_local[owned,3:7]
            local[:,owned,3:7]=mod[:,owned,3:7];new=compose(local,parents)
        poses[(family,path)]=dict(times=t,before=old,after=new,cameras=camera(family,path,t))
        b=np.array([bend(w) for w in new]);active=t>=(2.8-(.9 if path.endswith('_empty') else 0))
        report[family+'/'+path.split('.')[-1]]=dict(wrist_max=float(b.max()),held_wrist_max=float(b[active].max()) if active.any() else float(b.max()),canonical_wrist=bend(canonical),canonical_parameters=canonical_parameters,max_joint_frame_step_cm=float(np.linalg.norm(np.diff(new[:,:,:3,3][:,[ua,la,ha]],axis=0),axis=2).max()))
pickle.dump(poses,open(ROOT/'left_final.pkl','wb'));(ROOT/'left_final_report.json').write_text(json.dumps(report,indent=2))
