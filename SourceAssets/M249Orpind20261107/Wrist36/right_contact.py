"""Joint-only thumb/index pinch on the leading cartridge, with a full arm solve."""
from rig import *
from scipy.ndimage import gaussian_filter1d
current=pickle.load(open(ROOT/'current_poses.pkl','rb'))['base'];cl,ua,la,ha,arm,hand=indices('r');belt=ix['New_PKM_Belt_00']
normal=current[next(p for p in current if p.endswith('_reload'))];ref=normal['world'][np.argmin(abs(normal['times']-4.8))].copy();pts=skin(ref)
tips={digit:pts[np.load(ROOT/(digit+'_tipids.npy'))].mean(0) for digit in ['index','thumb']};mid=(tips['index']+tips['thumb'])/2;axis=unit(tips['index']-tips['thumb'])
for digit,sgn in [('index',1),('thumb',-1)]:
    root=ix[digit+'_01_r'];origin=ref[root,:3,3];a=unit(tips[digit]-origin);b=unit(mid+axis*1.10*sgn-origin)
    turn=R.from_rotvec(unit(np.cross(a,b))*np.arccos(np.clip(a@b,-1,1))).as_matrix()
    for i,n in enumerate(names):
        if n.startswith(digit+'_') and n.endswith('_r') and 'metacarpal' not in n:
            ref[i,:3,:3]=turn@ref[i,:3,:3];ref[i,:3,3]=origin+turn@(ref[i,:3,3]-origin)
points=skin(ref);pinch=(points[np.load(ROOT/'index_tipids.npy')].mean(0)+points[np.load(ROOT/'thumb_tipids.npy')].mean(0))/2
pinch_local=rot(ref[ha]).T@(pinch-ref[ha,:3,3]);ref_local=encode(ref[None],parents)[0]
centerlocal=np.linalg.inv(ref[belt])@np.r_[points[dominant==belt].mean(0),1]
poses={};reports={}
for path,a in current.items():
    if '_reload' not in path:continue
    empty=path.endswith('_empty');t=a['times'];old=a['world'];offset=.9 if empty else 0.;win=ease((t-(4.28-offset))/.24)*(1-ease((t-(5.10-offset))/.19))
    xs=[];last=np.zeros(7)
    def target(w,x,weight):
        bulletaxis=rot(w[belt])@rot(B[belt]).T@np.array([0.,1.,0.]);center=(w[belt]@centerlocal)[:3]+bulletaxis*.8+np.array([0.,0.,.15])
        turn=R.from_rotvec(x[4:]).as_matrix();hr=turn@rot(w[ha]);h=center-hr@pinch_local
        shift=(h-w[ha,:3,3])*weight;dr=R.from_rotvec(x[4:]*weight).as_matrix()
        return solve(w,x[:4]*weight,'r',shift,dr,station_weight=weight)
    for k,w in enumerate(old):
        weight=win[k]
        if weight<1e-10:xs.append(np.zeros(7));last=np.zeros(7);continue
        def cost(x):
            q=target(w,x,weight);length=np.linalg.norm(w[la,:3,3]-w[ua,:3,3])+np.linalg.norm(w[ha,:3,3]-w[la,:3,3]);reach=np.linalg.norm(q[ha,:3,3]-q[ua,:3,3])
            return max(0,bend(q,'r')-16)**2*10+.10*np.linalg.norm(q[ua,:3,3]-w[ua,:3,3])**2+.05*np.linalg.norm(q[la,:3,3]-w[la,:3,3])**2+.02*np.degrees(x[:4]).dot(np.degrees(x[:4]))+.10*np.degrees(x[4:]).dot(np.degrees(x[4:]))+.01*np.degrees(x-last).dot(np.degrees(x-last))+max(0,reach-length*.96)**2*1e5
        fit=minimize(cost,last,method='SLSQP',bounds=[(-.85,.85)]*4+[(-.4,.4)]*3,options=dict(maxiter=90,ftol=1e-5,eps=1e-5))
        last=fit.x;xs.append(last)
    xs=gaussian_filter1d(np.array(xs),1.25,axis=0,mode='nearest');new=old.copy()
    for k,w in enumerate(old):
        weight=win[k]
        if weight<1e-10:continue
        q=target(w,xs[k],weight);local=encode(q[None],parents)[0]
        for b in hand:
            if b==ha:continue
            diff=(R.from_quat(ref_local[b,3:7])*R.from_quat(local[b,3:7]).inv()).as_rotvec();local[b,3:7]=(R.from_rotvec(diff*weight)*R.from_quat(local[b,3:7])).as_quat()
        new[k]=compose(local[None],parents)[0]
    final=preserve_local(old,new,[cl]+arm+hand);poses[path]=dict(times=t,before=old,after=final,weights=win,parameters=xs)
    reports[path]=dict(max_contact_bend=float(max(bend(final[k],'r') for k in np.flatnonzero(win>.99))),max_hand_frame_step_cm=float(np.linalg.norm(np.diff(final[:,ha,:3,3],axis=0),axis=1).max()),window=[4.28-offset,4.52-offset,5.10-offset,5.29-offset])
    print(path,reports[path],flush=True)
pickle.dump(poses,open(ROOT/'right_final.pkl','wb'));(ROOT/'right_final_report.json').write_text(json.dumps(reports,indent=2))
experiment=pickle.load(open(ROOT/'experiment.pkl','rb'));a=poses[next(p for p in poses if p.endswith('_reload'))];k=np.argmin(abs(a['times']-5.1));experiment['right_belt']=dict(before=a['before'][k],after=a['after'][k],time=5.1);pickle.dump(experiment,open(ROOT/'experiment.pkl','wb'))
