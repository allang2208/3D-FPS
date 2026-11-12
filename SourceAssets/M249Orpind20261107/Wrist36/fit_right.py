"""Hold the first three cartridges between the existing thumb/index pads.

The belt endpoint is authored and is not displaced by the soft-chain solver.
Keep the weapon and belt untouched; move the full right arm by joint rotations.
"""
from rig import *
from scipy.interpolate import PchipInterpolator
current=pickle.load(open(ROOT/'current_poses.pkl','rb'))['base']
cl,ua,la,ha,arm,hand=indices('r');belt=ix['New_PKM_Belt_00']
path=next(p for p in current if p.endswith('_reload'));normal=current[path]
k=np.argmin(abs(normal['times']-4.8));ref=normal['world'][k];points=skin(ref)
tips={digit:points[np.load(ROOT/(digit+'_tipids.npy'))].mean(0) for digit in ['index','thumb']}
p0=points[dominant==belt].mean(0);p2=points[dominant==ix['New_PKM_Belt_02']].mean(0)
pinch=unit(tips['index']-tips['thumb']);span=unit(p0-p2)
turn=R.from_rotvec(unit(np.cross(pinch,span))*np.arccos(np.clip(pinch@span,-1,1))).as_matrix()
# The case body, away from the pointed copper tips and the moving cover.
longaxis=rot(ref[belt])@rot(B[belt]).T@np.array([0.,1.,0.])
center=(p0+p2)/2+longaxis*1.0
shift=center-((tips['index']+tips['thumb'])/2-ref[ha,:3,3])@turn.T-ref[ha,:3,3]
handref=ref[ha].copy();handref[:3,:3]=turn@handref[:3,:3];handref[:3,3]+=shift
def rigid(w):
    m=w.copy();m[:3,:3]=rot(m);return m
contact_local=np.linalg.inv(rigid(ref[belt]))@handref
center_local=(np.linalg.inv(rigid(ref[belt]))@np.r_[center,1])[:3]
span_local=rot(ref[belt]).T@span
ref_local=encode(ref[None],parents)[0]
poses={};reports={}
for path,a in current.items():
    if '_reload' not in path:continue
    empty=path.endswith('_empty');t=a['times'];old=a['world'];offset=.9 if empty else 0.
    win=ease((t-(4.28-offset))/.24)*(1-ease((t-(5.10-offset))/.17))
    targets=[];new=[];params=[];last=np.zeros(5)
    for j,w in enumerate(old):
        weight=win[j]
        if weight<1e-10:new.append(w.copy());params.append(np.zeros(5));continue
        target=rigid(w[belt])@contact_local
        pivot=(rigid(w[belt])@np.r_[center_local,1])[:3];axis=rot(w[belt])@span_local
        def posed(x):
            roll=R.from_rotvec(axis*x[4]).as_matrix();h=pivot+roll@(target[:3,3]-pivot)
            delta=(R.from_matrix(roll@rot(target))*R.from_matrix(rot(w[ha])).inv()).as_rotvec()
            turn=R.from_rotvec(delta*weight).as_matrix();shift=(h-w[ha,:3,3])*weight
            return solve(w,x[:4],'r',shift,turn)
        def cost(x):
            q=posed(x)
            length=np.linalg.norm(w[la,:3,3]-w[ua,:3,3])+np.linalg.norm(w[ha,:3,3]-w[la,:3,3]);reach=np.linalg.norm(q[ha,:3,3]-q[ua,:3,3])
            return max(0,bend(q,'r')-8)**2*20+.04*np.linalg.norm(q[ua,:3,3]-w[ua,:3,3])**2+.02*np.linalg.norm(q[la,:3,3]-w[la,:3,3])**2+.004*np.degrees(x).dot(np.degrees(x))+.004*np.degrees(x-last).dot(np.degrees(x-last))+max(0,reach-length*.97)**2*1e5
        fit=minimize(cost,last,method='SLSQP',bounds=[(-1.25,1.25)]*4+[(-2.2,2.2)],options=dict(maxiter=100,ftol=1e-5,eps=1e-5))
        last=fit.x;params.append(last);q=posed(fit.x)
        # Keep the source pinch shape during contact, blend each original joint.
        local=encode(q[None],parents)[0]
        for b in hand:
            if b==ha:continue
            diff=(R.from_quat(ref_local[b,3:7])*R.from_quat(local[b,3:7]).inv()).as_rotvec()
            local[b,3:7]=(R.from_rotvec(diff*weight)*R.from_quat(local[b,3:7])).as_quat()
        new.append(compose(local[None],parents)[0])
    new=np.array(new);final=preserve_local(old,new,[cl]+arm+hand)
    poses[path]=dict(times=t,before=old,after=final,weights=win,parameters=np.array(params))
    report=dict(window=[4.28-offset,4.52-offset,5.10-offset,5.27-offset],max_hand_shift_cm=float(np.linalg.norm(final[:,ha,:3,3]-old[:,ha,:3,3],axis=1).max()),max_wrist_in_contact=float(max(bend(final[k],'r') for k in np.flatnonzero(win>.99))))
    reports[path]=report;print(path,report,flush=True)
pickle.dump(poses,open(ROOT/'right.pkl','wb'));(ROOT/'right_report.json').write_text(json.dumps(reports,indent=2))
experiment=pickle.load(open(ROOT/'experiment.pkl','rb'));a=poses[next(p for p in poses if p.endswith('_reload'))];k=np.argmin(abs(a['times']-5.1));experiment['right_belt']=dict(before=a['before'][k],after=a['after'][k],time=5.1)
pickle.dump(experiment,open(ROOT/'experiment.pkl','wb'))
